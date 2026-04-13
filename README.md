# Ссылка на репозиторий в GitFlic

[**https://gitflic.mtuci.ru/project/r-f-shamsutdinov-edu-mtuci-ru/mtuci-piis**](https://gitflic.mtuci.ru/project/r-f-shamsutdinov-edu-mtuci-ru/mtuci-piis)



# Fraud Detector

Сервис автоматического детектирования мошеннических банковских транзакций на основе ML.
Пользователь вводит параметры транзакции через веб-форму или загружает CSV — сервис возвращает вероятность фрода и бинарное решение.

Модель: GradientBoosting · PR-AUC **0.357** · ROC-AUC **0.813** · порог **0.1739**

## Требования

- Docker ≥ 24
- docker-compose ≥ 2.20

## Установка и запуск

```bash
git clone <repo>
cd project
docker-compose up --build
```

Весь стек поднимается одной командой. После старта:

| Сервис | URL |
|---|---|
| Приложение | http://localhost |
| Grafana (мониторинг) | http://localhost:3000 (admin / admin) |

## Использование

### Через веб-интерфейс (http://localhost)

Интерфейс содержит три вкладки:

**Одиночная транзакция**
1. Заполните поля формы: сумма, тип продукта, данные карты, устройство и т.д.
2. Нажмите «Проверить» — результат появится под формой: ✅ Легитимная или 🚨 ФРОД с вероятностью

**CSV-файл**
1. Нажмите на область загрузки и выберите CSV-файл (пример: [`project/test_data.csv`](project/test_data.csv))
2. Нажмите «Загрузить и проверить» — отобразится таблица с результатами по каждой строке

**История**
- Показывает последние 20 предсказаний из базы данных с временными метками

### Через curl

**Одиночная транзакция:**
```bash
curl -X POST http://localhost/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionAmt": 1200,
    "ProductCD": "C",
    "card1": 9999,
    "card4": "mastercard",
    "card6": "credit",
    "DeviceType": "mobile",
    "C1": 10
  }'
```

**Пакетная обработка CSV:**
```bash
curl -X POST http://localhost/api/predict/batch \
  -F "file=@project/test_data.csv"
```

**История предсказаний:**
```bash
curl "http://localhost/api/history?limit=10"

```

**Метрики Prometheus:**
```bash
curl http://localhost/metrics
```

## Архитектура

```
Браузер → Nginx :80 → Backend :8000 → ML Service :8001
                           ↕
                    PostgreSQL + Redis
```

| Компонент | Стек | Роль |
|---|---|---|
| Frontend | React + TypeScript + Vite | Веб-интерфейс |
| Backend | FastAPI + Python | Оркестрация, кэш, БД, метрики |
| ML Service | FastAPI + scikit-learn | Инференс GradientBoosting |
| PostgreSQL | postgres:16 | История предсказаний |
| Redis | redis:7 | Кэш результатов (TTL 1 ч) |
| Prometheus + Grafana | — | Мониторинг |

Подробные диаграммы: [контекстная диаграмма](docs/lab1.md#шаг-5-проектирование-высокоуровневой-архитектуры-системы) · [диаграмма модулей](docs/lab1.md#шаг-6-выделение-модулей-и-протоколов-взаимодействия)

## Подключение к БД напрямую

| | Host | Port | User | Password | DB |
|---|---|---|---|---|---|
| PostgreSQL | localhost | 5432 | fraud | fraud | fraud |
| Redis | localhost | 6379 | — | — | — |

## Структура проекта

```
project/
├── ml_service/          # Инференс модели
├── backend/             # API, кэш, БД, метрики
├── frontend/            # React + TS (App.tsx)
├── nginx/               # Reverse proxy
├── grafana/             # Дашборд + datasource provisioning
├── prometheus.yml       # Конфиг scrape
├── docker-compose.yml
└── test_data.csv        # Тестовые данные (5 транзакций)
Models/
└── final_model.pkl      # Обученная модель (GradientBoosting, joblib)
```

## Документация

| | |
|---|---|
| [ЛР1 — Постановка задачи и архитектура](docs/lab1.md) | Бизнес-задача, EDA, архитектурные диаграммы, выбор технологий |
| [ЛР2 — Предобработка данных](docs/lab2.md) | Пайплайн предобработки, разбиение выборки |
| [ЛР3 — Разработка и оценка модели](docs/lab3.md) | Эксперименты, финальная модель, метрики |
| [ЛР4 — Интеграция, мониторинг, контейнеризация](docs/lab4.md) | Описание сервиса, мониторинг, Docker |
