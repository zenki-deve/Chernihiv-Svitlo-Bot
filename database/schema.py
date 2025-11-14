DB_PATH = "base.db"

SCHEMA_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    chat_id INTEGER UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_users_chat ON users(chat_id);
"""

SCHEMA_SUBS = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    person_accnt TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_payload TEXT,
    updated_at TEXT,
    poll_interval_minutes INTEGER NOT NULL DEFAULT 30,
    UNIQUE(name, chat_id, person_accnt)
);
CREATE INDEX IF NOT EXISTS idx_subs_chat ON subscriptions(chat_id);
CREATE INDEX IF NOT EXISTS idx_subs_enabled ON subscriptions(enabled);
"""

SCHEMA_LIMITS = """
CREATE TABLE IF NOT EXISTS request_limits (
    chat_id INTEGER NOT NULL,
    person_accnt TEXT NOT NULL,
    hour_count INTEGER NOT NULL DEFAULT 0,
    hour_reset_at TEXT,
    hour_notified INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (chat_id, person_accnt)
);
"""

SCHEMA_CACHE = """
CREATE TABLE IF NOT EXISTS account_cache (
    person_accnt TEXT PRIMARY KEY,
    payload TEXT,
    updated_at TEXT
);
"""
