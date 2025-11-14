from aiogram import types, Router
from aiogram.filters import Command

from keyboards import main_menu

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