"""Utility helpers for handling updates and polling logic."""

import aiohttp
import json
import asyncio
from aiogram import Bot
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple, Dict, Any

from config import CACHE_SEC
from utils import format_daily_schedule
from utils.request import fetch_status, fetch_schedule
from database import (
    get_subscription_by_details,
    update_subscription_payload,
    upsert_fetch_schedule,
    list_queues_with_payload_for_date,
    list_chat_ids_by_queue,
)

def _kyiv_tz():
    try:
        return ZoneInfo("Europe/Kyiv")
    except Exception:
        return timezone.utc


def _build_limit_message(person_accnt: int, hour_reset_at: Optional[str]) -> str:
    """Build a localized message for exceeded hourly limit.

    Args:
        person_accnt: The target account identifier.
        hour_reset_at: Optional ISO string for when the hourly window resets.

    Returns:
        A human-readable message informing the user about exceeded hourly limit.
    """
    parts = [f"Ліміт запитів перевищено для {person_accnt}."]
    if hour_reset_at:
        dt = datetime.fromisoformat(hour_reset_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        kyiv = ZoneInfo("Europe/Kyiv")
        dt_local = dt.astimezone(kyiv)
        local_str = dt_local.strftime("%H:%M")
        parts.append(f"Годинний ліміт оновиться о {local_str}.")
    return " ".join(parts)


async def try_fetch_with_limits(
    session: aiohttp.ClientSession,
    chat_id: int,
    person_accnt: int,
    *,
    is_poll: bool = False,
) -> Tuple[Optional[list[dict[str, Any]]], Optional[str]]:
    """Try to fetch status for a personal account, respecting subscription limits and cache.

    Args:
        session: Shared aiohttp client session.
        chat_id: Chat ID of the requesting user.
        person_accnt: Personal account identifier.
        is_poll: Whether this fetch is part of the polling loop (no limit checks).

    Returns:
        A tuple of (data payload dict when successful, otherwise None, limit message when limit exceeded, otherwise None).
    """
    kyiv = _kyiv_tz()
    now_kyiv = datetime.now(kyiv)

    sub = await get_subscription_by_details(chat_id, person_accnt)
    if sub is None:
        
        if not is_poll:
            data_direct = await fetch_status(session, str(person_accnt))
            return data_direct, None
        return None, None
    
    cached_payload: Optional[Dict[str, Any]] = sub.get("last_payload") if sub.get("last_payload") else None
    updated_at: Optional[datetime] = sub.get("updated_at")

    if updated_at is not None:
        if (now_kyiv - updated_at).total_seconds() < CACHE_SEC and cached_payload is not None:
            return cached_payload, None
        
    count: Optional[int] = sub.get("hour_count")
    reset_at: Optional[datetime] = sub.get("hour_reset_at")

    if reset_at is None or now_kyiv >= reset_at:
        count = 0
        reset_at = now_kyiv + timedelta(hours=1)

    if (count or 0) >= 10:
        limit_msg = _build_limit_message(person_accnt, reset_at.isoformat() if reset_at else None)
        return None, limit_msg

    data = await fetch_status(session, str(person_accnt))
    if data:
        await update_subscription_payload(
            sub_id=sub["id"],
            hour_count=(count or 0) + 1,
            hour_reset_at=reset_at,
            payload=data,
        )
    return data, None


async def poll_loop(bot: Bot) -> None:
    """Background polling loop to check for schedule updates and notify users.

    Args:
        bot: The aiogram Bot instance to send messages.

    Returns:
        None
    """
    BASE_SLEEP = 600  # 10 minutes tick to catch updates without spamming
    kyiv = _kyiv_tz()

    while True:

        now_kyiv = datetime.now(kyiv)

        try:
            if now_kyiv.hour >= 21:
                now_kyiv += timedelta(days=1)
            schedule_date = now_kyiv.date()
            today_str = schedule_date.strftime("%Y-%m-%d")
            queues = await list_queues_with_payload_for_date(schedule_date)
            
            if not queues:
                await asyncio.sleep(BASE_SLEEP)
                continue

            async with aiohttp.ClientSession() as session:
                for row in queues:
                    queue_code = row.get("queue_code")
                    payload = row.get("payload")

                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except Exception:
                            pass

                    if queue_code is None:
                        continue

                    sched = await fetch_schedule(session, queue_code, today_str)
                    if not isinstance(sched, dict) or not sched:
                        continue

                    if payload != sched:
                        await upsert_fetch_schedule(queue_code, schedule_date, sched)
                        try:
                            aData_list: list[Dict[str, Any]] = sched.get("aData", [])
                            aState_map: Dict[str, Dict[str, Any]] = sched.get("aState", {})

                            if aData_list:
                                body_core = format_daily_schedule(aData_list, aState_map)
                            else:
                                continue                                

                            header = f"Графік на {today_str} для черги {queue_code}"
                            text = f"{header}\n\n{body_core}"
                            chat_ids = await list_chat_ids_by_queue(queue_code)
                            for cid in chat_ids:
                                try:
                                    await bot.send_message(chat_id=cid, text=text[:4000])
                                except Exception:
                                    pass
                        except Exception:
                            pass
        except Exception as ex:
            print(f"Exception in poll loop: {ex}")
            
        finally:
            await asyncio.sleep(BASE_SLEEP)