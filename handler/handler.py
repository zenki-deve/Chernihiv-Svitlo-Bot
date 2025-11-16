"""Handler for main menu button presses and manual checks."""

import aiohttp
from aiogram import Router
from aiogram import types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from database import list_subscriptions
from keyboards import cancel_kb, subs_inline, main_menu
from states import AddStreet
from utils import format_entries, try_fetch_with_limits

handler_router = Router(name="handler")

@handler_router.message(F.text, StateFilter(None))
async def on_menu(message: types.Message, state: FSMContext):
    """Handle main menu button presses and manual checks."""
    
    txt = (message.text or "").strip()

    if txt == "Додати адресу":
        await state.set_state(AddStreet.waiting_person_accnt)
        await message.answer("Введіть особовий рахунок:", reply_markup=cancel_kb())

    elif txt == "Мої дані":
        subs = await list_subscriptions(message.chat.id)
        await message.answer("Оберіть запис:", reply_markup=subs_inline(subs))

    elif txt == "Перевірити зараз":
        subs = await list_subscriptions(message.chat.id)
        if not subs:
            await message.answer("Немає записів. Натисніть 'Додати адресу'.")
            return
        
        async with aiohttp.ClientSession() as session:
            for s in subs:
                data, limit_msg = await try_fetch_with_limits(session, message.chat.id, s["person_accnt"], is_poll=False)
                header = f"О/р {s['person_accnt']},\n{s.get('street','')}"

                if limit_msg:
                    await message.answer(f"{header}: {limit_msg}")
                    continue

                if not data:
                    await message.answer(f"{header}: не вдалося отримати дані")
                    continue

                await message.answer(f"{header}\n\n{format_entries(data)}"[:4000])

    else:
        await message.answer("Невідома команда. Використовуйте меню.", reply_markup=main_menu())