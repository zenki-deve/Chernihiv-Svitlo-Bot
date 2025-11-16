"""Callback query handlers for aiogram bot."""

import aiohttp
from aiogram import types, F, Router, Bot
from typing import cast

from keyboards import subs_inline, sub_actions_inline, main_menu
from utils import try_fetch_with_limits
from utils import format_entries, cb_chat_id
from database import (
    list_subscriptions,
    set_subscription_enabled,
    remove_subscription,
    get_subscription_by_id,
)

callback_router = Router(name="callback")
pending_interval: dict[int, tuple[int, int]] = {}


@callback_router.callback_query(F.data == "menu")
async def cb_menu(call: types.CallbackQuery):
    if call.message:
        await call.message.answer("Головне меню:", reply_markup=main_menu())
    else:
        chat_id = cb_chat_id(call)
        bot = cast(Bot, call.bot)
        await bot.send_message(chat_id, "Головне меню:", reply_markup=main_menu())
    await call.answer()


@callback_router.callback_query(F.data.startswith("toggle:"))
async def cb_toggle(call: types.CallbackQuery):
    if not call.data:
        await call.answer()
        return
    
    chat_id = cb_chat_id(call)
    sub_id = int(call.data.split(":")[1])
    s = await get_subscription_by_id(sub_id)

    if not s:
        await call.answer("Не знайдено")
        return
    
    new_state = not bool(s.get("enabled"))
    ok = await set_subscription_enabled(chat_id, sub_id, new_state)
    await call.answer("Увімкнено" if new_state else "Вимкнено", show_alert=False)

    if ok and call.message:
        subs = await list_subscriptions(chat_id)
        sub = next((x for x in subs if x["id"] == sub_id), None)
        if sub:
            header = f"Налаштування:\n\nО/р {sub['person_accnt']}, {sub.get('street','')}"
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
    
    chat_id = cb_chat_id(call)
    sub_id = int(call.data.split(":")[1])
    s = await get_subscription_by_id(sub_id)

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
    
    if call.message:
        header = f"О/р {s['person_accnt']},\n {s.get('street','')}"
        kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"sub:{s['id']}")]]
        )
        try:
            msg = cast(types.Message, call.message)
            await msg.edit_text(f"{header}\n\n{format_entries(data)}"[:4000], reply_markup=kb)
        except Exception:
            try:
                msg = cast(types.Message, call.message)
                await msg.delete()
            except Exception:
                pass
            await cast(types.Message, call.message).answer(f"{header}\n\n{format_entries(data)}"[:4000], reply_markup=kb)
    await call.answer()


@callback_router.callback_query(F.data.startswith("del:"))
async def cb_delete(call: types.CallbackQuery):
    if not call.data:
        await call.answer()
        return
    
    chat_id = cb_chat_id(call)
    sub_id = int(call.data.split(":")[1])
    s = await remove_subscription(chat_id, sub_id)

    if not s:
        await call.answer("Не вдалося видалити")
        return

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
        header = f"Налаштування:\n\nО/р {s['person_accnt']}, {s.get('street','')}"
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