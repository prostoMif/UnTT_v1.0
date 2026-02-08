"""Модуль дневных проверок и практик осознанности."""
import logging
from typing import Optional
from datetime import datetime

# Импорт внешних модулей
from tree_progress.tree import TreeProgress
from daily_practice.daily_practices import get_daily_practice
from utils.storage import save_user_data, load_user_data
from daily_practice.schedule import get_moscow_time

logger = logging.getLogger(__name__)


async def quick_pause(user_id: int, bot=None) -> dict:
    """
    Чек-ин перед использованием TikTok.
    
    Задаёт вопросы:
    - "Зачем я открываю TikTok?"
    - "Сколько минут планирую?"
    
    При подтверждении сохраняет ответы и вызывает TreeProgress.grow().
    
    Args:
        user_id: ID пользователя Telegram
        bot: Экземпляр бота для отправки сообщений (опционально)
    
    Returns:
        dict: Результат чек-ина с ответами пользователя
    """
    result = {
        "user_id": user_id,
        "purpose": None,
        "planned_minutes": None,
        "confirmed": False,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"quick_pause вызван для user_id: {user_id}")
    
    # Если бот передан, можно отправить приветственное сообщение
    if bot:
        await bot.send_message(
            chat_id=user_id,
            text="⏸️ <b>Чек-ин перед TikTok</b>\n\n"
                 "Перед тем как погрузиться в ленту, ответьте на два вопроса:\n\n"
                 "1️⃣ <b>Зачем я открываю TikTok?</b>\n"
                 "   (развлечение / поиск информации / скука / другое)\n\n"
                 "2️⃣ <b>Сколько минут планирую провести?</b>",
            parse_mode='HTML'
        )
    
    # В реальной реализации здесь был бы FSM для получения ответов
    # Пока возвращаем заглушку с примером данных
    logger.info(f"quick_pause завершён для user_id: {user_id}")
    
    return result


async def daily_check(user_id: int, bot=None) -> dict:
    """Дневная мини-практика осознанности."""
    result = {
        "user_id": user_id,
        "day_reflection": None,
        "practice_completed": False,
        "practice_type": None,
        "mood_before": None,
        "mood_after": None,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"daily_check вызван для user_id: {user_id}")
    
    # Получаем микро-практику на сегодня
    day = datetime.now().day
    if day > 30:
        day = 30
    daily_practice = get_daily_practice(day)
    
    # Если бот передан, отправляем приветствие и практику
    if bot:
        await bot.send_message(
            chat_id=user_id,
            text="📊 <b>Дневная отметка</b>\n\n"
                 "Подведём итоги дня!\n\n"
                 f"🌿 <b>Микро-практика на сегодня:</b>\n"
                 f"{daily_practice['title']}\n\n"
                 f"{daily_practice['instruction']}\n\n"
                 "---",
            parse_mode='HTML'
        )
    
    logger.info(f"daily_check завершён для user_id: {user_id}")
    
    return result

async def save_pause_data(user_id: int, data: dict) -> bool:
    """
    Сохраняет данные чек-ина перед TikTok.
    
    Args:
        user_id: ID пользователя
        data: Данные для сохранения
    
    Returns:
        bool: Успех операции
    """
    try:
        storage_key = f"quick_pause_{user_id}"
        await save_user_data(storage_key, data)
        logger.info(f"Данные quick_pause сохранены для user_id: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения quick_pause: {e}")
        return False




async def load_last_pause(user_id: int) -> Optional[dict]:
    """
    Загружает последний чек-ин перед TikTok.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        dict или None: Данные последнего чек-ина
    """
    try:
        storage_key = f"quick_pause_{user_id}"
        return await load_user_data(storage_key)
    except Exception as e:
        logger.error(f"Ошибка загрузки quick_pause: {e}")
        return None

async def save_daily_data(user_id: int, data: dict) -> bool:
    """Сохранение данных дневной практики с историей."""
    try:
        # Загружаем существующие данные
        user_data = load_user_data()
        user_key = str(user_id)
        
        if user_key not in user_data:
            user_data[user_key] = {}
        
        # Добавляем запись в историю
        current_time = get_moscow_time()
        date_key = current_time.date().isoformat()
        
        if 'practice_history' not in user_data[user_key]:
            user_data[user_key]['practice_history'] = {}
        
        user_data[user_key]['practice_history'][date_key] = {
            'type': 'daily_practice',
            'completed_at': current_time.isoformat(),
            'data': data
        }
        
        # Сохраняем обновленные данные
        save_user_data(user_data)
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения данных практики: {e}")
        return False

async def load_last_daily_check(user_id: int) -> Optional[dict]:
    """
    Загружает последнюю дневную практику.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        dict или None: Данные последней практики
    """
    try:
        storage_key = f"daily_check_{user_id}"
        return await load_user_data(storage_key)
    except Exception as e:
        logger.error(f"Ошибка загрузки daily_check: {e}")
        return None