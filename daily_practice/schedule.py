"""Система дневных практик с расписанием."""
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict

from utils.storage import save_user_data, load_user_data
from daily_practice.daily_practices import DAILY_PRACTICES

logger = logging.getLogger(__name__)

# Часовой пояс Москвы (UTC+3)
MOSCOW_TZ = timezone(timedelta(hours=3))

# Время обновления практики (7:00 МСК)
UPDATE_HOUR = 7


def get_moscow_time() -> datetime:
    """Получает текущее время в Москве."""
    return datetime.now(MOSCOW_TZ)


def get_user_practice_day(user_id: int) -> int:
    """Получает номер дня практики для пользователя (начинается с 1)."""
    today = get_moscow_time()
    # Базовый день - 1 января 2024 года
    base_date = datetime(2024, 1, 1, tzinfo=MOSCOW_TZ)
    days_passed = (today.date() - base_date.date()).days
    return max(1, days_passed + 1)


def should_update_practice(user_id: int) -> bool:
    """Проверяет, нужно ли обновить практику для пользователя."""
    try:
        user_data = load_user_data(user_id, "daily_practice_schedule")
        
        if not user_data:
            return True
        
        last_update = datetime.fromisoformat(user_data.get("last_update", "2024-01-01T00:00:00"))
        last_update_moscow = last_update.replace(tzinfo=timezone.utc).astimezone(MOSCOW_TZ)
        
        today = get_moscow_time()
        last_update_date = last_update_moscow.date()
        today_date = today.date()
        
        # Обновляем если день изменился
        if last_update_date < today_date:
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Ошибка в should_update_practice: {e}")
        return True


async def get_next_practice(user_id: int) -> Optional[Dict]:
    """Получает следующую практику для пользователя."""
    if not should_update_practice(user_id):
        # Возвращаем текущую практику
        user_data = await load_user_data(user_id, "daily_practice_schedule")
        if user_data:
            return user_data.get("current_practice")
        return None
    
    # Определяем порядковый номер практики
    practice_day = get_user_practice_day(user_id)
    total_practices = len(DAILY_PRACTICES)
    
    # Вычисляем индекс практики (циклично)
    practice_index = (practice_day - 1) % total_practices
    
    # Получаем практику
    practice_data = DAILY_PRACTICES[practice_index + 1]  # +1 потому что словарь начинается с 1
    
    # Формируем результат
    result = {
        "practice_id": practice_index + 1,
        "practice_day": practice_day,
        "title": practice_data["title"],
        "instruction": practice_data["instruction"],
        "type": practice_data["type"],
        "difficulty": practice_data["difficulty"],
        "xp": practice_data["xp"],
        "date_assigned": get_moscow_time().isoformat(),
        "completed": False,
        "completed_at": None
    }
    
    # Сохраняем обновление
    await save_practice_schedule(user_id, result)
    
    logger.info(f"Выдана практика {practice_index + 1} пользователю {user_id}")
    return result


async def save_practice_schedule(user_id: int, practice_data: Dict) -> bool:
    """Сохраняет данные о практике пользователя."""
    schedule_data = {
        "user_id": user_id,
        "current_practice": practice_data,
        "last_update": get_moscow_time().isoformat(),
        "total_assigned": practice_data.get("practice_day", 1),
        "total_completed": 0
    }
    
    return await save_user_data(user_id, schedule_data, "daily_practice_schedule")


async def complete_practice(user_id: int) -> bool:
    """Отмечает практику как выполненную и обновляет статистику."""
    user_data = await load_user_data(user_id, "daily_practice_schedule")
    
    if not user_data or not user_data.get("current_practice"):
        return False
    
    current_practice = user_data["current_practice"]
    if current_practice.get("completed"):
        return False
    
    # Отмечаем как выполненную
    current_practice["completed"] = True
    current_practice["completed_at"] = get_moscow_time().isoformat()
    
    # Обновляем счетчики
    user_data["total_completed"] += 1
    
    success = await save_user_data(user_id, user_data, "daily_practice_schedule")
    
    # НОВОЕ: Обновляем статистику пользователя
    if success:
        await update_user_stats(user_id, current_practice)
        logger.info(f"Практика {current_practice['practice_id']} выполнена пользователем {user_id}")
    
    return success

