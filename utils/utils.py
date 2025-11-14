"""Utility helpers shared across bot modules."""

from aiogram import types


def cb_chat_id(call: types.CallbackQuery) -> int:
    """Extract the chat_id for a callback query reliably.

    Args:
        call: Incoming callback query object.

    Returns:
        Integer chat_id derived from the original message when available,
        otherwise from the user id. Returns 0 if not found.
    """
    if call.message and call.message.chat:
        return call.message.chat.id
    return call.from_user.id if call.from_user else 0


def format_entries(a: list[dict]) -> str:
    """Format interruption entries list into a human-readable text.

    Args:
        a: List of interruption dicts returned by the upstream API (aData).

    Returns:
        Concatenated string suitable for sending in a Telegram message.
    """
    parts: list[str] = []
    for row in a:
        cause = (row.get('cause') or '').strip()
        begin = (row.get('acc_begin') or '').strip()
        end = (row.get('accend_plan') or '').strip()
        parts.append(f"{cause}\nПочаток: {begin}\nЗакінчення: {end}\n~~~~~~~~~~~~~~~~~~~~~")
    return "\n".join(parts)
