"""Main bot entrypoint: command and message handlers, dispatcher wiring."""

import logging
import asyncio

from utils.log import setup_logger
from utils.updates import poll_loop
from callback import callback_router
from command import command_router
from states import states_router
from handler import handler_router
from config import API_TOKEN
from aiogram import Bot, Dispatcher, types
from database import init_db

logger = setup_logger(log_level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
dp.include_router(callback_router)
dp.include_router(command_router)
dp.include_router(states_router)
dp.include_router(handler_router)


async def main(bot: Bot):
    """Initialize DB, register bot commands, and start polling + background loop."""
    await init_db()
    try:
        await bot.set_my_commands([
            types.BotCommand(command="start", description="Start the bot"),
        ])
    except Exception:
        pass

    polling = asyncio.create_task(dp.start_polling(bot))
    bg = asyncio.create_task(poll_loop(bot))

    await asyncio.gather(polling, bg)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main(bot))