async def get_user_practice_status(user_id: int) -> Dict:
    """
    Получение статуса дневной практики пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Dict: Статус практики с информацией о последнем выполнении
    """
    try:
        # Загружаем данные пользователя
        user_data = load_user_data()
        user_info = user_data.get(str(user_id), {})
        
        # Получаем историю практик (если есть)
        practice_history = user_info.get('practice_history', {})
        
        # Находим последнюю практику
        last_practice = None
        last_date = None
        
        for date_str, practice_data in practice_history.items():
            if practice_data.get('type') == 'daily_practice':
                practice_date = datetime.fromisoformat(date_str).date()
                
                if last_date is None or practice_date > last_date:
                    last_date = practice_date
                    last_practice = practice_data
        
        # Формируем ответ
        status = {
            'user_id': user_id,
            'has_practiced_today': False,
            'last_completion_date': None,
            'total_completions': len(practice_history),
            'current_streak': 0,  # Нужно реализовать подсчет стрика
            'last_practice': last_practice
        }
        
        # Проверяем, выполнялась ли практика сегодня
        today = get_moscow_time().date()
        if last_date == today:
            status['has_practiced_today'] = True
            if last_practice:
                status['last_completion_date'] = last_practice.get('completed_at')
        
        return status
        
    except Exception as e:
        logger.error(f"Ошибка получения статуса практики для пользователя {user_id}: {e}")
        return {
            'user_id': user_id,
            'has_practiced_today': False,
            'last_completion_date': None,
            'total_completions': 0,
            'current_streak': 0,
            'last_practice': None
        }

async def update_user_stats(user_id: int, practice_data: dict) -> bool:
    """Обновляет статистику пользователя после выполнения практики."""
    try:
        # Обновляем базовую статистику (существующий код)
        user_data = load_user_data()
        user_key = str(user_id)
        
        if user_key not in user_data:
            user_data[user_key] = {"stats": {}}
        
        if "stats" not in user_data[user_key]:
            user_data[user_key]["stats"] = {}
        
        stats = user_data[user_key]["stats"]
        
        # Обновляем статистику
        stats["total_practices"] = stats.get("total_practices", 0) + 1
        stats["xp_total"] = stats.get("xp_total", 0) + practice_data.get("xp", 5)
        stats["last_practice_date"] = practice_data.get("completed_at")
        stats["practice_types"] = stats.get("practice_types", {})
        
        practice_type = practice_data.get("type", "daily_practice")
        stats["practice_types"][practice_type] = stats.get(practice_type, 0) + 1
        
        # Сохраняем обновленные данные
        save_user_data(user_data)
        
        # НОВОЕ: Обновляем детализированную статистику
        from stats.user_stats import update_stats
        await update_stats(user_id, "daily_practice", practice_data)
        
        logger.info(f"Статистика обновлена для пользователя {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка обновления статистики: {e}")
        return False

async def get_user_stats(user_id: int, period: str = "total") -> dict:
    """Получает статистику пользователя за указанный период."""
    try:
        user_profile = await load_user_data(user_id)
        if not user_profile:
            return {"error": "Пользователь не найден"}
        
        stats = user_profile.get("profile", {}).get("stats", {})
        practice_history = stats.get("practice_history", [])
        
        if period == "total":
            return {
                "period": "Общая статистика",
                "total_practices": len(practice_history),
                "total_xp": stats.get("xp", 0),
                "current_level": stats.get("level", 0),
                "current_streak": stats.get("current_streak", 0),
                "by_difficulty": {
                    "easy": len([p for p in practice_history if p.get("difficulty") == "easy"]),
                    "medium": len([p for p in practice_history if p.get("difficulty") == "medium"]),
                    "hard": len([p for p in practice_history if p.get("difficulty") == "hard"])
                },
                "by_type": {}
            }
        
        # Фильтрация по дате для других периодов
        from datetime import datetime, timedelta
        now = get_moscow_time()
        
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now - timedelta(days=30)
        else:
            start_date = datetime.min
        
        filtered_practices = [
            p for p in practice_history 
            if datetime.fromisoformat(p["date"]) >= start_date
        ]
        
        return {
            "period": f"Статистика за {period}",
            "total_practices": len(filtered_practices),
            "total_xp": sum(p.get("xp", 0) for p in filtered_practices),
            "by_difficulty": {
                "easy": len([p for p in filtered_practices if p.get("difficulty") == "easy"]),
                "medium": len([p for p in filtered_practices if p.get("difficulty") == "medium"]),
                "hard": len([p for p in filtered_practices if p.get("difficulty") == "hard"])
            },
            "practices": filtered_practices[-10:]  # Последние 10 практик
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return {"error": "Ошибка получения статистики"}