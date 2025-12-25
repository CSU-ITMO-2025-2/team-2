import os
import asyncio
import json
import os
import uuid
from typing import Optional

from aiokafka import AIOKafkaProducer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app import db


class OrderCreate(BaseModel):
    user_id: str
    item: str
    amount: int = Field(gt=0)


class OrderRecord(OrderCreate):
    id: str
    status: str
    created_at: str
    updated_at: str


app = FastAPI(title="Order Service", version="0.1.0")

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
ORDER_EVENTS_TOPIC = os.getenv("ORDER_EVENTS_TOPIC", "order-events")

_producer: AIOKafkaProducer | None = None


async def publish_order_event(order: OrderRecord) -> None:
    """Publish order event to Kafka."""
    if not _producer:
        return
    payload = order.model_dump()
    await _producer.send_and_wait(ORDER_EVENTS_TOPIC, json.dumps(payload).encode("utf-8"))


def _to_order_record(data: dict) -> OrderRecord:
    return OrderRecord(
        id=data["id"],
        user_id=data["user_id"],
        item=data["item"],
        amount=data["amount"],
        status=data["status"],
        created_at=data["created_at"].isoformat(),
        updated_at=data["updated_at"].isoformat(),
    )


@app.post("/orders", response_model=OrderRecord)
async def create_order(order: OrderCreate) -> OrderRecord:
    order_id = str(uuid.uuid4())
    data = await db.create_order(
        user_id=order.user_id,
        item=order.item,
        amount=order.amount,
        status="pending",
        order_id=order_id,
    )
    record = _to_order_record(data)
    await publish_order_event(record)
    return record


@app.get("/orders/{order_id}", response_model=OrderRecord)
async def get_order(order_id: str) -> OrderRecord:
    data = await db.get_order(order_id)
    if not data:
        raise HTTPException(status_code=404, detail="Order not found")
    return _to_order_record(data)


@app.patch("/orders/{order_id}/status", response_model=OrderRecord)
async def update_status(order_id: str, status: str) -> OrderRecord:
    data = await db.update_order_status(order_id, status)
    if not data:
        raise HTTPException(status_code=404, detail="Order not found")
    record = _to_order_record(data)
    await publish_order_event(record)
    return record


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "kafka": KAFKA_BOOTSTRAP_SERVERS,
        "topic": ORDER_EVENTS_TOPIC,
        "database_url": db.DATABASE_URL,
    }


@app.on_event("startup")
async def startup_event():
    global _producer
    await db.init_db()
    _producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await _producer.start()


@app.on_event("shutdown")
async def shutdown_event():
    if _producer:
        await _producer.stop()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

