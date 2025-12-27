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

## CI/CD

Проект использует GitHub Actions для автоматической сборки и публикации Docker образов.

### Workflow

При push в ветку `main`/`master` или создании Pull Request:
1. **Сборка образов** — собираются Docker образы для всех 4 сервисов
2. **Публикация** — образы публикуются в GitHub Container Registry (ghcr.io)
3. **Тестирование** — выполняются базовые проверки синтаксиса и валидация docker-compose

### Использование образов

После успешной сборки образы доступны по адресам:
```
ghcr.io/<ваш-username>/api-gateway:latest
ghcr.io/<ваш-username>/order-service:latest
ghcr.io/<ваш-username>/notification-service:latest
ghcr.io/<ваш-username>/analytics-service:latest
```

Для использования в docker-compose замените `build:` на `image:`:
```yaml
api-gateway:
  image: ghcr.io/<ваш-username>/api-gateway:latest
  # вместо build: ./services/api-gateway
```

### Secrets

GitHub Actions автоматически использует `GITHUB_TOKEN` для публикации в GitHub Container Registry. Дополнительная настройка не требуется.

## Дальнейшие шаги
- Настроить Helm-чарты, ArgoCD, Chaos Mesh (позже).

