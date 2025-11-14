import asyncio
import aiohttp
from aiogram import types, F, Router, Bot
from typing import cast

from keyboards import subs_inline, sub_actions_inline, cancel_kb, CANCEL_TEXT, main_menu
from utils.updates import try_fetch_with_limits, extract_aData
from utils import format_entries, cb_chat_id
from database import (
    list_subscriptions,
    set_subscription_enabled,
    remove_subscription,
    set_subscription_interval,
)

callback_router = Router(name="callback")
pending_interval: dict[int, tuple[int, int]] = {}


@callback_router.callback_query(F.data.startswith("toggle:"))
async def cb_toggle(call: types.CallbackQuery):
    if not call.data:
        await call.answer()
        return
    
    sub_id = int(call.data.split(":")[1])
    chat_id = cb_chat_id(call)
    subs = await list_subscriptions(chat_id)
    found = next((s for s in subs if s["id"] == sub_id), None)

    if not found:
        await call.answer("Не знайдено")
        return
    
    new_state = not bool(found.get("enabled"))
    ok = await set_subscription_enabled(chat_id, sub_id, new_state)
    await call.answer("Увімкнено" if new_state else "Вимкнено", show_alert=False)

    if ok and call.message:
        subs = await list_subscriptions(chat_id)
        sub = next((x for x in subs if x["id"] == sub_id), None)
        if sub:
            header = f"Налаштування:\n\nО/р {sub['person_accnt']}, {sub.get('name','')}"
            try:
                msg = cast(types.Message, call.message)
                await msg.edit_text(header, reply_markup=sub_actions_inline(sub))
            except Exception:
                    
                try:
                    msg = cast(types.Message, call.message)
                    await msg.delete()
                except Exception:
                    pass
                await cast(types.Message, call.message).answer(header, reply_markup=sub_actions_inline(sub))


@callback_router.callback_query(F.data.startswith("check:"))
async def cb_check(call: types.CallbackQuery):
    if not call.data:
        await call.answer()
        return
    
    sub_id = int(call.data.split(":")[1])
    chat_id = cb_chat_id(call)
    subs = await list_subscriptions(chat_id)
    s = next((x for x in subs if x["id"] == sub_id), None)

    if not s:
        await call.answer("Не знайдено")
        return

    async with aiohttp.ClientSession() as session:
        data, limit_msg = await try_fetch_with_limits(session, chat_id, s["person_accnt"], is_poll=False)
    if limit_msg:
        await call.answer("Ліміт вичерпано", show_alert=True)
        if call.message:
            await call.message.answer(limit_msg)
        return
    
    if not data:
        await call.answer("Немає даних", show_alert=True)
        return
    
    a = extract_aData(data)
    if not a:
        if call.message:
            await call.message.answer("Немає записів aData")
        await call.answer()
        return
    
    if call.message:
        header = f"О/р {s['person_accnt']},\n {s.get('name','')}"
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sub:{s['id']}")]]
        )
        try:
            msg = cast(types.Message, call.message)
            await msg.edit_text(f"{header}\n\n{format_entries(a)}"[:4000], reply_markup=kb)
        except Exception:
            try:
                msg = cast(types.Message, call.message)
                await msg.delete()
            except Exception:
                pass
            await cast(types.Message, call.message).answer(f"{header}\n\n{format_entries(a)}"[:4000], reply_markup=kb)
    await call.answer()


@callback_router.callback_query(F.data == "menu")
async def cb_main_menu(call: types.CallbackQuery):
    if call.message:
        try:
            msg = cast(types.Message, call.message)
            await msg.delete()
        except Exception:
            pass
        await cast(types.Message, call.message).answer("Меню:", reply_markup=main_menu())
    await call.answer()


@callback_router.callback_query(F.data.startswith("del:"))
async def cb_delete(call: types.CallbackQuery):
    if not call.data:
        await call.answer()
        return
    
    sub_id = int(call.data.split(":")[1])
    chat_id = cb_chat_id(call)
    ok = await remove_subscription(chat_id, sub_id)
    await call.answer("Видалено" if ok else "Не знайдено")

    subs = await list_subscriptions(chat_id)
    if call.message:
        try:
            msg = cast(types.Message, call.message)
            await msg.edit_text("Підписки:", reply_markup=subs_inline(subs))
        except Exception:
            try:
                msg = cast(types.Message, call.message)
                await msg.delete()
            except Exception:
                pass
            await cast(types.Message, call.message).answer("Підписки:", reply_markup=subs_inline(subs))


@callback_router.callback_query(F.data.startswith("sub:"))
async def cb_open_sub(call: types.CallbackQuery):
    if not call.data:
        await call.answer()
        return
    
    sub_id = int(call.data.split(":")[1])
    chat_id = cb_chat_id(call)
    subs = await list_subscriptions(chat_id)
    s = next((x for x in subs if x["id"] == sub_id), None)

    if not s:
        await call.answer("Не знайдено")
        return
    
    if call.message:
        header = f"Налаштування:\n\nО/р {s['person_accnt']}, {s.get('name','')}"
        try:
            msg = cast(types.Message, call.message)
            await msg.edit_text(header, reply_markup=sub_actions_inline(s))
        except Exception:
            try:
                msg = cast(types.Message, call.message)
                await msg.delete()
            except Exception:
                pass
            await cast(types.Message, call.message).answer(header, reply_markup=sub_actions_inline(s))

    await call.answer()


