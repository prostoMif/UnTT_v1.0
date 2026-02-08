"""Модуль SOS для восстановления осознанности после срыва."""
import logging
from typing import Optional
from datetime import datetime

# Импорт внешних модулей
from tree_progress.tree import TreeProgress
from daily_practice.daily_practices import get_daily_practice
from daily_practice.schedule import get_moscow_time
logger = logging.getLogger(__name__)


# Варианты дыхательных упражнений
BREATHING_EXERCISES = [
    {
        "name": "🌬️ Техника 4-7-8",
        "instruction": "Вдох 4 сек → Задержка 7 сек → Выдох 8 сек\n\nПовторите 3-4 цикла"
    },
    {
        "name": "🌊 Квадратное дыхание",
        "instruction": "Вдох 4 сек → Задержка 4 сек → Выдох 4 сек → Задержка 4 сек\n\nСделайте 5 квадратов"
    },
    {
        "name": "🍃 Глубокое дыхание",
        "instruction": "Медленный вдох через нос (5 сек)\nГлубокий выдох через рот (7 сек)\n\nПовторите 5 раз"
    }
]

# Мини-задачи для восстановления осознанности
MINI_TASKS = [
    "Выпейте стакан воды 🍵",
    "Сделайте 5 приседаний или потянитесь 🧘",
    "Посмотрите в окно и назовите 3 вещи, которые видите 👁️",
    "Сделайте 10 глубоких вдохов 🌬️",
    "Напишите 3 вещи, за которые благодарны 🙏",
    "Встаньте и пройдитесь по комнате 🚶",
    "Умойтесь холодной водой 💧",
    "Позвоните другу или близкому человеку 📞"
]

# Вопросы для осознанности
MINDFULNESS_QUESTIONS = [
    "Что я хочу почувствовать? 💭",
    "Какой момент сейчас? ⏰",
    "Что мне действительно нужно в этот момент? 🎯",
    "Как я себя чувствую физически? 🫀",
    "Что было триггером этого срыва? 🔍",
    "Чего я хочу от следующего часа? ⭐",
    "Какой будет мой следующий осознанный шаг? 🚀"
]


async def handle_sos(user_id: int, bot=None) -> dict:
    """Обработка SOS запроса."""
    try:
        # Обновляем статистику SOS - ВАЖНО!
        try:
            from stats.user_stats import update_stats
            await update_stats(user_id, "sos", {
                "timestamp": get_moscow_time().isoformat()
            })
            print(f"Статистика SOS обновлена для user_id {user_id}")
        except Exception as stats_error:
            print(f"Ошибка обновления статистики SOS: {stats_error}")
        
        # Отправляем поддерживающее сообщение
        sos_message = (
            "🆘 Я здесь, чтобы помочь.\n\n"
            "Помни:\n"
            "• Это нормально чувствовать сложности\n"
            "• Каждый шаг к осознанности - это победа\n"
            "• Ты не один в этом пути\n\n"
            "Сделай 3 глубоких вдоха. Ты справишься. 💪"
        )
        
        if bot:
            await bot.send_message(chat_id=user_id, text=sos_message)
        
        return {"success": True, "message": "SOS обработан"}
        
    except Exception as e:
        logger.error(f"Ошибка в handle_sos: {e}")
        return {"success": False, "error": str(e)}


async def _register_relapse(user_id: int) -> dict:
    """
    Регистрирует срыв пользователя.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        dict: Данные о срыве
    """
    result = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "type": "tiktok_relapse",
        "recovered": False
    }
    
    logger.info(f"Срыв зафиксирован для user_id: {user_id}")
    
    return result


async def get_sos_options(user_id: int) -> dict:
    """
    Возвращает все доступные варианты SOS.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        dict: Словарь с вариантами
    """
    import random
    
    # Выбираем случайные элементы
    breathing = random.choice(BREATHING_EXERCISES)
    task = random.choice(MINI_TASKS)
    question = random.choice(MINDFULNESS_QUESTIONS)
    
    return {
        "breathing": breathing,
        "mini_task": task,
        "mindfulness_question": question
    }


async def get_breathing_exercise() -> dict:
    """
    Возвращает случайное дыхательное упражнение.
    
    Returns:
        dict: Упражнение с названием и инструкцией
    """
    import random
    return random.choice(BREATHING_EXERCISES)


async def get_mini_task() -> str:
    """
    Возвращает случайную мини-задачу.
    
    Returns:
        str: Текст задачи
    """
    import random
    return random.choice(MINI_TASKS)


async def get_mindfulness_question() -> str:
    """
    Возвращает случайный вопрос для осознанности.
    
    Returns:
        str: Вопрос
    """
    import random
    return random.choice(MINDFULNESS_QUESTIONS)


async def complete_sos_exercise(user_id: int, exercise_type: str) -> dict:
    """
    Фиксирует выполнение SOS-упражнения.
    
    Args:
        user_id: ID пользователя
        exercise_type: Тип упражнения (breathing / mini_task / question)
    
    Returns:
        dict: Результат
    """
    result = {
        "user_id": user_id,
        "exercise_type": exercise_type,
        "completed": True,
        "timestamp": datetime.now().isoformat()
    }
    
    # Обновляем прогресс дерева (небольшой бонус за восстановление)
    tree = TreeProgress(user_id)
    grow_result = await tree.grow(xp_gain=2)  # Меньше XP, чем за полноценную практику
    result["xp_gained"] = 2
    result["tree_progress"] = grow_result
    
    logger.info(f"SOS упражнение '{exercise_type}' выполнено для user_id: {user_id}")
    
    return result


async def get_recovery_message() -> str:
    """
    Возвращает мотивационное сообщение для восстановления.
    
    Returns:
        str: Текст сообщения
    """
    messages = [
        "🌟 Каждый срыв — это возможность стать осознаннее. Вы уже на правильном пути!",
        "💪 Не сдавайтесь! Осознанность — это практика, а не совершенство.",
        "🌱 Ошибки — часть пути. Главное — вы снова здесь и готовы продолжать.",
        "⭐ Вы молодец, что вернулись. Маленький шаг — это тоже шаг вперёд!",
        "🌿 Срыв не определяет вас. Ваши усилия — вот что важно."
    ]
    
    import random
    return random.choice(messages)


async def get_sos_summary(user_id: int) -> dict:
    """
    Возвращает сводку по SOS для пользователя.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        dict: Статистика SOS
    """
    tree = TreeProgress(user_id)
    stats = tree.get_stats()
    
    return {
        "total_relapses_today": 1,  # Заглушка, в реальности считать из БД
        "current_streak": stats["streak"],
        "level": stats["level"],
        "recovery_needed": True,
        "message": await get_recovery_message()
    }