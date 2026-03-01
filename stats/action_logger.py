"""
Модуль логирования действий пользователей.
База данных всех действий для аналитики и улучшений.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
ACTIONS_FILE = DATA_DIR / "actions_log.json"
ADMIN_ID = 5782224611

# Все типы действий
ACTION_TYPES = {
    # Quick Pause
    "go_tiktok": "Нажал 'Иду в TikTok'",
    "qp_reason_habit": "Причина: привычка",
    "qp_reason_fatigue": "Причина: усталость",
    "qp_reason_distraction": "Причина: отвлечение",
    "qp_reason_interest": "Причина: интерес",
    "qp_set_timer": "Выбрал 'Поставить таймер'",
    "qp_say_no": "Сказал 'Нет'",
    "qp_finish": "Нажал 'Я закончил'",
    "qp_timer_stay": "Остался в TikTok",
    "qp_stop": "Остановил таймер",
    
    # SOS
    "sos": "Использовал SOS",
    "sos_prio_work": "SOS: учёба/работа",
    "sos_prio_sleep": "SOS: сон",
    "sos_prio_sport": "SOS: спорт",
    "sos_prio_people": "SOS: друзья/семья",
    "sos_prio_hobby": "SOS: хобби",
    "sos_act_close": "SOS: закрыл TikTok",
    "sos_act_open": "SOS: открыл TikTok",
    
    # Статистика
    "stats": "Смотрел статистику",
    
    # Подписка
    "subscribe": "Открыл подписку",
    "pay_unlock": "Нажал 'Купить'",
    "manage_subscription": "Управление подпиской",
    
    # Навигация
    "tariffs": "Открыл тарифы",
    "help": "Открыл помощь",
    "back_to_menu": "Нажал 'Назад'",
    
    # Команды
    "cmd_start": "Команда /start",
    "cmd_menu": "Команда /menu",
}


def get_moscow_time():
    """Получить московское время."""
    import pytz
    return datetime.now(pytz.timezone('Europe/Moscow'))


def load_actions() -> Dict:
    """Загрузить лог действий."""
    if not ACTIONS_FILE.exists():
        return {"users": {}, "global_stats": {}}
    try:
        with open(ACTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"users": {}, "global_stats": {}}


def save_actions(data: Dict) -> None:
    """Сохранить лог действий."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(ACTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def log_action(user_id: int, action: str, details: Optional[Dict] = None) -> None:
    # Не логировать действия админа
    if user_id == ADMIN_ID:
        return    
    """
    Записать действие пользователя.
    
    Args:
        user_id: ID пользователя
        action: Тип действия (ключ из ACTION_TYPES)
        details: Дополнительные данные
    """
    data = load_actions()
    user_id_str = str(user_id)
    now = get_moscow_time()
    today = now.date().isoformat()
    hour = now.hour
    
    # Инициализация пользователя
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "actions": [],
            "action_counts": {},
            "hourly_stats": {},  # {hour: count}
            "daily_stats": {},   # {date: count}
            "first_action": now.isoformat(),
            "last_action": now.isoformat(),
            "total_actions": 0
        }
    
    user_data = data["users"][user_id_str]
    
    # Запись действия
    action_record = {
        "timestamp": now.isoformat(),
        "date": today,
        "hour": hour,
        "action": action,
        "action_name": ACTION_TYPES.get(action, action),
        "details": details or {}
    }
    
    user_data["actions"].append(action_record)
    user_data["total_actions"] += 1
    user_data["last_action"] = now.isoformat()
    
    # Счётчик действий
    user_data["action_counts"][action] = user_data["action_counts"].get(action, 0) + 1
    
    # Почасовая статистика
    user_data["hourly_stats"][str(hour)] = user_data["hourly_stats"].get(str(hour), 0) + 1
    
    # Дневная статистика
    user_data["daily_stats"][today] = user_data["daily_stats"].get(today, 0) + 1
    
    # Глобальная статистика
    if "global_stats" not in data:
        data["global_stats"] = {}
    
    data["global_stats"]["total_actions"] = data["global_stats"].get("total_actions", 0) + 1
    data["global_stats"][action] = data["global_stats"].get(action, 0) + 1
    
    # Глобальная почасовая
    if "hourly_stats" not in data["global_stats"]:
        data["global_stats"]["hourly_stats"] = {}
    data["global_stats"]["hourly_stats"][str(hour)] = data["global_stats"]["hourly_stats"].get(str(hour), 0) + 1
    
    save_actions(data)
    logger.info(f"[ACTION_LOG] user={user_id}, action={action}")


