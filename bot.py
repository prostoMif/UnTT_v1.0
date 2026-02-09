import os
import logging
import asyncio
import json

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv
import re

# Импорт функций из модулей
from daily_check.check import quick_pause, daily_check
from sos.sos import handle_sos
# from registration import (
#     RegistrationState,
#     is_user_registered,
#     start_registration,
#     process_time_spent,
#     process_purpose,
#     process_likes,
#     process_reduce_time,
#     process_confirmation
# )
from daily_check.check import save_pause_data, save_daily_data
from daily_practice import get_next_practice, complete_practice, get_user_practice_status
from daily_practice import get_daily_practice
from tree_progress.tree import TreeProgress
from daily_practice.schedule import get_user_stats, update_user_stats
from datetime import datetime
from daily_check.check import save_daily_data
from scheduler import start_reminder_system, stop_reminder_system
from scheduler import MOSCOW_TZ, get_moscow_time
from stats.user_stats import update_stats, get_stats
from registration import is_user_registered



# ... (импорты)

# Состояния для диалога
class QuickPauseStates(StatesGroup):
    waiting_purpose = State()      # Ожидаем ответ "зачем открываешь TikTok"
    waiting_time = State()         # Ожидаем ответ "сколько времени"
    confirmation = State()         # Ожидаем подтверждение

class DailyCheckStates(StatesGroup):
    waiting_reflection = State()
    waiting_practice = State()

# НОВЫЕ СОСТОЯНИЯ ДЛЯ SOS
class SosStates(StatesGroup):
    waiting_priority = State()     # Шаг 1: Что важнее?
    waiting_confirmation = State()  # Шаг 2: Открыть или закрыть?   
class DailyPracticeStates(StatesGroup):
    waiting_reflection = State()
    waiting_practice_completion = State()
    
# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Создание экземпляров бота и диспетчера с FSM
from aiogram.fsm.storage.memory import MemoryStorage
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

active_timers = {}


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создание главного меню с кнопками"""
    keyboard = [
        [
            InlineKeyboardButton(text="Иду в Tik Tok", callback_data="quick_pause"),
            # InlineKeyboardButton(text=" Дневная практика", callback_data="daily_practice")
            InlineKeyboardButton(text=" SOS", callback_data="sos")
        ],
        [
            # InlineKeyboardButton(text=" Дерево прогресса", callback_data="tree_progress"),
            InlineKeyboardButton(text=" Статистика", callback_data="stats")
        ]
        
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
    pass 

def parse_duration(text: str) -> int:
    """
    Парсит текст и возвращает количество минут.
    Примеры: "5 минут", "1 час", "30", "0.5 ч"
    """
    text = text.lower().strip()
    
    # Проверяем на часы
    match_hour = re.search(r'(\d+\.?\d*)\s*(час|ч|h)', text)
    if match_hour:
        return int(float(match_hour.group(1)) * 60)
    
    # Проверяем на минуты или просто число
    match_min = re.search(r'(\d+\.?\d*)', text)
    if match_min:
        return int(float(match_min.group(1)))
        
    return None

async def save_user_preference(user_id: int, preference: str):
    """Сохраняет предпочтение пользователя в JSON файл."""
    file_path = "data/user_preferences.json"
    
    # Загружаем существующие данные
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}
    else:
        data = {}
    
    # Обновляем данные (используем str(user_id) как ключ)
    data[str(user_id)] = preference
    
    # Создаем папку data, если её нет
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Сохраняем обратно в файл
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

async def get_user_preference(user_id: int) -> str:
    """Получает сохраненное предпочтение пользователя (если нужно)."""
    file_path = "data/user_preferences.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(str(user_id))
        except (json.JSONDecodeError, IOError):
            return None
    return None


@dp.message(Command("unstart"))
async def cmd_unstart(message: types.Message):
    """Сброс регистрации и прогресса для повторного прохождения."""
    user_id = message.from_user.id
    
    # 1. Удаляем предпочтения
    pref_file_path = "data/user_preferences.json"
    if os.path.exists(pref_file_path):
        try:
            with open(pref_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}
        else:
            if str(user_id) in data:
                del data[str(user_id)]
                os.makedirs(os.path.dirname(pref_file_path), exist_ok=True)
                with open(pref_file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)

    # 2. Удаляем файл прогресса дерева
    tree_file_path = f"data/tree_{user_id}.json"
    if os.path.exists(tree_file_path):
        try:
            os.remove(tree_file_path)
        except Exception as e:
            logger.error(f"Ошибка удаления файла дерева: {e}")

    # 3. Удаляем файл статистики (ВАЖНО для исправления проблемы с 0)
    # Путь зависит от реализации load_user_data, обычно это data/user_stats_{user_id}.json
    stats_file_path = f"data/user_stats_{user_id}.json"
    if os.path.exists(stats_file_path):
        try:
            os.remove(stats_file_path)
        except Exception as e:
            logger.error(f"Ошибка удаления файла статистики: {e}")

    await message.answer("🗑 Твоя запись, прогресс дерева и статистика удалены. Теперь ты можешь начать с чистого листа командой /start")


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Обработка команды /start"""
    user_id = message.from_user.id
    
    # Если нужна проверка на регистрацию (файл users.py не показан, но логика сохраняется):
    if await is_user_registered(user_id): 
        await message.answer("С возвращением!", reply_markup=get_main_keyboard())
        return

    # Шаг 1: Первое сообщение
    await message.answer(
        "UnTT.\n"
        "Этот бот помогает замечать моменты перед TikTok.\n"
        "Ты решаешь, что делать дальше.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Начать", callback_data="onboarding_start"),
                InlineKeyboardButton(text="Как это работает", callback_data="onboarding_info")
            ]
        ])
    )

