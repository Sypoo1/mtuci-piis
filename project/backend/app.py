"""
Backend API — оркестратор: валидация, кэш, БД, ML Service, метрики.

Endpoints:
  POST /api/predict          — одиночная транзакция
  POST /api/predict/batch    — CSV-файл (multipart)
  GET  /api/history          — последние N записей из БД
  GET  /api/health           — статус сервиса
  GET  /metrics              — Prometheus-метрики
"""

import os
import csv
import json
import time
import hashlib
import logging
import io

import httpx
import redis
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# ── Логирование ──────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Prometheus-метрики ───────────────────────────────────────────────────────

REQUEST_COUNT   = Counter("fraud_requests_total", "Total predict requests", ["endpoint", "status"])
REQUEST_LATENCY = Histogram("fraud_request_duration_seconds", "Request latency", ["endpoint"])
FRAUD_COUNT     = Counter("fraud_detected_total", "Fraud predictions returned")
CACHE_HITS      = Counter("fraud_cache_hits_total", "Redis cache hits")
CACHE_MISSES    = Counter("fraud_cache_misses_total", "Redis cache misses")

# ── Конфиг из env ────────────────────────────────────────────────────────────

ML_URL   = os.getenv("ML_SERVICE_URL", "http://ml_service:8001")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DB_DSN   = os.getenv("DATABASE_URL", "postgresql://fraud:fraud@postgres:5432/fraud")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

# ── Подключения (ленивые — при первом запросе) ───────────────────────────────

_redis: redis.Redis | None = None
_db_conn = None


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL, decode_responses=True)
    return _redis


def get_db():
    global _db_conn
    if _db_conn is None or _db_conn.closed:
        _db_conn = psycopg2.connect(DB_DSN)
        _db_conn.autocommit = True
        _init_db(_db_conn)
    return _db_conn


def _init_db(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id               SERIAL PRIMARY KEY,
                transaction_amt  FLOAT,
                product_cd       TEXT,
                card1            FLOAT,
                card4            TEXT,
                card6            TEXT,
                addr1            FLOAT,
                p_emaildomain    TEXT,
                device_type      TEXT,
                c1               FLOAT,
                fraud_probability FLOAT,
                is_fraud         BOOLEAN,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            )
        """)


# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title="Fraud Detector Backend")


# Middleware: логирование каждого запроса
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    log.info("%s %s %s %.3fs", request.method, request.url.path, response.status_code, elapsed)
    return response


class Transaction(BaseModel):
    TransactionAmt: float
    ProductCD: str | None = None
    card1: float | None = None
    card4: str | None = None
    card6: str | None = None
    addr1: float | None = None
    P_emaildomain: str | None = None
    DeviceType: str | None = None
    C1: float | None = None


def _cache_key(data: dict) -> str:
    s = json.dumps(data, sort_keys=True)
    return "fraud:" + hashlib.md5(s.encode()).hexdigest()


def _call_ml(data: dict) -> dict:
    resp = httpx.post(f"{ML_URL}/predict", json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _save_to_db(tx: dict, result: dict):
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO predictions
                  (transaction_amt, product_cd, card1, card4, card6,
                   addr1, p_emaildomain, device_type, c1,
                   fraud_probability, is_fraud)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                tx.get("TransactionAmt"), tx.get("ProductCD"), tx.get("card1"),
                tx.get("card4"), tx.get("card6"), tx.get("addr1"),
                tx.get("P_emaildomain"), tx.get("DeviceType"), tx.get("C1"),
                result["fraud_probability"], result["is_fraud"],
            ))
    except Exception as e:
        log.warning("DB write failed: %s", e)


def _predict_one(data: dict) -> dict:
    key = _cache_key(data)
    r = get_redis()

    # 1. Redis cache
    try:
        cached = r.get(key)
        if cached:
            CACHE_HITS.inc()
            return json.loads(cached)
    except Exception as e:
        log.warning("Redis get failed: %s", e)

    CACHE_MISSES.inc()

    # 2. PostgreSQL lookup
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT fraud_probability, is_fraud FROM predictions
                WHERE transaction_amt=%s AND product_cd=%s AND card1=%s
                  AND card4=%s AND card6=%s AND addr1=%s
                  AND p_emaildomain=%s AND device_type=%s AND c1=%s
                ORDER BY created_at DESC LIMIT 1
            """, (
                data.get("TransactionAmt"), data.get("ProductCD"), data.get("card1"),
                data.get("card4"), data.get("card6"), data.get("addr1"),
                data.get("P_emaildomain"), data.get("DeviceType"), data.get("C1"),
            ))
            row = cur.fetchone()
            if row:
                result = {"fraud_probability": row["fraud_probability"], "is_fraud": row["is_fraud"]}
                try:
                    r.setex(key, CACHE_TTL, json.dumps(result))
                except Exception:
                    pass
                return result
    except Exception as e:
        log.warning("DB lookup failed: %s", e)

    # 3. ML Service
    result = _call_ml(data)
    _save_to_db(data, result)
    try:
        r.setex(key, CACHE_TTL, json.dumps(result))
    except Exception:
        pass
    if result.get("is_fraud"):
        FRAUD_COUNT.inc()
    return result


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/predict")
def predict(tx: Transaction):
    endpoint = "/api/predict"
    with REQUEST_LATENCY.labels(endpoint).time():
        try:
            result = _predict_one(tx.model_dump())
            REQUEST_COUNT.labels(endpoint, "200").inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(endpoint, "500").inc()
            log.error("predict error: %s", e)
            return {"error": str(e)}, 500


@app.post("/api/predict/batch")
async def predict_batch(file: UploadFile = File(...)):
    endpoint = "/api/predict/batch"
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    results = []
    for row in reader:
        tx = {
            "TransactionAmt": float(row.get("TransactionAmt") or 0),
            "ProductCD":      row.get("ProductCD") or None,
            "card1":          float(row["card1"]) if row.get("card1") else None,
            "card4":          row.get("card4") or None,
            "card6":          row.get("card6") or None,
            "addr1":          float(row["addr1"]) if row.get("addr1") else None,
            "P_emaildomain":  row.get("P_emaildomain") or None,
            "DeviceType":     row.get("DeviceType") or None,
            "C1":             float(row["C1"]) if row.get("C1") else None,
        }
        try:
            res = _predict_one(tx)
            results.append({**tx, **res})
        except Exception as e:
            results.append({**tx, "error": str(e)})
    REQUEST_COUNT.labels(endpoint, "200").inc()
    return results


@app.get("/api/history")
def history(limit: int = 50):
    try:
        conn = get_db()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM predictions ORDER BY created_at DESC LIMIT %s", (limit,)
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error("history error: %s", e)
        return []


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
