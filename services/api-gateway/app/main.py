import os
from typing import Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class OrderCreate(BaseModel):
    user_id: str
    item: str
    amount: int


class OrderStatus(BaseModel):
    id: str
    status: str
    item: str
    amount: int
    user_id: str
    updated_at: str


ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:8002")

app = FastAPI(title="API Gateway", version="0.1.0")

_local_cache: Dict[str, OrderStatus] = {}


async def create_order_via_http(order: OrderCreate) -> OrderStatus:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{ORDER_SERVICE_URL}/orders", json=order.model_dump())
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        data = resp.json()
        return OrderStatus(**data)


async def fetch_order_status(order_id: str) -> Optional[OrderStatus]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{ORDER_SERVICE_URL}/orders/{order_id}")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        return OrderStatus(**resp.json())


@app.post("/orders", response_model=OrderStatus)
async def create_order(order: OrderCreate) -> OrderStatus:
    created = await create_order_via_http(order)
    _local_cache[created.id] = created
    return created


@app.get("/orders/{order_id}", response_model=OrderStatus)
async def get_order(order_id: str) -> OrderStatus:
    if order_id in _local_cache:
        return _local_cache[order_id]
    status = await fetch_order_status(order_id)
    if not status:
        raise HTTPException(status_code=404, detail="Order not found")
    _local_cache[order_id] = status
    return status


@app.get("/health")
async def health():
    return {"status": "ok", "order_service_url": ORDER_SERVICE_URL}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)

