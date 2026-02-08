"""Пакет контента."""
from .daily_practices import get_daily_practice
from .schedule import get_next_practice, complete_practice, get_user_practice_status

__all__ = [
    "get_daily_practice",
    "get_next_practice", 
    "complete_practice",
    "get_user_practice_status"
]