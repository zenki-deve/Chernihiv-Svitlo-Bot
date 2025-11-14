"""Database orchestration module.

This module wires together table-specific helpers and schema initialization.
It re-exports functions from submodules for convenient imports.
"""

import aiosqlite
from .schema import DB_PATH, SCHEMA_CACHE, SCHEMA_LIMITS, SCHEMA_SUBS, SCHEMA_USERS

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA_USERS)
        await db.executescript(SCHEMA_SUBS)
        await db.executescript(SCHEMA_LIMITS)
        await db.executescript(SCHEMA_CACHE)
        await db.commit()