from .database import _pool
from typing import Dict, Any
from datetime import date
import json

async def upsert_fetch_schedule(queue_code: str, sched_date: date, payload: Dict[str, Any]) -> None:
    """Insert or update full schedule JSON (including aData/aState) for queue/date."""
    async with _pool().acquire() as conn:
        payload_json = json.dumps(payload, ensure_ascii=False)
        await conn.execute(
            """
            INSERT INTO queue_schedule (queue_code, sched_date, payload)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (queue_code, sched_date)
            DO UPDATE SET payload=EXCLUDED.payload, updated_at=(NOW() AT TIME ZONE 'Europe/Kyiv')
            """,
            queue_code,
            sched_date,
            payload_json,
        )

async def list_queues_with_payload_for_date(sched_date: date) -> list[dict]:
    """Return queue codes and any existing full schedule JSON for the date."""
    async with _pool().acquire() as conn:
        rows = await conn.fetch(
            """
            WITH q AS (
                SELECT DISTINCT queue_code
                FROM subscriptions
                WHERE queue_code IS NOT NULL AND LENGTH(queue_code) > 0
            )
            SELECT q.queue_code, qs.payload
            FROM q
            LEFT JOIN queue_schedule qs
              ON qs.queue_code = q.queue_code AND qs.sched_date = $1
            ORDER BY q.queue_code
            """,
            sched_date,
        )
        out: list[dict] = []
        for r in rows:
            out.append({"queue_code": r["queue_code"], "payload": r["payload"]})
        return out