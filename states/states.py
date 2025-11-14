import aiohttp
from aiogram import types, Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from keyboards import CANCEL_TEXT, main_menu, cancel_kb
from utils.updates import try_fetch_with_limits
from database import add_subscription

states_router = Router(name="states")

class AddStreet(StatesGroup):
    waiting_name = State()
    waiting_person_accnt = State()


@states_router.message(AddStreet.waiting_name)
async def process_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    
    if name.lower() in {CANCEL_TEXT.lower(), "отмена"}:
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return
    
    if not name:
        await message.reply("Назва не може бути порожньою, спробуйте ще раз.", reply_markup=cancel_kb())
        return
    
    await state.update_data(name=name)
    await state.set_state(AddStreet.waiting_person_accnt)
    await message.answer("Введіть особовий рахунок:", reply_markup=cancel_kb())

@states_router.message(AddStreet.waiting_person_accnt)
async def process_person_account(message: types.Message, state: FSMContext):
    person_account = (message.text or "").strip()

    if person_account.lower() in {CANCEL_TEXT.lower(), "отмена"}:
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_menu())
        return
    
    if not person_account or not person_account.isdigit():
        await message.reply("Особовий рахунок має бути числом, спробуйте ще раз.", reply_markup=cancel_kb())
        return
    
    await state.update_data(person_accnt=person_account)
    data = await state.get_data()

    name = data.get("name", "").strip()
    if not name:
        await message.reply("Назва не може бути порожньою, спробуйте ще раз.", reply_markup=cancel_kb())
        return
    
    async with aiohttp.ClientSession() as session:
        resp, limit_msg = await try_fetch_with_limits(session, message.chat.id, person_account, is_poll=False)
    if limit_msg:
        await message.reply(limit_msg, reply_markup=cancel_kb())
        return
    if not resp:
        await message.reply("Валідація не пройшла (status!='ok' або помилка). Спробуйте ще раз.", reply_markup=cancel_kb())
        return
    
    sub_id = await add_subscription(name, message.chat.id, person_account)
    if not sub_id:
        await message.answer("Такий запис вже існує або не вдалося зберегти.", reply_markup=main_menu())
        await state.clear()
        return
    
    await message.answer("Збережено та сповіщення увімкнено.", reply_markup=main_menu())
    await state.clear()