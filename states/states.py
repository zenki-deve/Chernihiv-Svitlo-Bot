"""States handlers for aiogram FSM."""

import aiohttp
from aiogram import types, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from keyboards import CANCEL_TEXT, main_menu, cancel_kb
from utils import try_fetch_with_limits
from database import add_subscription, check_subscription_limit, add_user
from utils import fetch_queue

states_router = Router(name="states")

class AddStreet(StatesGroup):
    waiting_person_accnt = State()


@states_router.message(AddStreet.waiting_person_accnt)
async def process_person_account(message: types.Message, state: FSMContext):
    """Process user input for adding a new street subscription."""
    person_account = (message.text or "")

    if person_account.lower() in {CANCEL_TEXT.lower()}:
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return
    
    if not person_account or not person_account.isdigit():
        await message.reply("Особовий рахунок має бути числом, спробуйте ще раз.", reply_markup=cancel_kb())
        return
    
    # Ensure user exists before enforcing subscription limits
    await add_user(
        message.chat.id,
        message.from_user.username if message.from_user else None,
        message.from_user.first_name if message.from_user else None,
        message.from_user.last_name if message.from_user else None,
        message.from_user.language_code if message.from_user else None,
        message.from_user.is_bot if message.from_user else False,
    )

    allowed = await check_subscription_limit(message.chat.id)
    if not allowed:
        await message.answer(
            "Досягнуто ліміту кількості підписок.\n"
            "Видаліть деякі у розділі «Підписки», щоб додати нові.",
            reply_markup=main_menu()
        )
        await state.clear()
        return
    
    async with aiohttp.ClientSession() as session:

        _, limit_msg = await try_fetch_with_limits(session, message.chat.id, int(person_account), is_poll=False)
        if limit_msg:
            await message.reply(limit_msg, reply_markup=cancel_kb())
            return
    
        resp_queue = await fetch_queue(session, person_account)
        if not resp_queue:
            print(resp_queue)
            await message.reply("Не вдалося отримати інформацію про чергу. Спробуйте ще раз.", reply_markup=cancel_kb())
            return
        
        street = resp_queue.get("street")
        queues = resp_queue.get("queues")
        if street is None or queues is None:
            await message.reply("Некоректна відповідь від сервера. Спробуйте ще раз.", reply_markup=cancel_kb())
            return

    sub_id = await add_subscription(street, message.chat.id, int(person_account), queues)
    if not sub_id:
        await message.answer("Такий запис вже існує або не вдалося зберегти.", reply_markup=main_menu())
        await state.clear()
        return
    
    await message.answer("Збережено та сповіщення увімкнено.", reply_markup=main_menu())
    await state.clear()