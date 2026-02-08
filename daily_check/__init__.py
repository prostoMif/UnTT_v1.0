"""Пакет дневных проверок."""
# Не импортируем функции как атрибуты, будем вызывать через модуль
import  daily_check.check as check_module

# Экспортируем функции для удобства
quick_pause = check_module.quick_pause
daily_check = check_module.daily_check
save_daily_data = check_module.save_daily_data
save_pause_data = check_module.save_pause_data

__all__ = ["quick_pause", "daily_check", "save_daily_data", "save_pause_data" ]