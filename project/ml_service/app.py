"""
ML Service — инференс детектора фрода.
POST /predict  →  { fraud_probability, is_fraud, threshold }
GET  /health   →  { status: "ok" }
"""

import os
import logging
import numpy as np
import joblib
from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Параметры предобработки (из train-выборки) ───────────────────────────────

NUM_MEDIANS = {"card1": 3429.0, "addr1": 299.0, "C1": 1.0}

CAT_MAPS = {
    "ProductCD":    {"C": 0, "H": 1, "R": 2, "S": 3, "W": 4, "unknown": 5},
    "card4":        {"american express": 0, "discover": 1, "mastercard": 2, "visa": 3, "unknown": 4},
    "card6":        {"charge card": 0, "credit": 1, "debit": 2, "debit or credit": 3, "unknown": 4},
    "P_emaildomain": {
        "aim.com": 0, "anonymous.com": 1, "aol.com": 2, "att.net": 3,
        "bellsouth.net": 4, "cableone.net": 5, "centurylink.net": 6,
        "charter.net": 7, "comcast.net": 8, "cox.net": 9,
        "earthlink.net": 10, "embarqmail.com": 11, "frontier.com": 12,
        "frontiernet.net": 13, "gmail.com": 14, "gmx.de": 15,
        "hotmail.co.uk": 16, "hotmail.com": 17, "hotmail.de": 18,
        "hotmail.es": 19, "hotmail.fr": 20, "icloud.com": 21,
        "juno.com": 22, "live.com": 23, "live.com.mx": 24,
        "live.fr": 25, "mac.com": 26, "mail.com": 27,
        "me.com": 28, "msn.com": 29, "netzero.com": 30,
        "netzero.net": 31, "optonline.net": 32, "outlook.com": 33,
        "outlook.es": 34, "prodigy.net.mx": 35, "ptd.net": 36,
        "q.com": 37, "roadrunner.com": 38, "rocketmail.com": 39,
        "sbcglobal.net": 40, "sc.rr.com": 41, "servicios-ta.com": 42,
        "suddenlink.net": 43, "twc.com": 44, "unknown": 45,
        "verizon.net": 46, "web.de": 47, "windstream.net": 48,
        "yahoo.co.jp": 49, "yahoo.co.uk": 50, "yahoo.com": 51,
        "yahoo.com.mx": 52, "yahoo.de": 53, "yahoo.es": 54,
        "yahoo.fr": 55, "ymail.com": 56,
    },
    "DeviceType": {"desktop": 0, "mobile": 1, "unknown": 2},
}

THRESHOLD = 0.1739
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/final_model.pkl")

# ── Загрузка модели при старте ───────────────────────────────────────────────

log.info("Loading model from %s", MODEL_PATH)
model = joblib.load(MODEL_PATH)
log.info("Model loaded: %s", type(model).__name__)

# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title="ML Service — Fraud Detector")


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


def preprocess(t: dict) -> np.ndarray:
    t = dict(t)
    t["TransactionAmt"] = np.log1p(float(t.get("TransactionAmt") or 0))
    for col, median in NUM_MEDIANS.items():
        val = t.get(col)
        t[col] = float(val) if val is not None else median
    for col, mapping in CAT_MAPS.items():
        val = t.get(col)
        val = str(val).strip().lower() if val is not None else "unknown"
        t[col] = mapping.get(val, mapping["unknown"])
    return np.array([[
        t["TransactionAmt"], t["ProductCD"], t["card1"],
        t["card4"], t["card6"], t["addr1"],
        t["P_emaildomain"], t["DeviceType"], t["C1"],
    ]], dtype=float)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(tx: Transaction):
    X = preprocess(tx.model_dump())
    prob = float(model.predict_proba(X)[0, 1])
    return {
        "fraud_probability": round(prob, 4),
        "is_fraud": bool(prob >= THRESHOLD),
        "threshold": THRESHOLD,
    }
