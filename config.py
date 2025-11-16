"""Configuration and environment loading for the svitlo bot.

This module centralizes environment variable parsing and constants
so other modules can import from a single place.
"""

from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv


# Load variables from .env if present
load_dotenv()


def _require_env(name: str) -> str:
    """Return the value of the required environment variable or raise.

    Args:
        name: Environment variable name.

    Returns:
        The string value from the environment.

    Raises:
        ValueError: If the variable is missing or empty.
    """
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} is not set in environment variables")
    return value


API_TOKEN: str = _require_env("API_TOKEN")

DB_HOST: str = _require_env("DB_HOST")
DB_PORT: int = int(_require_env("DB_PORT"))
DB_NAME: str = _require_env("DB_NAME")
DB_USER: str = _require_env("DB_USER")
DB_PASSWORD: str = _require_env("DB_PASSWORD")

CACHE_SEC: int = int(_require_env("CACHE_SEC"))