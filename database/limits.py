import aiosqlite
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .schema import DB_PATH

async def _get_limits_row(db: aiosqlite.Connection, chat_id: int, person_accnt: str):
    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT chat_id, person_accnt, hour_count, hour_reset_at, hour_notified FROM request_limits WHERE chat_id = ? AND person_accnt = ?",
        (chat_id, person_accnt),
    ) as cur:
        row = await cur.fetchone()
        return dict(row) if row else None

async def _ensure_limits_row(db: aiosqlite.Connection, chat_id: int, person_accnt: str):
    row = await _get_limits_row(db, chat_id, person_accnt)
    if row is None:
        await db.execute(
            "INSERT OR IGNORE INTO request_limits (chat_id, person_accnt) VALUES (?, ?)",
            (chat_id, person_accnt),
        )
        await db.commit()
        row = await _get_limits_row(db, chat_id, person_accnt)
    return row


def _parse_iso(dt: Optional[str]):
    if not dt:
        return None
    try:
        return datetime.fromisoformat(dt)
    except Exception:
        return None


def _to_iso(dt) -> str:
    return dt.isoformat(timespec="minutes")


async def consume_request_budget(chat_id: int, person_accnt: str, now_utc: datetime) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        row = await _ensure_limits_row(db, chat_id, person_accnt)
        if row is None:
            row = {}
        hour_count = int(row.get("hour_count", 0) or 0)
        hour_reset_at = _parse_iso(row.get("hour_reset_at"))

        changed = False
        if hour_reset_at is None or now_utc >= hour_reset_at:
            hour_count = 0
            hour_reset_at = now_utc + timedelta(hours=1)
            row["hour_notified"] = 0
            changed = True
        if changed:
            await db.execute(
                "UPDATE request_limits SET hour_count = ?, hour_reset_at = ?, hour_notified = ? WHERE chat_id = ? AND person_accnt = ?",
                (hour_count, _to_iso(hour_reset_at), row.get("hour_notified", 0), chat_id, person_accnt),
            )
            await db.commit()

        exceeded_hour = hour_count >= 5
        if exceeded_hour:
            return {
                "ok": False,
                "exceeded": "hour",
                "hour_reset_at": _to_iso(hour_reset_at) if hour_reset_at else None,
                "hour_notified": int(row.get("hour_notified", 0) or 0),
            }

        hour_count += 1
        await db.execute(
            "UPDATE request_limits SET hour_count = ? WHERE chat_id = ? AND person_accnt = ?",
            (hour_count, chat_id, person_accnt),
        )
        await db.commit()
        return {
            "ok": True,
            "exceeded": None,
            "hour_reset_at": _to_iso(hour_reset_at) if hour_reset_at else None,
            "hour_notified": int(row.get("hour_notified", 0) or 0),
        }


async def mark_limit_notified(chat_id: int, person_accnt: str, which: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE request_limits SET hour_notified = 1 WHERE chat_id = ? AND person_accnt = ?",
            (chat_id, person_accnt),
        )
        await db.commit()
