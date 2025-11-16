"""Low-level HTTP polling utilities for the upstream API."""

import json
import aiohttp
from typing import Dict, Any, Optional, List

API_URL_DISABLE = "https://interruptions.energy.cn.ua/api/info_disable"
API_URL_SCHEDULE = "https://interruptions.energy.cn.ua/api/info_schedule_part"
API_URL_QUEUE = "https://interruptions.energy.cn.ua/api/number_queue/"

async def fetch_status(session: aiohttp.ClientSession, person_accnt: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch the status (outage data) for a given personal account.

    Args:
        session: Shared aiohttp client session.
        person_accnt: Personal account identifier string.

    Returns:
        List of dicts from 'aData' when successful and status == 'ok', otherwise None.
    """
    try:
        async with session.post(
            API_URL_DISABLE,
            json={"person_accnt": person_accnt, "token": None},
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            
            if resp.status != 200:
                print("Response status not 200:", resp.status)
                return None
            
            data = await resp.json(content_type=None)
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    print("Failed to parse JSON string:", data)
                    return None
                
            if not isinstance(data, dict):
                print("Data is not a dict:", data)
                return None
            
            status_val = data.get("status")
            if status_val not in ("ok", "200", 200):
                print("Status not ok:", status_val)
                return None
            
            return extract_aData(data)
    except Exception:
        return None


async def fetch_queue(session: aiohttp.ClientSession, person_accnt: str) -> Optional[Dict[str, Any]]:
    """Fetch the queue information for a given personal account.

    Args:
        session: Shared aiohttp client session.
        person_accnt: Personal account identifier string.

    Returns:
        Parsed JSON dict when successful and status == 'ok', otherwise None.
    """
    try:
        async with session.post(
            API_URL_QUEUE,
            json={"search_param": person_accnt, "token": None},
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            
            if resp.status != 200:
                return None
            
            data = await resp.json()
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    return None
                
            if not isinstance(data, dict):
                return None
            
            status_val = data.get("status")
            if status_val not in ("ok", "200", 200):
                return None
            
            street = None
            queues = None

            for d in data.get("list_grp", []):
                first = d[0] if d and isinstance(d[0], dict) else {}
                street = first.get("adr_to") if first.get("adr_to") is not None else "Невідомо"
                q_val = first.get("queues") if first.get("queues") is not None else first.get("queue")
                queues = q_val if q_val is not None else "Невідомо"
                break
            
            return {"street": street, "queues": queues}
    except Exception:
        return None


async def fetch_schedule(session: aiohttp.ClientSession, queue: str, curr_dt: str) -> Optional[Dict[str, Any]]:
    """Fetch the interruption schedule details.

    Args:
        session: Shared aiohttp client session.
        queue: Queue identifier string.
        curr_dt: Date string in 'YYYY-MM-DD' format.

    Returns:
        Parsed JSON dict when successful and status == 'ok', otherwise None.
    """
    try:
        async with session.post(
            API_URL_SCHEDULE,
            json={"queue": queue, "curr_dt": curr_dt},
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
            
            status_val = data.get("status")
            if status_val not in ("ok", "200", 200):
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
