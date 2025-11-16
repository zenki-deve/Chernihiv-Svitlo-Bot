"""Command handlers for aiogram bot."""

from aiogram import types, Router
from aiogram.filters import Command

from keyboards import main_menu
from database import add_user

command_router = Router(name="commands")


@command_router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start and show main menu to authorized users."""
    await message.answer(
        (
            "Привіт! Цей бот надсилатиме сповіщення про зміни в графіку відключення електроенергії.\n\n"
            "Користуйтеся кнопками нижче для керування."
        ),
        reply_markup=main_menu(),
    )

    await add_user(
        message.chat.id,
        message.from_user.username if message.from_user else None,
        message.from_user.first_name if message.from_user else None,
        message.from_user.last_name if message.from_user else None,
        message.from_user.language_code if message.from_user else None,
        message.from_user.is_bot if message.from_user else False,
    )