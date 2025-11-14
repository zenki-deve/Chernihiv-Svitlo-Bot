"""Updates orchestration: caching, hourly rate limits, and background polling.

This module centralizes the logic for:
- Enforcing per-(chat_id, person_accnt) request budgets (5/hour) with
    single-window notifications during automated polling.
- Sharing a short-lived cache per person_accnt to deduplicate upstream calls
    across users and handlers.
- Periodically polling all enabled subscriptions, grouping by account to avoid
    redundant network requests, and broadcasting only meaningful changes.

Public functions
----------------
- try_fetch_with_limits: Fetches account data with cache and limits applied.
- poll_loop: Long-running background task that polls and notifies subscribers.
"""
import aiohttp
import asyncio
from aiogram import Bot
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Tuple, Dict, Any

from utils import format_entries
from utils.request import fetch_status, extract_aData, diff_payload
from database import (
    consume_request_budget,
    mark_limit_notified, 
    get_cached_account, 
    set_cached_account,
    get_enabled_subscriptions,
    set_last_payload_for_sub,
    get_last_payload_for_sub,
)


def _build_limit_message(person_accnt: str, hour_reset_at: Optional[str]) -> str:
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
    person_accnt: str,
    *,
    is_poll: bool = False,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Fetch account data with shared cache and rate limits applied.

    Contract
    - Input:
        session: An aiohttp session to reuse connections.
        chat_id: Telegram chat identifier to apply the request budget.
        person_accnt: The account code to fetch.
        is_poll: If True, send only one notification per window when a limit is hit.
    - Output:
        Returns a tuple (payload, error_message):
          - payload: Dict with upstream response on success, or None on error/limit.
          - error_message: Localized text to show to the user if a limit is exceeded;
            None when no message should be shown (e.g., already notified in-window).
    - Behavior:
        1) Uses a per-account cache (TTL 300s) to avoid redundant upstream calls.
          2) Enforces 5/hour per (chat_id, person_accnt) request budgets.
          3) During automated polling (is_poll=True), ensures only a single message is
              sent per hourly window about exceeded limits.
    """
    now_utc = datetime.utcnow()

    CACHE_TTL_SEC = 300
    cached = await get_cached_account(person_accnt)
    if cached:
        updated_at_raw = cached.get("updated_at")
        try:
            updated_dt = datetime.fromisoformat(updated_at_raw) if updated_at_raw else None
        except Exception:
            updated_dt = None
        if updated_dt and (now_utc - updated_dt).total_seconds() < CACHE_TTL_SEC:
            return cached.get("payload"), None
    res = await consume_request_budget(chat_id, person_accnt, now_utc)
    if not res.get("ok"):
        hour_reset_at = res.get("hour_reset_at")
        msg = _build_limit_message(person_accnt, hour_reset_at)
        if is_poll:
            already_hour = bool(res.get("hour_notified"))
            if already_hour:
                return None, None
            await mark_limit_notified(chat_id, person_accnt, "hour")
            return None, msg
        return None, msg

    data = await fetch_status(session, person_accnt)
    if data:
        await set_cached_account(person_accnt, data)
    return data, None


async def poll_loop(bot: Bot) -> None:
    """Dynamic background polling loop.

    Interval semantics:
      Each subscription can specify poll_interval_minutes (10-1440, default 30).
      For a given person_accnt shared by multiple users, the loop uses the
      minimum interval among its enabled subscriptions (clamped to [10, 1440])
      so that frequent subscribers benefit without over-polling the upstream.

    Fetch decision:
      We reuse the account cache timestamp (updated_at) to decide whether the
      effective interval has elapsed. If not elapsed, the account is skipped.

    Tick cadence:
      The loop wakes every BASE_SLEEP (5 minutes) to evaluate due accounts. This
      keeps resource usage modest while respecting short intervals like 10 min.
    """
    BASE_SLEEP = 600  # 10 minutes tick
    while True:
        start_cycle = datetime.utcnow()
        try:
            enabled = await get_enabled_subscriptions()
            if not enabled:
                await asyncio.sleep(BASE_SLEEP)
                continue
            by_account: dict[str, list[dict[str, Any]]] = {}
            for row in enabled:
                by_account.setdefault(row["person_accnt"], []).append(row)
            async with aiohttp.ClientSession() as session:
                for person_accnt, subs_rows in by_account.items():
                    raw_intervals = [int(r.get("poll_interval_minutes") or 30) for r in subs_rows]
                    effective = min(raw_intervals) if raw_intervals else 30
                    effective = max(10, min(1440, effective))  # clamp
                    cached = await get_cached_account(person_accnt)
                    should_fetch = True

                    if cached:
                        updated_raw = cached.get("updated_at")
                        try:
                            updated_dt = datetime.fromisoformat(updated_raw) if updated_raw else None
                        except Exception:
                            updated_dt = None

                        if updated_dt:
                            elapsed = (start_cycle - updated_dt).total_seconds() / 60.0
                            if elapsed < effective:
                                should_fetch = False

                    if not should_fetch:
                        continue

                    representative_chat = subs_rows[0]["chat_id"]
                    data, limit_msg = await try_fetch_with_limits(session, representative_chat, person_accnt, is_poll=True)

                    if limit_msg:
                        for r in subs_rows:
                            await bot.send_message(chat_id=r["chat_id"], text=limit_msg)
                        continue

                    if data is None:
                        continue
                    
                    for r in subs_rows:
                        sub_id = r["id"]
                        old = await get_last_payload_for_sub(sub_id)
                        if old != data:
                            a = extract_aData(data)
                            header = f"О/р {person_accnt},\n{r.get('name','')}"
                            body_core = format_entries(a) if a else diff_payload(old, data)
                            body = f"{header}\n\n{body_core}" if body_core else header
                            await bot.send_message(chat_id=r["chat_id"], text=body[:4000])
                            await set_last_payload_for_sub(sub_id, data)
        except Exception:
            pass
        finally:
            await asyncio.sleep(BASE_SLEEP)