async def get_user_stats(user_id: int) -> Dict:
    """Получить статистику пользователя."""
    data = load_actions()
    user_id_str = str(user_id)
    
    if user_id_str not in data["users"]:
        return {}
    
    user = data["users"][user_id_str]
    
    # Самые частые действия
    top_actions = sorted(
        user["action_counts"].items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:10]
    
    # Часы пик
    hourly = user.get("hourly_stats", {})
    peak_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Вычислить дни с ботом
    first_action = datetime.fromisoformat(user["first_action"])
    days_with_bot = (get_moscow_time() - first_action).days + 1
    
    return {
        "total_actions": user["total_actions"],
        "days_with_bot": days_with_bot,
        "top_actions": [(ACTION_TYPES.get(a, a), c) for a, c in top_actions],
        "peak_hours": [(f"{h}:00", c) for h, c in peak_hours],
        "action_counts": user["action_counts"],
        "hourly_stats": hourly,
        "daily_stats": user.get("daily_stats", {}),
        "first_action": user["first_action"],
        "last_action": user["last_action"]
    }


async def get_global_stats() -> Dict:
    """Получить глобальную статистику."""
    data = load_actions()
    users = data.get("users", {})
    global_stats = data.get("global_stats", {})
    
    # Активные пользователи сегодня
    today = get_moscow_time().date().isoformat()
    active_today = sum(
        1 for u in users.values() 
        if today in u.get("daily_stats", {})
    )
    
    # Активные за неделю
    week_ago = (get_moscow_time() - timedelta(days=7)).date().isoformat()
    active_week = sum(
        1 for u in users.values() 
        if any(d >= week_ago for d in u.get("daily_stats", {}).keys())
    )
    
    # Всего пользователей
    total_users = len(users)
    
    # Глобальные часы пик
    global_hourly = global_stats.get("hourly_stats", {})
    global_peak_hours = sorted(global_hourly.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Топ действий
    top_global = sorted(
        [(k, v) for k, v in global_stats.items() if k not in ("total_actions", "hourly_stats")],
        key=lambda x: x[1],
        reverse=True
    )[:15]
    
    return {
        "total_users": total_users,
        "total_actions": global_stats.get("total_actions", 0),
        "active_today": active_today,
        "active_week": active_week,
        "top_actions": [(ACTION_TYPES.get(a, a), c) for a, c in top_global],
        "peak_hours": [(f"{h}:00", c) for h, c in global_peak_hours]
    }


async def format_user_report(user_id: int) -> str:
    """Форматировать отчёт по пользователю."""
    stats = await get_user_stats(user_id)
    
    if not stats:
        return "Нет данных о пользователе."
    
    lines = [
        f"📊 Статистика пользователя {user_id}",
        "",
        f"Всего действий: {stats['total_actions']}",
        f"Дней с ботом: {stats['days_with_bot']}",
        f"Первый визит: {stats['first_action'][:10]}",
        f"Последний визит: {stats['last_action'][:10]}",
        "",
        "🔝 Топ действий:"
    ]
    
    for action, count in stats["top_actions"]:
        lines.append(f"  {action}: {count}")
    
    lines.extend(["", "🕐 Часы активности:"])
    for hour, count in stats["peak_hours"]:
        lines.append(f"  {hour} — {count} действий")
    
    return "\n".join(lines)


async def format_global_report() -> str:
    """Форматировать глобальный отчёт."""
    stats = await get_global_stats()
    
    lines = [
        "🌐 Глобальная статистика",
        "",
        f"Всего пользователей: {stats['total_users']}",
        f"Всего действий: {stats['total_actions']}",
        f"Активных сегодня: {stats['active_today']}",
        f"Активных за неделю: {stats['active_week']}",
        "",
        "🔝 Топ действий (все пользователи):"
    ]
    
    for action, count in stats["top_actions"]:
        lines.append(f"  {action}: {count}")
    
    lines.extend(["", "🕐 Часы пик (все пользователи):"])
    for hour, count in stats["peak_hours"]:
        lines.append(f"  {hour} — {count} действий")
    
    return "\n".join(lines)


# Команда для админа
ADMIN_ID = 5782224611  # Твой ID


async def handle_action_logger_command(message, user_id: int) -> str:
    """Обработать команду /action_logger."""
    if user_id != ADMIN_ID:
        return "Нет доступа."
    
    # Проверяем аргументы
    args = message.text.split()
    
    if len(args) == 1:
        # Общая статистика
        return await format_global_report()
    
    elif len(args) == 2:
        # Конкретный пользователь
        try:
            target_id = int(args[1])
            return await format_user_report(target_id)
        except ValueError:
            return "Неверный формат ID"
    
    else:
        return "Использование:\n/action_logger — общая статистика\n/action_logger <user_id> — статистика пользователя"