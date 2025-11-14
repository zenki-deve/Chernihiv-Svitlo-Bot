import json
import aiosqlite
from datetime import datetime
from typing import Optional, Dict, Any

from .schema import DB_PATH

async def get_cached_account(person_accnt: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT payload, updated_at FROM account_cache WHERE person_accnt = ?", (person_accnt,)) as cur:
            row = await cur.fetchone()
            if not row or not row[0]:
                return None
            try:
                payload = json.loads(row[0])
            except Exception:
                return None
            return {"payload": payload, "updated_at": row[1]}

async def set_cached_account(person_accnt: str, payload: Dict[str, Any]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO account_cache (person_accnt, payload, updated_at) VALUES (?, ?, ?) ON CONFLICT(person_accnt) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (person_accnt, json.dumps(payload, ensure_ascii=False, sort_keys=True), datetime.utcnow().isoformat()),
        )
        await db.commit()
