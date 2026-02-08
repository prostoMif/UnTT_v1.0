"""Модуль регистрации новых пользователей."""
import logging
from datetime import datetime
from typing import Optional

from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Импорт утилит
from utils.storage import save_user_data, load_user_data, user_exists

logger = logging.getLogger(__name__)


class RegistrationState(StatesGroup):
    """Состояния регистрации пользователя."""
    time_spent = State()      # Сколько времени в TikTok
    purpose = State()         # Зачем заходит в TikTok
    likes = State()          # Что нравится в TikTok
    reduce_time = State()     # Хочет ли сократить время
    confirm = State()        # Подтверждение данных


async def is_user_registered(user_id: int) -> bool:
    """Проверяет, зарегистрирован ли пользователь."""
    return await user_exists(user_id)


async def start_registration(message: types.Message, state: FSMContext) -> None:
    """Начинает процесс регистрации."""
    user = message.from_user
    
    await message.answer(
        f"Привет, {user.first_name}! 👋\n\n"
        "Давай познакомимся! Ответь на несколько вопросов, чтобы настроить бота под тебя.\n\n"
        "❓ <b>Вопрос 1/4:</b>\n"
        "Сколько времени ты проводишь в TikTok в день?\n"
        "Ответь примером: '2 часа', '30 минут', '5 минут'",
        parse_mode='HTML'
    )
    
    # Устанавливаем первое состояние
    await state.set_state(RegistrationState.time_spent)


async def process_time_spent(message: types.Message, state: FSMContext) -> None:
    """Обрабатывает ответ на первый вопрос."""
    user_id = message.from_user.id
    time_spent = message.text.strip()
    
    # Сохраняем первый ответ
    await state.update_data(time_spent=time_spent)
    
    await message.answer(
        "✅ Записал!\n\n"
        "❓ <b>Вопрос 2/4:</b>\n"
        "Почему ты заходишь в TikTok?\n"
        "Например: развлечение, обучение, скука, поиск информации",
        parse_mode='HTML'
    )
    
    await state.set_state(RegistrationState.purpose)


async def process_purpose(message: types.Message, state: FSMContext) -> None:
    """Обрабатывает ответ на второй вопрос."""
    purpose = message.text.strip()
    
    # Сохраняем второй ответ
    await state.update_data(purpose=purpose)
    
    await message.answer(
        "✅ Записал!\n\n"
        "❓ <b>Вопрос 3/4:</b>\n"
        "Что тебе больше всего нравится в TikTok?\n"
        "Расскажи коротко о любимом контенте",
        parse_mode='HTML'
    )
    
    await state.set_state(RegistrationState.likes)


async def process_likes(message: types.Message, state: FSMContext) -> None:
    """Обрабатывает ответ на третий вопрос."""
    likes = message.text.strip()
    
    # Сохраняем третий ответ
    await state.update_data(likes=likes)
    
    await message.answer(
        "✅ Записал!\n\n"
        "❓ <b>Последний вопрос 4/4:</b>\n"
        "Хочешь ли ты сократить время в TikTok?\n"
        "Ответь 'да' или 'нет' (можно с объяснением)",
        parse_mode='HTML'
    )
    
    await state.set_state(RegistrationState.reduce_time)


async def process_reduce_time(message: types.Message, state: FSMContext) -> None:
    """Обрабатывает ответ на четвертый вопрос."""
    reduce_time = message.text.strip()
    
    # Сохраняем четвертый ответ
    await state.update_data(reduce_time=reduce_time)
    
    # Получаем все данные
    user_data = await state.get_data()
    
    # Формируем сводку для подтверждения
    summary = (
        "📋 <b>Проверь свои данные:</b>\n\n"
        f"⏰ Время в TikTok: {user_data.get('time_spent', 'Не указано')}\n"
        f"🎯 Цель использования: {user_data.get('purpose', 'Не указано')}\n"
        f"❤️ Что нравится: {user_data.get('likes', 'Не указано')}\n"
        f"📉 Хочет сократить время: {user_data.get('reduce_time', 'Не указано')}\n\n"
        "Если всё верно, напиши 'да' для подтверждения.\n"
        "Если нужно что-то исправить, напиши 'нет'."
    )
    
    await message.answer(summary, parse_mode='HTML')
    await state.set_state(RegistrationState.confirm)


async def process_confirmation(message: types.Message, state: FSMContext) -> None:
    """Обрабатывает подтверждение регистрации."""
    user = message.from_user
    user_id = user.id
    confirmation = message.text.strip().lower()
    
    if confirmation in ['да', 'yes', 'подтверждаю', 'ок']:
        # Получаем все данные регистрации
        registration_data = await state.get_data()
        
        # Создаём полный профиль пользователя
        user_profile = {
            "user_id": user_id,
            "username": user.username or "",
            "first_name": user.first_name,
            "registration_date": datetime.now().isoformat(),
            "registration_answers": registration_data,
            "settings": {
                "daily_practice_reminder": True,
                "notifications_enabled": True,
                "language": "ru"
            },
            "stats": {
                "total_sessions": 0,
                "total_pause_count": 0,
                "total_daily_checks": 0,
                "current_streak": 0,
                "level": 0,
                "xp": 0
            }
        }
        
        # Сохраняем данные пользователя
        success = await save_user_data(user_id, user_profile, "profile")
        
        if success:
            await state.clear()
            
            await message.answer(
                "🎉 <b>Отлично! Регистрация завершена!</b>\n\n"
                "Теперь ты можешь использовать все функции бота:\n"
                "• ⏸️ Быстрая пауза перед TikTok\n"
                "• ✅ Дневные практики осознанности\n"
                "• 🆘 SOS при срыве\n\n"
                "Напиши /start чтобы начать!",
                parse_mode='HTML'
            )
            
            logger.info(f"Пользователь {user_id} успешно зарегистрирован")
        else:
            await message.answer(
                "❌ Произошла ошибка при сохранении данных. Попробуй позже."
            )
            
    elif confirmation in ['нет', 'no', 'отмена', 'исправить']:
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.\n"
            "Напиши /start чтобы начать заново."
        )
    else:
        await message.answer(
            "Пожалуйста, ответь 'да' для подтверждения или 'нет' для отмены."
        )


async def get_user_profile(user_id: int) -> Optional[dict]:
    """Возвращает профиль пользователя."""
    return await load_user_data(user_id, "profile")


async def update_user_stats(user_id: int, stats_update: dict) -> bool:
    """Обновляет статистику пользователя."""
    profile = await get_user_profile(user_id)
    if profile:
        profile["stats"].update(stats_update)
        return await save_user_data(user_id, profile, "profile")
    return False