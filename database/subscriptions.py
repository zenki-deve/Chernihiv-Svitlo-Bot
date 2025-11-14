import json
import aiosqlite
from datetime import datetime
from typing import Optional, Dict, Any, List

from .schema import DB_PATH

async def add_subscription(name: str, chat_id: int, person_accnt: str) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            cur = await db.execute(
                "INSERT OR IGNORE INTO subscriptions (name, chat_id, person_accnt, enabled) VALUES (?, ?, ?, 1)",
                (name, chat_id, person_accnt),
            )
            await db.commit()
            if cur.lastrowid is None:
                async with db.execute(
                    "SELECT id FROM subscriptions WHERE name = ? AND chat_id = ? AND person_accnt = ?",
                    (name, chat_id, person_accnt),
                ) as c2:
                    row = await c2.fetchone()
                    return row[0] if row else None
            return int(cur.lastrowid)
        except Exception:
            return None

async def list_subscriptions(chat_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, name, person_accnt, enabled, updated_at, poll_interval_minutes FROM subscriptions WHERE chat_id = ? ORDER BY id DESC",
            (chat_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def remove_subscription(chat_id: int, sub_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM subscriptions WHERE id = ? AND chat_id = ?", (sub_id, chat_id))
        await db.commit()
        return cur.rowcount > 0

async def set_subscription_enabled(chat_id: int, sub_id: int, enabled: bool) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE subscriptions SET enabled = ? WHERE id = ? AND chat_id = ?",
            (1 if enabled else 0, sub_id, chat_id),
        )
        await db.commit()
        return cur.rowcount > 0

async def get_enabled_subscriptions() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, name, chat_id, person_accnt, last_payload, poll_interval_minutes FROM subscriptions WHERE enabled = 1"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

async def set_subscription_interval(chat_id: int, sub_id: int, minutes: int) -> bool:
    """Update polling interval (in minutes) for a subscription.

    Enforces boundary [10, 1440]. Returns True if updated.
    """
    minutes = max(10, min(1440, minutes))
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "UPDATE subscriptions SET poll_interval_minutes = ? WHERE id = ? AND chat_id = ?",
            (minutes, sub_id, chat_id),
        )
        await db.commit()
        return cur.rowcount > 0

async def set_last_payload_for_sub(sub_id: int, payload: Dict[str, Any]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscriptions SET last_payload = ?, updated_at = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False, sort_keys=True), datetime.utcnow().isoformat(), sub_id),
        )
        await db.commit()

async def get_last_payload_for_sub(sub_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT last_payload FROM subscriptions WHERE id = ?", (sub_id,)) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return None
            try:
                return json.loads(row[0])
            except Exception:
                return None
