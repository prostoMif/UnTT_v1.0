"""Пакет регистрации пользователей."""
from registration.registration import (
    RegistrationState,
    is_user_registered,
    start_registration,
    process_time_spent,
    process_purpose,
    process_likes,
    process_reduce_time,
    process_confirmation
)

__all__ = [
    "RegistrationState",
    "is_user_registered", 
    "start_registration",
    "process_time_spent",
    "process_purpose",
    "process_likes",
    "process_reduce_time",
    "process_confirmation"
]