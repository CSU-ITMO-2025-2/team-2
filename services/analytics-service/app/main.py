import asyncio
import json
import os
from typing import Dict

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI
from pydantic import BaseModel


class OrderEvent(BaseModel):
    id: str
    status: str


app = FastAPI(title="Analytics Service", version="0.1.0")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
ORDER_EVENTS_TOPIC = os.getenv("ORDER_EVENTS_TOPIC", "order-events")

_counters: Dict[str, int] = {
    "total_orders": 0,
    "succeeded": 0,
    "failed": 0,
}

_consumer: AIOKafkaConsumer | None = None
_consumer_task: asyncio.Task | None = None


async def _ingest_event(event: OrderEvent):
    _counters["total_orders"] += 1
    if event.status == "succeeded":
        _counters["succeeded"] += 1
    if event.status == "failed":
        _counters["failed"] += 1


async def _consume_events():
    assert _consumer
    try:
        async for msg in _consumer:
            data = json.loads(msg.value.decode("utf-8"))
            await _ingest_event(OrderEvent(**data))
    except asyncio.CancelledError:
        pass


@app.get("/analytics/summary")
async def summary():
    return _counters


@app.get("/metrics")
async def metrics():
    # Простейший Prometheus формат без сторонних зависимостей.
    lines = [
        "# HELP orders_total Total orders seen",
        "# TYPE orders_total counter",
        f"orders_total {_counters['total_orders']}",
        "# HELP orders_succeeded Total succeeded orders",
        "# TYPE orders_succeeded counter",
        f"orders_succeeded {_counters['succeeded']}",
        "# HELP orders_failed Total failed orders",
        "# TYPE orders_failed counter",
        f"orders_failed {_counters['failed']}",
    ]
    return "\n".join(lines) + "\n"


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "kafka": KAFKA_BOOTSTRAP_SERVERS,
        "topic": ORDER_EVENTS_TOPIC,
        "consumer_running": _consumer_task is not None and not _consumer_task.done(),
    }


@app.on_event("startup")
async def startup_event():
    global _consumer, _consumer_task
    _consumer = AIOKafkaConsumer(
        ORDER_EVENTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
    )
    await _consumer.start()
    _consumer_task = asyncio.create_task(_consume_events())


@app.on_event("shutdown")
async def shutdown_event():
    if _consumer_task:
        _consumer_task.cancel()
    if _consumer:
        await _consumer.stop()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

