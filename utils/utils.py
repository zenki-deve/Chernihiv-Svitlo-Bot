"""Utility helpers shared across bot modules."""

from aiogram import types
from typing import List, Dict, Any, Optional
import json


def cb_chat_id(call: types.CallbackQuery) -> int:
    """Extract the chat_id for a callback query reliably.

    Args:
        call: Incoming callback query object.

    Returns:
        Integer chat_id derived from the original message when available,
        otherwise from the user id. Returns 0 if not found.
    """
    if call.message and call.message.chat:
        return call.message.chat.id
    return call.from_user.id if call.from_user else 0


def format_entries(a: Any) -> str:
    """Format entries from 'aData' or similar structure into a human-readable string.
    
    Args:
        a: Input data which can be a dict with 'aData', a list of dicts, or a JSON string.
        
    Returns:
        A formatted string listing the entries, or "Немає записів" if none found.
    """
    try:
        if isinstance(a, str):
            try:
                import json as _json
                a = _json.loads(a)
            except Exception:
                return "Немає записів"
        if isinstance(a, dict):
            entries = a.get("aData")
            if not isinstance(entries, list):
                return "Немає записів"
        elif isinstance(a, list):
            entries = a
        else:
            return "Немає записів"
    except Exception:
        return "Немає записів"

    parts: List[str] = []
    for row in entries:
        if isinstance(row, str):
            try:
                import json as _json
                row = _json.loads(row)
            except Exception:
                continue
        if not isinstance(row, dict):
            continue
        cause = (row.get('cause') or '').strip()
        begin = (row.get('acc_begin') or '').strip()
        end = (row.get('accend_plan') or '').strip()
        parts.append(f"{cause}\nПочаток: {begin}\nЗакінчення: {end}\n~~~~~~~~~~~~~~~~~~~~~")
    return "\n".join(parts)


def format_daily_schedule(aData: List[Dict[str, Any]], aState: Dict[str, Dict[str, Any]]) -> str:
    """Format only outage intervals for the day, merging 2+3.

    Args:
        aData: List of schedule entries with 'from', 'to', 'queue' fields.
        aState: Mapping of queue states to their details (e.g. names).
        
    Returns:
        A formatted string listing only outage intervals, merged when contiguous.
    """
    def norm_str(x: Any) -> str:
        return (str(x) if x is not None else "").strip()

    items = [
        {
            "from": norm_str(r.get("time_from")),
            "to": norm_str(r.get("time_to")),
            "queue": str(r.get("queue")) if r.get("queue") is not None else "",
        }
        for r in aData
        if isinstance(r, dict)
    ]

    def time_key(t: str) -> tuple[int, int]:
        try:
            hh, mm = t.split(":")
            return (int(hh), int(mm))
        except Exception:
            return (0, 0)

    items.sort(key=lambda r: time_key(r["from"]))
    outage_name = (aState.get("3", {}) or {}).get("name") or "Відключення"
    parts: List[str] = []
    cur_outage_from: Optional[str] = None
    cur_outage_to: Optional[str] = None

    def flush_outage():
        nonlocal cur_outage_from, cur_outage_to
        if cur_outage_from and cur_outage_to:
            parts.append(f"{outage_name}\nПочаток: {cur_outage_from}\nЗакінчення: {cur_outage_to}\n~~~~~~~~~~~~~")
        cur_outage_from = None
        cur_outage_to = None

    for r in items:
        q = r["queue"]
        tf = r["from"]
        tt = r["to"]

        if q in {"2", "3"}:
            
            if cur_outage_from is None:
                cur_outage_from = tf
                cur_outage_to = tt

            else:
                if cur_outage_to == tf:
                    cur_outage_to = tt
                
                else:
                    flush_outage()
                    cur_outage_from = tf
                    cur_outage_to = tt
        else:

            flush_outage()

    flush_outage()

    if not parts:
        return "Відключень немає"
    return "\n".join(parts)
