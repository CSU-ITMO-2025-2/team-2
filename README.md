# Учебный каркас распределенной системы (FastAPI + Kafka + Postgres)

Минимальный набор микросервисов на Python/FastAPI для учебного проекта:

- `api-gateway` — принимает внешние запросы, проксирует в `order-service`.
- `order-service` — создает и хранит заказы, публикует события в Kafka (`order-events`).
- `notification-service` — потребляет события из Kafka, имитирует отправку уведомлений.
- `analytics-service` — потребляет события из Kafka и отдает агрегированные метрики/статистику.

Инфраструктура пока сведена к локальному `docker-compose` с Kafka/Zookeeper и Postgres. Helm/CI/CD/ArgoCD и Chaos Mesh не тронуты по условию.

## Быстрый старт (локально)
```bash
docker compose up --build
```

Порты по умолчанию:
- API Gateway: http://localhost:8001
- Order Service: http://localhost:8002
- Notification Service: http://localhost:8003
- Analytics Service: http://localhost:8004
- Kafka: PLAINTEXT kafka:9092 (внутри compose)

Примеры запросов:
```bash
curl -X POST http://localhost:8001/orders -H "Content-Type: application/json" \
  -d '{"user_id":"u1","item":"book","amount":2}'

curl http://localhost:8001/orders/<order_id>
curl http://localhost:8004/analytics/summary
```

## Структура репозитория
- `services/*/app` — код микросервисов (FastAPI).
- `services/*/requirements.txt` — зависимости каждого сервиса.
- `services/*/Dockerfile` — сборка образов.
- `docker-compose.yml` — локальный запуск всех сервисов + Kafka/ZooKeeper + Postgres.

## Заметки по данным
- Postgres используется в `order-service` (асинхронный SQLAlchemy, таблица `orders`).
- Миграции: простые SQL-файлы в `services/order-service/migrations`; выполняются на старте.

## Дальнейшие шаги
- Настроить Helm-чарты, CI/CD, ArgoCD, Chaos Mesh (позже).