@callback_router.callback_query(F.data == "back_subs")
async def cb_back_subs(call: types.CallbackQuery):
    chat_id = cb_chat_id(call)
    subs = await list_subscriptions(chat_id)
    if call.message:
        try:
            msg = cast(types.Message, call.message)
            await msg.edit_text("Підписки:", reply_markup=subs_inline(subs))
        except Exception:
            try:
                msg = cast(types.Message, call.message)
                await msg.delete()
            except Exception:
                pass
            await cast(types.Message, call.message).answer("Підписки:", reply_markup=subs_inline(subs))
    await call.answer()


@callback_router.callback_query(F.data.startswith("interval:"))
async def cb_interval_edit(call: types.CallbackQuery):
    if not call.data:
        await call.answer()
        return
    
    sub_id = int(call.data.split(":")[1])
    chat_id = cb_chat_id(call)
    subs = await list_subscriptions(chat_id)
    s = next((x for x in subs if x["id"] == sub_id), None)

    if not s:
        await call.answer("Не знайдено")
        return
    
    if call.message:
        try:
            msg = cast(types.Message, call.message)
            await msg.delete()
        except Exception:
            pass

        prompt = (
            "Введіть інтервал у хвилинах (10 - 1440). Поточний: "
            f"{s.get('poll_interval_minutes') or 30}. Надішліть число або натисніть '{CANCEL_TEXT}'."
        )

        bot_instance = cast(Bot, call.bot) if call.bot else None
        sent = None

        if bot_instance:
            sent = await bot_instance.send_message(chat_id=chat_id, text=prompt, reply_markup=cancel_kb())
        else:
            sent = await cast(types.Message, call.message).answer(prompt, reply_markup=cancel_kb())
        if sent:
            pending_interval[chat_id] = (sub_id, sent.message_id)
    await call.answer()


@callback_router.message(F.text.regexp(r"^\d{1,4}$") & F.chat.id.func(lambda cid: cid in pending_interval))
async def msg_interval_input(message: types.Message):
    chat_id = message.chat.id
    sub_id, prompt_id = pending_interval.get(chat_id, (None, None)) or (None, None)
    raw = (message.text or "").strip()

    try:
        minutes = int(raw)
    except ValueError:
        try:
            await message.delete()
        except Exception:
            pass

        try:
            tmp = await message.answer("Невірне число")
            await asyncio.sleep(2)
            try:
                await tmp.delete()
            except Exception:
                pass
        except Exception:
            pass
        return
    
    if minutes < 10 or minutes > 1440:
        try:
            await message.delete()
        except Exception:
            pass

        try:
            tmp = await message.answer("Число поза допустимим діапазоном (10-1440)")
            await asyncio.sleep(2)
            try:
                await tmp.delete()
            except Exception:
                pass
        except Exception:
            pass
        return
    
    if sub_id is None:
        await message.answer("Спроба оновлення скасована або не ініційована.")
        return
    
    ok = await set_subscription_interval(chat_id, sub_id, minutes)

    try:
        bot_instance = cast(Bot, message.bot)
        if prompt_id:
            await bot_instance.delete_message(chat_id=chat_id, message_id=prompt_id)
    except Exception:
        pass
    
    try:
        await message.delete()
    except Exception:
        pass

    pending_interval.pop(chat_id, None)
    subs = await list_subscriptions(chat_id)
    s = next((x for x in subs if x["id"] == sub_id), None)
    
    try:
        if not ok:
            tmp = await message.answer("Не вдалося оновити інтервал.", reply_markup=types.ReplyKeyboardRemove())
            await asyncio.sleep(2)
            try:
                await tmp.delete()
            except Exception:
                pass
        else:
            tmp = await message.answer("Інтервал оновлено ✅", reply_markup=types.ReplyKeyboardRemove())
            await asyncio.sleep(2)
            try:
                await tmp.delete()
            except Exception:
                pass
    except Exception:
        pass
    
    if s:
        header = f"Налаштування:\n\nО/р {s['person_accnt']}, {s.get('name','')}"
        await message.answer(header, reply_markup=sub_actions_inline(s))


@callback_router.message(F.text.func(lambda t: t and t.lower() == CANCEL_TEXT.lower()) & F.chat.id.func(lambda cid: cid in pending_interval))
async def msg_interval_cancel(message: types.Message):
    chat_id = message.chat.id
    sub_id, prompt_id = pending_interval.pop(chat_id, (None, None)) or (None, None)
    
    try:
        bot_instance = cast(Bot, message.bot)
        if prompt_id:
            await bot_instance.delete_message(chat_id=chat_id, message_id=prompt_id)
    except Exception:
        pass
    
    try:
        await message.delete()
    except Exception:
        pass

    if sub_id is None:
        try:
            tmp = await message.answer("Скасовано", reply_markup=types.ReplyKeyboardRemove())
            await asyncio.sleep(2)
            try:
                await tmp.delete()
            except Exception:
                pass
        except Exception:
            pass
        return
    
    subs = await list_subscriptions(chat_id)
    s = next((x for x in subs if x["id"] == sub_id), None)

    try:
        tmp = await message.answer("Скасовано", reply_markup=types.ReplyKeyboardRemove())
        await asyncio.sleep(2)
        try:
            await tmp.delete()
        except Exception:
            pass
    except Exception:
        pass

    if s:
        header = f"Налаштування:\n\nО/р {s['person_accnt']}, {s.get('name','')}"
        await message.answer(header, reply_markup=sub_actions_inline(s))