# Хэндлер для кнопки "Как это работает" (Шаг 3)
@dp.callback_query(F.data == "onboarding_info")
async def callback_onboarding_info(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Когда рука тянется к TikTok, ты заходишь сюда первым.\n"
        "UnTT спрашивает: зачем сейчас, сколько времени.\n"
        "Ты отвечаешь. Дерево отмечает выбор.\n"
        "Только первые 5 дней. Дальше — по твоему решению.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Понял", callback_data="onboarding_understood")]
        ])
    )
    await callback.answer()

# Хэндлер для кнопки "Понял" и "Начать" (Переход к Шагу 4)
@dp.callback_query(F.data.in_(["onboarding_start", "onboarding_understood"]))
async def callback_onboarding_next(callback: types.CallbackQuery):
    """Показывает мини-регистрацию"""
    await callback.message.edit_text(
        "Где TikTok чаще всего забирает время?\n"
        "(Это поможет настроить напоминания.)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Перед сном", callback_data="reg_sleep"),
                InlineKeyboardButton(text="Днём, вместо дел", callback_data="reg_day")
            ],
            [
                InlineKeyboardButton(text="Вечером, когда один", callback_data="reg_evening"),
                InlineKeyboardButton(text="Пропустить", callback_data="reg_skip")
            ]
        ])
    )
    await callback.answer()

