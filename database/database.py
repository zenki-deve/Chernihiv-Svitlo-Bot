import asyncpg
from typing import Optional
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

USERS_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code VARCHAR(10),
    is_bot BOOLEAN DEFAULT FALSE,
    max_street_subscriptions INTEGER DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'Europe/Kyiv'),
    updated_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'Europe/Kyiv')
);
"""

SUBS_SQL = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id BIGSERIAL PRIMARY KEY,
    street TEXT NOT NULL,
    chat_id BIGINT NOT NULL,
    person_accnt BIGINT NOT NULL,
    queue_code TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_payload JSONB,
    hour_count INTEGER NOT NULL DEFAULT 0,
    hour_reset_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'Europe/Kyiv' + INTERVAL '1 hour'),
    updated_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'Europe/Kyiv'),
    CONSTRAINT uniq_sub UNIQUE (street, chat_id, person_accnt)
);
CREATE INDEX IF NOT EXISTS idx_subs_chat ON subscriptions(chat_id);
CREATE INDEX IF NOT EXISTS idx_subs_enabled ON subscriptions(enabled);
"""

QUEUE_SCHEDULE_SQL = """
CREATE TABLE IF NOT EXISTS queue_schedule (
    queue_code TEXT NOT NULL,
    sched_date DATE NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (NOW() AT TIME ZONE 'Europe/Kyiv') NOT NULL,
    PRIMARY KEY (queue_code, sched_date)
);
"""


async def init_db() -> None:
    """Initialize PostgreSQL schema based on schema.py (adapted for Postgres).

    This function connects, creates all tables and indexes if missing, then closes.
    """
    conn = await asyncpg.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
    )
    try:
        async with conn.transaction():
            await conn.execute(USERS_SQL)
            await conn.execute(SUBS_SQL)
            await conn.execute(QUEUE_SCHEDULE_SQL)
    finally:
        await conn.close()


# Connection pool for queries
_POOL: Optional[asyncpg.Pool] = None


async def init_pool() -> None:
    global _POOL
    if _POOL is None:
        _POOL = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            min_size=1,
            max_size=10,
        )


def _pool() -> asyncpg.Pool:
    if _POOL is None:
        raise RuntimeError("DB pool is not initialized. Call init_pool() first.")
    return _POOL


def get_pool() -> asyncpg.Pool:
    """Public accessor for the asyncpg pool. Ensure init_pool() was called."""
    return _pool()


async def close_pool() -> None:
    global _POOL
    if _POOL is not None:
        await _POOL.close()
        _POOL = None