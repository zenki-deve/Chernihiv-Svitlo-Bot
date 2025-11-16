from typing import Optional
from database import get_pool


async def add_user(
    chat_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    language_code: Optional[str] = None,
    is_bot: Optional[bool] = None,
) -> None:
    """Insert or update a user by chat_id.

    Accepts optional fields to match Telegram payloads and handler usage.
    """
    async with get_pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (chat_id, username, first_name, last_name, language_code, is_bot, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, (NOW() AT TIME ZONE 'Europe/Kyiv'))
            ON CONFLICT(chat_id)
            DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                language_code = EXCLUDED.language_code,
                is_bot = COALESCE(EXCLUDED.is_bot, users.is_bot),
                updated_at = EXCLUDED.updated_at;
            """,
            chat_id,
            username,
            first_name,
            last_name,
            language_code,
            is_bot,
        )

async def check_subscription_limit(chat_id: int) -> bool:
    """Check if the user has reached the maximum number of street subscriptions.

    Args:
        chat_id: Telegram chat ID.
    Returns:
        True if the user can add more subscriptions, False if the limit is reached.
    """
    async with get_pool().acquire() as conn:
        result = await conn.fetchrow(
            "SELECT max_street_subscriptions FROM users WHERE chat_id = $1",
            chat_id,
        )
        if result is None:
            return False  # User not found, treat as limit reached
        max_subs = result["max_street_subscriptions"]
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM subscriptions WHERE chat_id = $1",
            chat_id,
        )
        return count < max_subs