# Хэндлер завершения мини-регистрации (Шаг 4 -> Шаг 2)
@dp.callback_query(F.data.in_(["reg_sleep", "reg_day", "reg_evening", "reg_skip"]))
async def callback_finish_onboarding(callback: types.CallbackQuery):
    """Сохраняет выбор (опционально) и показывает главное меню"""
    # Здесь можно сохранить callback_data в БД, если нужно
    await save_user_preference(callback.from_user.id, callback.data)
    
    await callback.message.edit_text(
        "Запомнил.\n\n"
        "Теперь главное меню."
    )
    
    # Шаг 2: Приветствие после старта
    await callback.message.answer(
        "Ты здесь.\n"
        "Когда соберёшься открыть TikTok, нажми кнопку ниже.\n"
        "unTT покажет этот момент.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()



# # Обработчики состояний регистрации
# @dp.message(RegistrationState.time_spent)
# async def registration_time_spent(message: types.Message, state: FSMContext):
#     await process_time_spent(message, state)

# @dp.message(RegistrationState.purpose)
# async def registration_purpose(message: types.Message, state: FSMContext):
#     await process_purpose(message, state)

# @dp.message(RegistrationState.likes)
# async def registration_likes(message: types.Message, state: FSMContext):
#     await process_likes(message, state)

# @dp.message(RegistrationState.reduce_time)
# async def registration_reduce_time(message: types.Message, state: FSMContext):
#     await process_reduce_time(message, state)

# @dp.message(RegistrationState.confirm)
# async def registration_confirm(message: types.Message, state: FSMContext):
#     await process_confirmation(message, state)


@dp.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Обработка команды /help"""
    help_text = (
        "📚 <b>Справка по боту</b>\n\n"
        "Доступные команды:\n"
        "• /start - Главное меню\n"
        "• /help - Эта справка\n"
        "• /cancel - Отмена текущего действия\n\n"
        "Функции кнопок:\n"
        "• ⏸️ <b>Быстрая пауза</b> - Чек-ин перед TikTok\n"
        "• 📚 <b>Дневная практика</b> - Рефлексия дня + осознанная практика\n"
        "• 🆘 <b>SOS</b> - Экстренная помощь\n\n"
        "📚 <b>Дневная практика включает:</b>\n"
        "• Рефлексию дня\n"
        "• Осознанную практику (из 52 вариантов)\n"
        "• Обновляется каждый день в 7:00 МСК\n"
        "• Награда XP за выполнение"
    )
    await message.answer(help_text, parse_mode='HTML')

async def quick_pause_timer_with_finish(user_id: int, minutes: int, bot: Bot):
    """Фоновая задача: ждет время и напоминает с кнопкой 'Я закончил'."""
    try:
        await asyncio.sleep(minutes * 60)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Я закончил", callback_data="qp_finish"),
                InlineKeyboardButton(text="Я остаюсь", callback_data="qp_timer_stay_action")
             ]
        ])
        
        await bot.send_message(
            chat_id=user_id,
            text=f"Твои {minutes} минут прошли.\n\n"
                 "Ты всё ещё в приложении?",
            reply_markup=keyboard
        )
    except asyncio.CancelledError:
        # Таймер был отменен (нажали "Я закончил")
        pass
    finally:
        # Удаляем себя из списка активных при завершении или отмене
        if user_id in active_timers:
            del active_timers[user_id]

# --- НОВАЯ ЛОГИКА "ИДУ В TIKTOK" ---

@dp.callback_query(F.data == "quick_pause")
async def callback_quick_pause_start(callback: types.CallbackQuery, state: FSMContext):
    """Старт сценария: Сообщение 1 и 2"""
    # Учитываем попытку в статистике
    try:
        from stats.user_stats import update_stats
        await update_stats(callback.from_user.id, "tiktok_attempt")
    except Exception as e:
        logger.error(f"Ошибка статистики (attempt): {e}")

    # Сообщение 1
    await callback.message.edit_text("Ты собираешься открыть TikTok.")
    
    # Пауза (имитация) и Сообщение 2
    await asyncio.sleep(1.5) # Небольшая пауза для атмосферы
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Привычка", callback_data="qp_reason_habit"),
            InlineKeyboardButton(text="Усталость", callback_data="qp_reason_fatigue")
        ],
        [
            InlineKeyboardButton(text="Отвлечься от дел", callback_data="qp_reason_distraction"),
            InlineKeyboardButton(text="Просто интересно", callback_data="qp_reason_interest")
        ]
    ])
    
    await callback.message.answer("Что за этим сейчас стоит?", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("qp_reason_"))
async def callback_quick_pause_reason(callback: types.CallbackQuery, state: FSMContext):
    """Обработка причины: Запрашиваем время в текстовом формате."""
    reason_code = callback.data.split("_")[-1]
    reasons_map = {
        "habit": "привычка",
        "fatigue": "усталость",
        "distraction": "отвлечение",
        "interest": "интерес"
    }
    reason_text = reasons_map.get(reason_code, "причина")
    
    # Сохраняем причину
    await state.update_data(reason=reason_text)
    
    await callback.message.edit_text(f"Сейчас за TikTok стоит: {reason_text}.")
    
    # Просим ввести время текстом
    await asyncio.sleep(0.5)
    await callback.message.answer(
        "Сколько времени ты готов отдать этому прямо сейчас?\n"
        "Напиши в формате: 15 минут, 1 час или просто 30."
    )
    
    # Устанавливаем состояние ожидания текста
    await state.set_state(QuickPauseStates.waiting_time)
    await callback.answer()
    
@dp.message(QuickPauseStates.waiting_time)
async def process_time_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод времени пользователем."""
    user_text = message.text
    minutes = parse_duration(user_text)
    
    if minutes is None or minutes <= 0:
        await message.answer("Пожалуйста, напиши время корректно. Например: 5 минут или 1 час.")
        return
    
    user_id = message.from_user.id
    start_time = datetime.now()
    
    # Сохраняем данные в состояние
    await state.update_data(
        planned_minutes=minutes,
        start_time=start_time.isoformat()
    )
    
    # Запускаем таймер и сохраняем ссылку на задачу
    task = asyncio.create_task(quick_pause_timer_with_finish(user_id, minutes, message.bot))
    active_timers[user_id] = task
    
    # Кнопка "Я закончил"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Я закончил", callback_data="qp_finish")]
    ])
    
    await message.answer(
        f"Ты выбираешь {minutes} минут.\n\n"
        f"Когда время закончится, я напомню об этом.",
        reply_markup=keyboard
    )
    
    # Сбрасываем состояние, чтобы не ловить лишние сообщения, 
    # но данные сохраняем в state через update_data выше
    await state.clear()

