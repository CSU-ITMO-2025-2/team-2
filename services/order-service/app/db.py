import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://app:app@postgres:5432/orders",
)

metadata = MetaData()

orders_table = Table(
    "orders",
    metadata,
    Column("id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("item", String, nullable=False),
    Column("amount", Integer, nullable=False),
    Column("status", String, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def run_migrations():
    """Execute simple SQL migrations from migrations/*.sql if present."""
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    if not migrations_dir.exists():
        return
    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        return

    async with engine.begin() as conn:
        for sql_file in sql_files:
            sql_text = sql_file.read_text(encoding="utf-8")
            if sql_text.strip():
                await conn.execute(text(sql_text))


async def init_db():
    # Ensure tables exist (idempotent) and run SQL migrations.
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    await run_migrations()


async def create_order(
    user_id: str,
    item: str,
    amount: int,
    status: str,
    order_id: str,
) -> dict:
    now = utcnow()
    async with SessionLocal() as session:
        await session.execute(
            orders_table.insert().values(
                id=order_id,
                user_id=user_id,
                item=item,
                amount=amount,
                status=status,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
    return {
        "id": order_id,
        "user_id": user_id,
        "item": item,
        "amount": amount,
        "status": status,
        "created_at": now,
        "updated_at": now,
    }


async def get_order(order_id: str) -> Optional[dict]:
    async with SessionLocal() as session:
        result = await session.execute(
            orders_table.select().where(orders_table.c.id == order_id)
        )
        row = result.fetchone()
        if not row:
            return None
        data = dict(row._mapping)
        return data


async def update_order_status(order_id: str, status: str) -> Optional[dict]:
    now = utcnow()
    async with SessionLocal() as session:
        result = await session.execute(
            orders_table.update()
            .where(orders_table.c.id == order_id)
            .values(status=status, updated_at=now)
            .returning(orders_table)
        )
        await session.commit()
        row = result.fetchone()
        if not row:
            return None
        data = dict(row._mapping)
        return data

