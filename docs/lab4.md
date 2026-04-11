# Лабораторная работа №4: Интеграция, инференс, мониторинг и контейнеризация ML-сервиса

**ФИО:** Шамсутдинов Рустам Фаргатевич
**Группа:** БВТ2201
**Тема:** Детектор фрода по банковским транзакциям

---

## Шаг 1. Разработка инференс-модуля

Реализован микросервис [`project/ml_service/app.py`](../project/ml_service/app.py) на FastAPI.

- При старте контейнера модель `Models/final_model.pkl` (GradientBoosting из ЛР3) загружается в память один раз через `joblib.load()`
- `POST /predict` принимает параметры транзакции, выполняет предобработку (log1p, медианная импутация, LabelEncoding) и возвращает `fraud_probability`, `is_fraud`, `threshold`
- `GET /health` — проверка доступности
- Latency инференса: ~0.13 мс; end-to-end через весь стек: ~20–30 мс (требование ЛР1 < 200 мс выполнено)

---

## Шаг 2. Интеграция компонентов

Все модули объединены через [`project/docker-compose.yml`](../project/docker-compose.yml). Итоговая архитектура соответствует спроектированной в ЛР1 (шаги 5–7) — расхождений нет.

| Компонент | Стек | Порт |
|---|---|---|
| Nginx | nginx:alpine | 80 |
| Frontend | React + TypeScript + Vite | — |
| Backend | FastAPI + Python | 8000 |
| ML Service | FastAPI + scikit-learn | 8001 |
| PostgreSQL | postgres:16 | 5432 |
| Redis | redis:7 | 6379 |
| Prometheus | prom/prometheus | 9090 |
| Grafana | grafana/grafana | 3000 |

**Поток данных:** Браузер → Nginx → Backend → Redis (кэш) → PostgreSQL → ML Service. Повторные запросы с теми же параметрами возвращаются из Redis без обращения к ML Service.

---

## Шаг 3. Внедрение базового мониторинга

- **Логирование запросов** — HTTP middleware в Backend логирует каждый запрос: метод, путь, статус-код, время выполнения
- **Метрики доступности** — `GET /api/health` (Backend) и `GET /health` (ML Service); Docker healthcheck для postgres, redis, ml_service
- **Метрики нагрузки** — экспортируются по `GET /metrics` в формате Prometheus:
  - `fraud_requests_total` — счётчик запросов по endpoint и статусу
  - `fraud_request_duration_seconds` — histogram latency (p50, p95, p99)
  - `fraud_detected_total` — количество обнаруженных фродов
  - `fraud_cache_hits_total` / `fraud_cache_misses_total` — эффективность кэша
- **Визуализация** — Grafana на http://localhost:3000 с преднастроенным дашбордом (RPS, latency p95, fraud rate, cache hit ratio, memory)

---

## Шаг 4. Контейнеризация и оркестрация

Каждый компонент имеет свой Dockerfile:

| Компонент | Базовый образ |
|---|---|
| ML Service | python:3.11-slim |
| Backend | python:3.11-slim |
| Frontend | node:20-alpine → nginx:alpine (multi-stage) |
| Nginx | nginx:alpine |

`docker-compose.yml` описывает 8 сервисов с зависимостями (`depends_on` + `condition: service_healthy`), томами (`pg_data`, `redis_data`, `prom_data`, `grafana_data`) и переменными окружения. Модель монтируется как read-only volume: `../Models:/app/models:ro`.

**Запуск одной командой:**
```bash
cd project
docker-compose up --build
```

---

## Шаг 5. Тестовые данные и демонстрация

Тестовые данные: [`project/test_data.csv`](../project/test_data.csv) — 5 транзакций (3 легитимных, 2 фрода).

**Демонстрация:**
- Веб-интерфейс: http://localhost — форма ввода, загрузка CSV, история предсказаний
- API: `POST /api/predict`, `POST /api/predict/batch`, `GET /api/history`
- Мониторинг: Grafana http://localhost:3000 (admin / admin)

---

## Ответы на вопросы самопроверки

**Как загрузка модели влияет на время старта?** Модель загружается ~2–3 с при старте контейнера. Уменьшить можно, предзагрузив модель в образ на этапе сборки или используя ONNX-формат.

**Что произойдёт при ошибке предсказания?** Backend перехватывает исключение, логирует его и возвращает `{"error": "..."}` с кодом 500. Транзакция не сохраняется в БД.

**Как обеспечивается безопасность данных?** Все сервисы работают внутри Docker-сети, наружу открыт только порт 80. Конфиденциальные поля (card1, addr1) не попадают в логи — логируется только метод/путь/статус.

**Какие метрики помогут заметить ухудшение качества?** Изменение доли фрода (`fraud_detected_total / fraud_requests_total`), рост latency, падение cache hit ratio.

**Как тестировалась интеграция?** Через curl-запросы к каждому эндпоинту после `docker-compose up --build`: одиночная транзакция, CSV-файл, история, метрики, повторный запрос для проверки кэша.

**Что сломается при 10 000 пользователях?** Backend — единственный инстанс с синхронным psycopg2. Решение: несколько реплик, async-драйвер (asyncpg), connection pooler.

---

## Ссылки на источники

1. [FastAPI Documentation](https://fastapi.tiangolo.com/)
2. [prometheus-client Python](https://github.com/prometheus/client_python)
3. [Docker Compose Documentation](https://docs.docker.com/compose/)
4. [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)
5. [Архитектурная диаграмма — ЛР1](lab1.md#шаг-5-проектирование-высокоуровневой-архитектуры-системы)
6. [Финальная модель — ЛР3](lab3.md#шаг-6-финальная-модель)

---
