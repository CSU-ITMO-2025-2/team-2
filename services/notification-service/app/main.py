import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict

from aiokafka import AIOKafkaConsumer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class NotificationRequest(BaseModel):
    order_id: str
    channel: str = Field(default="email")


class NotificationRecord(NotificationRequest):
    id: str
    status: str
    error: str | None = None
    created_at: str


_notifications: Dict[str, NotificationRecord] = {}

app = FastAPI(title="Notification Service", version="0.1.0")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
ORDER_EVENTS_TOPIC = os.getenv("ORDER_EVENTS_TOPIC", "order-events")

_consumer: AIOKafkaConsumer | None = None
_consumer_task: asyncio.Task | None = None


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


@app.post("/notify", response_model=NotificationRecord)
async def send_notification(req: NotificationRequest) -> NotificationRecord:
    notification_id = str(uuid.uuid4())
    record = NotificationRecord(
        id=notification_id,
        status="sent",
        error=None,
        created_at=_now(),
        **req.model_dump(),
    )
    _notifications[notification_id] = record
    return record


@app.get("/notifications/{notification_id}", response_model=NotificationRecord)
async def get_notification(notification_id: str) -> NotificationRecord:
    record = _notifications.get(notification_id)
    if not record:
        raise HTTPException(status_code=404, detail="Notification not found")
    return record


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "count": len(_notifications),
        "kafka": KAFKA_BOOTSTRAP_SERVERS,
        "topic": ORDER_EVENTS_TOPIC,
        "consumer_running": _consumer_task is not None and not _consumer_task.done(),
    }


async def _consume_events():
    assert _consumer
    try:
        async for msg in _consumer:
            data = json.loads(msg.value.decode("utf-8"))
            # Имитация отправки уведомления по событию заказа.
            await send_notification(NotificationRequest(order_id=data["id"], channel="email"))
    except asyncio.CancelledError:
        pass


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