@dp.callback_query(F.data == "qp_finish")
async def callback_quick_pause_finish(callback: types.CallbackQuery, state: FSMContext):
    """Пользователь нажал 'Я закончил'."""
    user_id = callback.from_user.id
    
    # Проверяем, есть ли активный таймер и отменяем его
    if user_id in active_timers:
        task = active_timers[user_id]
        if not task.done():
            task.cancel() # Останавливаем фоновую задачу
        del active_timers[user_id]
    
    # ВОССТАНОВЛЕННАЯ ЛОГИКА: Получаем данные и вычисляем время
    data = await state.get_data()
    start_time_str = data.get("start_time")
    planned_minutes = data.get("planned_minutes", 0)
    
    actual_minutes = 0
    time_text = "Некоторое время."
    
    if start_time_str:
        try:
            start_dt = datetime.fromisoformat(start_time_str)
            now_dt = datetime.now()
            delta_seconds = (now_dt - start_dt).total_seconds()
            actual_minutes = int(delta_seconds // 60)
            if actual_minutes < 1:
                time_text = "Меньше минуты."
            else:
                time_text = f"{actual_minutes} мин."
        except Exception:
            pass
    # КОНЕЦ ВОССТАНОВЛЕННОЙ ЛОГИКИ

    # Формируем сообщение с похвалой
    praise = "Ты вернулся в реальность."
    
    if planned_minutes > 0 and actual_minutes < planned_minutes:
        praise = (
            f"Ты провел {time_text} "
            f"вместо запланированных {planned_minutes} мин. "
            f"Это победа над привычкой."
        )
    elif actual_minutes > 0:
        praise = f"Ты провел в TikTok {time_text}. Хорошо, что ты вернулся."
    
    try:
        # Обновляем статистику
        from stats.user_stats import update_stats
        await update_stats(user_id, "conscious_stop")
    except Exception as e:
        logger.error(f"Ошибка статистики: {e}")

    await callback.message.edit_text(
        f"{praise}\n\n"
        "Дерево отмечает этот выбор."
    )
    
    await callback.message.answer( reply_markup=get_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("qp_time_"))
async def callback_quick_pause_time(callback: types.CallbackQuery):
    """Обработка выбора времени"""
    time_code = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    
    if time_code == "none":
        # Ветка: "Сегодня нет"
        await callback.message.edit_text("Сегодня TikTok остаётся закрытым.")
        await asyncio.sleep(1)
        await callback.message.answer("Этот день пойдёт в рост дерева.")
        
        # Статистика: Осознанное решение + Рост дерева
        try:
            from stats.user_stats import update_stats
            from tree_progress.tree import TreeProgress
            await update_stats(user_id, "conscious_stop")
            tree = TreeProgress(user_id)
            # БЫЛО: await tree.add_completion(xp_gain=5)
            # СТАЛО:
            result = await tree.add_day()
            
            # Можно добавить тихое уведомление о смене уровня, если нужно
            # Но в рамках "тихого" стиля лучше оставить просто эмодзи дерева
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса: {e}")
            
        await callback.message.answer( reply_markup=get_main_keyboard())
        await callback.answer()
        
    else:
        # Ветка: 5 / 15 / 30 минут
        minutes = int(time_code)
        await callback.message.edit_text(f"Ты выбираешь {minutes} минут.")
        await asyncio.sleep(1)
        await callback.message.answer("Когда время закончится, я напомню об этом.")
        
        # Запуск таймера в фоне
        asyncio.create_task(quick_pause_timer_with_finish(user_id, minutes, callback.bot))
        await callback.answer()




@dp.callback_query(F.data.startswith("qp_timer_close_"))
async def callback_quick_pause_timer_close(callback: types.CallbackQuery):
    """Таймер истек, пользователь выбрал 'Закрыть TikTok'"""
    user_id = callback.from_user.id
    # minutes = int(callback.data.split("_")[-1]) # Можно использовать для логов
    
    await callback.message.edit_text("Ты остановился там, где обычно продолжаешь.")
    await asyncio.sleep(1)
    await callback.message.answer("Этот день пойдёт в рост дерева.")
    
    # Статистика: Осознанное решение + Рост дерева
    try:
        from stats.user_stats import update_stats
        from tree_progress.tree import TreeProgress
        await update_stats(user_id, "conscious_stop")
        tree = TreeProgress(user_id)
        if tree.load():
            await tree.add_completion(xp_gain=5)
    except Exception as e:
        logger.error(f"Ошибка обновления прогресса: {e}")

    await callback.message.answer( reply_markup=get_main_keyboard())
    await callback.answer()



@dp.callback_query(F.data.startswith("qp_timer_stay_"))
async def callback_quick_pause_timer_stay(callback: types.CallbackQuery):
    """Таймер истек, пользователь выбрал 'Остаться'"""
    user_id = callback.from_user.id
    
    await callback.message.edit_text("Сегодня ты решил остаться в ленте.")
    await asyncio.sleep(1)
    await callback.message.answer("Мы просто отметим этот момент.")
    
    # Статистика: только фиксация (без осознанного решения и роста)
    # Метрика 'tiktok_attempt' уже была добавлена в начале.
    
    # Проверка на 3 срыва
    try:
        from stats.user_stats import UserStats
        stats = UserStats(user_id)
        if stats.data is None:
            stats.data = await stats._load_stats()
            
        slips_count = await stats.increment_slip()
        
        if slips_count == 3:
            await asyncio.sleep(0.5)
            await callback.message.answer("Это уже третий раз за сегодня.")
            
    except Exception as e:
        logger.error(f"Ошибка проверки срывов: {e}")

    await callback.message.answer( reply_markup=get_main_keyboard())
    await callback.answer()

    
@dp.callback_query(F.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
    """Обработка кнопки 'Статистика' в стиле Зеркала."""
    user_id = callback.from_user.id
    
    try:
        from stats.user_stats import get_stats
        from tree_progress.tree import TreeProgress
        
        # 1. Данные за сегодня
        today_stats = await get_stats(user_id, "today")
        attempts = today_stats.get("events_count", {}).get("tiktok_attempt", 0)
        conscious = today_stats.get("events_count", {}).get("conscious_stop", 0)
        
        # 2. Данные за неделю
        week_stats = await get_stats(user_id, "week")
        week_conscious = week_stats.get("events_count", {}).get("conscious_stop", 0)
        
        # Вычисляем "осознанные дни" (дни, когда было хотя бы одно осознанное решение)
        # Для MVP берем количество событий как ориентир или заглушку, если нет точной логики дат
        # Здесь используем упрощенный подход: события == решения для наглядности,
        # но текст сформируем так, как будто это дни.
        
        # 3. Данные дерева
        tree = TreeProgress(user_id)
        tree_level_name = "семя"
        tree_total_days = 0
        
        if tree.load():
            if tree.level >= 1: tree_level_name = "росток"
            elif tree.level >= 2: tree_level_name = "куст"
            elif tree.level >= 3: tree_level_name = "дерево"
            elif tree.level >= 4: tree_level_name = "лес"
            tree_total_days = tree.total_days

        # Формирование текста (Стиль Зеркала)
        # Блок 1: Сегодня
        text_today = f"Сегодня: осознанных решений — {conscious}, попыток открыть TikTok — {attempts}."
        
        # Блок 2: За 7 дней
        text_week = f"За 7 дней: осознанных дней — {week_conscious}, серия — {tree.streak} дн."
        
        # Блок 3: Дерево
        text_tree = f"Дерево: уровень — {tree_level_name}, осознанных дней всего — {tree_total_days}."
        
        # Финальная сборка
        stats_message = (
            f"{text_today}\n\n"
            f"{text_week}\n\n"
            f"{text_tree}"
        )

        # Если сегодня были попытки, но не было остановок - добавить мягкое напоминание
        if attempts > 0 and conscious == 0:
            stats_message += "\n\nДерево сегодня не росло. Бывает и так."

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        
        await callback.message.edit_text(stats_message, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await callback.message.edit_text(
            "Статистика на размышлении...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
        )
    
    await callback.answer()

# Удалите старый callback_tree_progress и вставьте этот:

@dp.callback_query(F.data == "tree_progress")
async def callback_tree_progress(callback: types.CallbackQuery):
    """Показывает состояние дерева (Тихий стиль)"""
    user_id = callback.from_user.id
    
    try:
        from tree_progress.tree import TreeProgress
        tree = TreeProgress(user_id)
        
        # Загружаем, если есть данные
        tree.load()
        
        stage_name = tree.get_stage_name()
        desc = tree.get_stage_description()
        
        text = (
            f"🌳 <b>Твой рост</b>\n\n"
            f"{stage_name}\n"
            f"{desc}\n\n"
            f"Всего осознанных дней: {tree.total_days}\n"
            f"Текущая серия: {tree.streak} дн."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        
        await callback.message.edit_text(text, parse_mode='HTML', reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка загрузки дерева: {e}")
        await callback.message.edit_text("Дерево растет молча.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ]))
    
    await callback.answer()


    



async def handle_practice_reflection(message: types.Message, state: FSMContext):
    """Обработка рефлексии дня"""
    reflection = message.text.strip()
    await state.update_data(reflection=reflection)
    
    # НЕ получаем новую практику - она уже показана в callback_daily_practice
    # Просто подтверждаем запись рефлексии и ждём 'готово'
    
    await message.answer(
        f"✅ Рефлексия записана: {reflection}\n\n"
        f"🌱 Теперь выполните практику, которая показана выше.\n\n"
        f"Когда закончите, напишите 'готово'",
        parse_mode='HTML'
    )
    await state.set_state(DailyPracticeStates.waiting_practice_completion)

async def handle_practice_completion(message: types.Message, state: FSMContext):
    """Обработка завершения практики"""
    if message.text.strip().lower() in ['готово', 'выполнил', 'done', 'завершил']:
        user_id = message.from_user.id
        data = await state.get_data()
        reflection = data.get('reflection', '')
        
        # Сохраняем данные практики
        practice_data = {
            "reflection": reflection,
            "completed_at": datetime.now().isoformat(),
            "practice_completed": True
        }
        
        # Сохраняем в daily_check
        await save_daily_data(user_id, practice_data)
        
        # Показываем дерево прогресса (если есть)
        try:
            from tree_progress.tree import TreeProgress
            tree = TreeProgress(user_id)
            if tree.load():
                progress_text = tree.get_progress_text()
                await message.answer(
                    f"🌳 <b>Твой прогресс:</b>\n\n{progress_text}",
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Ошибка загрузки прогресса: {e}")
        
        # Сообщение об успешном завершении
        await message.answer(
            f"🎉 <b>Практика засчитана!</b>\n\n"
            f"📝 Рефлексия: {reflection}\n\n"
            f"✅ Ты успешно выполнил(а) дневную практику!\n"
            f"⭐ Получено XP за осознанность\n"
            f"🌱 Продолжай в том же духе!\n\n"
            f"Новая практика будет доступна завтра в 7:00 МСК",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    else:
        await message.answer(
            "Напишите 'готово' когда выполните практику.\n"
            "Или '/cancel' для отмены."
        )

        
@dp.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.answer(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )
    await callback.answer()        



# --- НОВЫЙ СЦЕНАРИЙ SOS ---

@dp.callback_query(F.data == "sos")
async def callback_sos_start(callback: types.CallbackQuery, state: FSMContext):
    """Шаг 1 SOS: Тянет открыть TikTok."""
    await state.set_state(SosStates.waiting_priority)
    
    text = "Тянет открыть TikTok.\n\nЧто сейчас важнее этого?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Сон", callback_data="sos_prio_sleep"),
            InlineKeyboardButton(text="Учёба / работа", callback_data="sos_prio_work")
        ],
        [
            InlineKeyboardButton(text="Люди рядом", callback_data="sos_prio_people"),
            InlineKeyboardButton(text="Дело на сегодня", callback_data="sos_prio_task")
        ],
        [
            InlineKeyboardButton(text="Ничего конкретного", callback_data="sos_prio_none"),
            InlineKeyboardButton(text="Отмена", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("sos_prio_"))
async def callback_sos_priority(callback: types.CallbackQuery, state: FSMContext):
    """Шаг 2 SOS: Подтверждение выбора."""
    # Сохраняем выбор, чтобы использовать в тексте
    priority_map = {
        "sleep": "Сон",
        "work": "Учёба / работа",
        "people": "Люди рядом",
        "task": "Дело на сегодня",
        "none": "Ничего конкретного"
    }
    
    prio_code = callback.data.split("_")[-1]
    prio_text = priority_map.get(prio_code, "Это")
    
    await state.update_data(priority=prio_text)
    await state.set_state(SosStates.waiting_confirmation)
    
    text = f"{prio_text} важнее TikTok сейчас.\n\nОткрывать или оставить закрытым?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Оставить закрытым", callback_data="sos_act_close"),
            InlineKeyboardButton(text="Открыть всё равно", callback_data="sos_act_open")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("sos_act_"))
async def callback_sos_action(callback: types.CallbackQuery, state: FSMContext):
    """Шаг 3 SOS: Результат."""
    action = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    data = await state.get_data()
    priority = data.get("priority", "Это")
    
    await state.clear()
    
    if action == "close":
        # Ветка: Оставить закрытым -> Рост дерева
        try:
            from stats.user_stats import update_stats
            from tree_progress.tree import TreeProgress
            
            await update_stats(user_id, "conscious_stop")
            tree = TreeProgress(user_id)
            result = await tree.add_day()
            
            text = (
                "TikTok остаётся закрытым.\n"
                "Этот выбор отмечен для дерева."
            )
            
            if result.get("stage_changed"):
                text += f"\n\nДерево перешло на уровень: {result['new_stage']}."
                text += f"\nВсего осознанных дней: {result['total_days']}."
                
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса в SOS: {e}")
            text = "TikTok остаётся закрытым."
            
    else:
        # Ветка: Открыть всё равно -> Фиксация + Счетчик срывов
        try:
            from stats.user_stats import update_stats
            await update_stats(user_id, "tiktok_attempt")
            
            # Проверка на 3 срыва
            from stats.user_stats import UserStats
            stats = UserStats(user_id)
            if stats.data is None:
                stats.data = await stats._load_stats()
            
            slips_count = await stats.increment_slip()
            warning_message = ""
            if slips_count == 3:
                warning_message = "\n\nЭто уже третий раз за сегодня."

        except Exception:
            warning_message = ""
            
        text = "TikTok открыт.\nМы просто зафиксировали этот момент." + warning_message

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="В меню", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()





async def main() -> None:
    """Запуск бота"""
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())