"""Low-level HTTP polling utilities for the upstream API."""

import json
import aiohttp
from typing import Dict, Any, Optional, List

API_URL = "https://interruptions.energy.cn.ua/api/info_disable"

async def fetch_status(session: aiohttp.ClientSession, person_accnt: str) -> Optional[Dict[str, Any]]:
    """Fetch the current interruption status for a given personal account.

    Args:
        session: Shared aiohttp client session.
        person_accnt: Personal account identifier string.

    Returns:
        Parsed JSON dict when successful and status == 'ok', otherwise None.
    """
    try:
        async with session.post(
            API_URL,
            json={"person_accnt": person_accnt, "token": None},
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            
            if resp.status != 200:
                return None
            
            data = await resp.json(content_type=None)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    return None
                
            if not isinstance(data, dict):
                return None
            
            if data.get("status") != "ok":
                return None
            
            return data
    except Exception:
        return None


def extract_aData(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and normalize the 'aData' list from the API payload."""
    raw = payload.get("aData")
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    return []

def diff_payload(old: Optional[Dict[str, Any]], new: Dict[str, Any]) -> str:
    """Produce a human-readable diff between old and new payloads.

    The diff focuses on added/removed entries in aData and limits output size.
    """
    new_list = extract_aData(new)
    old_list = extract_aData(old) if old else []

    if not old_list and new_list:
        return "Получено новое расписание (" + str(len(new_list)) + " записей)."
    
    old_set = {json.dumps(o, sort_keys=True, ensure_ascii=False) for o in old_list}
    new_set = {json.dumps(n, sort_keys=True, ensure_ascii=False) for n in new_list}
    added = new_set - old_set
    removed = old_set - new_set
    lines = []

    if added:
        lines.append("Добавлено записей: " + str(len(added)))
        for a in list(added)[:5]:
            lines.append("+ " + a)

    if removed:
        lines.append("Удалено записей: " + str(len(removed)))
        for r in list(removed)[:5]:
            lines.append("- " + r)

    if not lines:
        lines.append("Изменений не обнаружено.")
        
    return "\n".join(lines)
