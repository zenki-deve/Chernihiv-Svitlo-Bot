"""Telegram keyboards used by the bot."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

CANCEL_TEXT = "Скасувати"

def cancel_kb() -> ReplyKeyboardMarkup:
    """Single-row keyboard with a Cancel button to abort a dialog."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def main_menu() -> ReplyKeyboardMarkup:
    """Main persistent reply keyboard with frequently used actions."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Додати адресу"), KeyboardButton(text="Мої дані")],
            [KeyboardButton(text="Перевірити зараз")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def subs_inline(subs: list[dict]) -> InlineKeyboardMarkup:
    """Build inline keyboard representing a list of subscriptions.

    Clicking an item opens action buttons for a specific subscription.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for s in subs:
        status = "🔔" if s.get("enabled") else "🔕"
        label = f"{status} {s['person_accnt']} | {s.get('street','')}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"sub:{s['id']}")])
        
    if not rows:
        rows = [[InlineKeyboardButton(text="Немає записів", callback_data="noop:0")]]
    
    rows.append([InlineKeyboardButton(text="🏠 Меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sub_actions_inline(sub: dict) -> InlineKeyboardMarkup:
    """Inline keyboard with actions for a single subscription."""
    enabled = bool(sub.get("enabled"))
    rows = [
        [InlineKeyboardButton(text=("🔕 Вимкнути сповіщення" if enabled else "🔔 Увімкнути сповіщення"), callback_data=f"toggle:{sub['id']}")],
        [InlineKeyboardButton(text="🔎 Перевірити графік", callback_data=f"check:{sub['id']}")],
        [
            InlineKeyboardButton(text="🗑️ Видалити", callback_data=f"del:{sub['id']}"),
            InlineKeyboardButton(text="⬅ Назад", callback_data="back_subs")
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)