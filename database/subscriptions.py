from typing import Optional
import json
import asyncpg
from datetime import datetime, timezone, timedelta
from database import get_pool


async def add_subscription(name: str, chat_id: int, person_accnt: int, queue_code: str) -> Optional[int]:
    """Add a new subscription for a chat and personal account.

    Args:
        name: Name of the subscription.
        chat_id: Telegram chat ID.
        person_accnt: Personal account identifier string.
    Returns:
        The ID of the newly created subscription, or None if it already exists.
    """
    
    async with get_pool().acquire() as conn:
        try:
            result = await conn.fetchrow(
                """
                INSERT INTO subscriptions (street, chat_id, person_accnt, queue_code)
                VALUES ($1, $2, $3, $4)
                RETURNING id;
                """,
                name,
                chat_id,
                person_accnt,
                queue_code,
            )
            return result["id"] if result else None
        except asyncpg.UniqueViolationError:
            return None
        
async def remove_subscription(chat_id: int, sub_id: int) -> bool:
    """Remove a subscription for a chat and personal account.

    Args:
        chat_id: Telegram chat ID.
        sub_id: Subscription ID.
    Returns:
        True if a subscription was deleted, False otherwise.
    """
    async with get_pool().acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM subscriptions
            WHERE chat_id = $1 AND id = $2;
            """,
            chat_id,
            sub_id,
        )
        return result.endswith("1")  # "DELETE 1" indicates one row deleted


async def list_subscriptions(chat_id: int) -> list[dict]:
    """List all subscriptions for a given chat.

    Args:
        chat_id: Telegram chat ID.
    Returns:
        List of subscription records.
    """
    async with get_pool().acquire() as conn:
        result = await conn.fetch(
            """
            SELECT * FROM subscriptions
            WHERE chat_id = $1;
            """,
            chat_id,
        )
        return [dict(record) for record in result]
    

async def set_subscription_enabled(chat_id: int, sub_id: int, enabled: bool) -> bool:
    """Enable or disable a subscription by ID.

    Args:
        chat_id: Telegram chat ID.
        sub_id: Subscription ID.
        enabled: True to enable, False to disable.
    """
    async with get_pool().acquire() as conn:
        result = await conn.execute(
            """
            UPDATE subscriptions
            SET enabled = $1, updated_at = (NOW() AT TIME ZONE 'Europe/Kyiv')
            WHERE id = $2 AND chat_id = $3;
            """,
            enabled,
            sub_id,
            chat_id,
        )
        return result.endswith("1")  # "UPDATE 1" indicates one row updated

async def get_subscription_by_id(sub_id: int) -> Optional[asyncpg.Record]:
    """Get a subscription by its ID.

    Args:
        sub_id: Subscription ID.
    Returns:
        Subscription record or None if not found.
    """
    async with get_pool().acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT * FROM subscriptions
            WHERE id = $1;
            """,
            sub_id,
        )
    
async def get_subscription_by_details(
    chat_id: int,
    person_accnt: int,
) -> Optional[dict]:
    """Get a subscription by its details.

    Args:
        chat_id: Telegram chat ID.
        person_accnt: Personal account identifier string.
    Returns:
        Subscription record or None if not found.
    """
    async with get_pool().acquire() as conn:
        result = await conn.fetchrow(
            """
            SELECT * FROM subscriptions
            WHERE chat_id = $1 AND person_accnt = $2;
            """,
            chat_id,
            person_accnt,
        )
        return dict(result) if result else None
    
async def update_subscription_payload(
    sub_id: int,
    hour_count: int,
    hour_reset_at: datetime,
    payload: Optional[list[dict]],
) -> bool:
    """Update the last payload of a subscription.

    Args:
        sub_id: Subscription ID.
        hour_count: Number of requests made in the current hour.
        hour_reset_at: Datetime when the hourly count resets.
        payload: New payload JSON payload (full dict from API).
    """
    async with get_pool().acquire() as conn:
        payload_str = json.dumps(payload, ensure_ascii=False)
        result = await conn.execute(
            """
            UPDATE subscriptions
            SET last_payload = ($1::jsonb), hour_count = $2, hour_reset_at = $3, updated_at = (NOW() AT TIME ZONE 'Europe/Kyiv')
            WHERE id = $4;
            """,
            payload_str,
            hour_count,
            hour_reset_at,
            sub_id,
        )
        return result.endswith("1")  # "UPDATE 1" indicates one row updated

async def list_chat_ids_by_queue(queue_code: str) -> list[int]:
    """Return distinct chat IDs subscribed to a queue (enabled only)."""
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT chat_id
            FROM subscriptions
            WHERE enabled = TRUE AND queue_code = $1
            """,
            queue_code,
        )
        out: list[int] = []
        for r in rows:
            try:
                out.append(int(r["chat_id"]))
            except Exception:
                pass
        return out