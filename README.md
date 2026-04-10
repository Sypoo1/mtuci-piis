# Fraud Detector — Детектор банковского фрода

ML-сервис для детектирования мошеннических банковских транзакций на основе модели GradientBoosting (PR-AUC 0.357, ROC-AUC 0.813 на тестовой выборке).

## Архитектура

```
Браузер → Nginx :80 → Backend (FastAPI :8000) → ML Service (FastAPI :8001)
                                ↕                        ↕
                           PostgreSQL              Redis (кэш)
```

| Компонент | Технология | Роль |
|---|---|---|
| **Nginx** | nginx:alpine | Единая точка входа, раздача статики, reverse proxy |
| **Frontend** | React (CDN) | Веб-интерфейс: форма, CSV-загрузка, история |
| **Backend** | FastAPI + Python | Валидация, кэш, БД, метрики, оркестрация |
| **ML Service** | FastAPI + scikit-learn | Инференс модели GradientBoosting |
| **PostgreSQL** | postgres:16 | Хранение истории предсказаний |
| **Redis** | redis:7 | Кэш результатов (TTL 1 час) |

## Требования

- Docker ≥ 24
- docker-compose ≥ 2.20 (или `docker compose` plugin)

## Запуск

```bash
cd project
docker-compose up --build
```

Сервис будет доступен по адресу **http://localhost**.

## Использование

### Через браузер

Откройте http://localhost — веб-интерфейс с тремя вкладками:
- **Одиночная транзакция** — заполните форму и нажмите «Проверить»
- **CSV-файл** — загрузите [`project/test_data.csv`](project/test_data.csv) для пакетной проверки
- **История** — последние 20 предсказаний из БД

### Через curl (одиночная транзакция)

```bash
curl -X POST http://localhost/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionAmt": 1200.0,
    "ProductCD": "C",
    "card1": 9999,
    "card4": "mastercard",
    "card6": "credit",
    "addr1": null,
    "P_emaildomain": null,
    "DeviceType": "mobile",
    "C1": 10.0
  }'
```

Ответ:
```json
{"fraud_probability": 0.8231, "is_fraud": true, "threshold": 0.1739}
```

### Через curl (CSV-файл)

```bash
curl -X POST http://localhost/api/predict/batch \
  -F "file=@project/test_data.csv"
```

### История предсказаний

```bash
curl http://localhost/api/history?limit=10
```

### Метрики Prometheus

```bash
curl http://localhost/metrics
```

Экспортируемые метрики:
- `fraud_requests_total` — количество запросов по endpoint и статусу
- `fraud_request_duration_seconds` — latency запросов
- `fraud_detected_total` — количество обнаруженных фродов
- `fraud_cache_hits_total` / `fraud_cache_misses_total` — попадания в кэш

## Структура проекта

```
project/
├── ml_service/       # ML Service: инференс модели
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── backend/          # Backend API: оркестратор
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/         # Frontend: React SPA
│   ├── index.html
│   └── Dockerfile
├── nginx/            # Reverse proxy
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
├── test_data.csv     # Тестовые данные
└── task.txt
Models/
├── final_model.pkl   # Обученная модель (GradientBoosting)
└── final_model_meta.json
docs/
├── lab1.md           # Постановка задачи и архитектура
├── lab2.md           # Предобработка данных
├── lab3.md           # Разработка и оценка модели
└── lab4.md           # Интеграция, мониторинг, контейнеризация
```

## Документация

- [ЛР1 — Постановка задачи и архитектура](docs/lab1.md)
- [ЛР2 — Предобработка данных](docs/lab2.md)
- [ЛР3 — Разработка и оценка модели](docs/lab3.md)
- [ЛР4 — Интеграция, мониторинг, контейнеризация](docs/lab4.md)
