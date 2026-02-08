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

# ИМПОРТЫ FSM - ДОБАВИТЬ СЮДА:
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ... (импорты)

# Состояния для диалога
class QuickPauseStates(StatesGroup):
    waiting_purpose = State()      # Ожидаем ответ "зачем открываешь TikTok"
    waiting_time = State()         # Ожидаем ответ "сколько времени"
    confirmation = State()         # Ожидаем подтверждение

class DailyCheckStates(StatesGroup):
    waiting_reflection = State()
    waiting_practice = State()

# ... (остальной код)

class DailyCheckStates(StatesGroup):
    waiting_reflection = State()   # Ожидаем ответ "как прошёл день"
    waiting_practice = State()     # Ожидаем выполнение практики
    
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
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создание главного меню с кнопками"""
    keyboard = [
        [
            InlineKeyboardButton(text="Иду в Tik Tok", callback_data="quick_pause"),
            # InlineKeyboardButton(text=" Дневная практика", callback_data="daily_practice")
        ],
        [
            InlineKeyboardButton(text=" Дерево прогресса", callback_data="tree_progress"),
            InlineKeyboardButton(text=" Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text=" SOS", callback_data="sos")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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


# Создание экземпляров бота и диспетчера
from aiogram.fsm.storage.memory import MemoryStorage
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

@dp.message(Command("unstart"))
async def cmd_unstart(message: types.Message):
    """Сброс регистрации для повторного прохождения онбординга"""
    user_id = message.from_user.id
    file_path = "data/user_preferences.json"

    # Загружаем данные
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = {}
    else:
        data = {}

    # Проверяем и удаляем
    if str(user_id) in data:
        del data[str(user_id)]
        
        # Сохраняем обновленные данные
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        await message.answer("🗑 Твоя запись удалена. Теперь ты можешь пройти регистрацию заново командой /start")
    else:
        await message.answer("🤷‍♂️ Ты не зарегистрирован или запись уже удалена.")

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

# Вспомогательная функция для таймера
async def quick_pause_timer(user_id: int, minutes: int, bot: Bot):
    """Фоновая задача: ждет время и напоминает пользователю."""
    await asyncio.sleep(minutes * 60)
    
    try:
        # Кнопки по истечении времени
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Закрыть TikTok", callback_data=f"qp_timer_close_{minutes}"),
                InlineKeyboardButton(text="Остаться", callback_data=f"qp_timer_stay_{minutes}")
            ]
        ])
        
        await bot.send_message(
            chat_id=user_id,
            text=f"Твои {minutes} минут прошли.\n\nЧто ты хочешь сделать дальше?",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке таймера: {e}")

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
async def callback_quick_pause_reason(callback: types.CallbackQuery):
    """Обработка причины: Сообщение 3 и 4"""
    reason_code = callback.data.split("_")[-1]
    reasons_map = {
        "habit": "привычка",
        "fatigue": "усталость",
        "distraction": "отвлечение",
        "interest": "интерес"
    }
    reason_text = reasons_map.get(reason_code, "причина")
    
    # Сообщение 3
    await callback.message.edit_text(f"Сейчас за TikTok стоит: {reason_text}.")
    
    # Пауза
    await asyncio.sleep(1)
    
    # Сообщение 4 + Кнопки времени
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 минут", callback_data="qp_time_5"),
            InlineKeyboardButton(text="15 минут", callback_data="qp_time_15")
        ],
        [
            InlineKeyboardButton(text="30 минут", callback_data="qp_time_30"),
            InlineKeyboardButton(text="Сегодня нет", callback_data="qp_time_none")
        ]
    ])
    
    await callback.message.answer("Сколько времени ты готов отдать этому прямо сейчас?", reply_markup=keyboard)
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
            if tree.load():
                await tree.add_completion(xp_gain=5) # Награда за осознанность
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса: {e}")
            
        await callback.message.answer("🌳", reply_markup=get_main_keyboard())
        await callback.answer()
        
    else:
        # Ветка: 5 / 15 / 30 минут
        minutes = int(time_code)
        await callback.message.edit_text(f"Ты выбираешь {minutes} минут.")
        await asyncio.sleep(1)
        await callback.message.answer("Когда время закончится, я напомню об этом.")
        
        # Запуск таймера в фоне
        asyncio.create_task(quick_pause_timer(user_id, minutes, callback.bot))
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

    await callback.message.answer("🌳", reply_markup=get_main_keyboard())
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
    
    await callback.message.answer("🌳", reply_markup=get_main_keyboard())
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

@dp.callback_query(F.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
    """Обработка кнопки 'Статистика' в новом стиле"""
    user_id = callback.from_user.id
    
    try:
        from stats.user_stats import get_stats
        from tree_progress.tree import TreeProgress
        
        # 1. Получаем данные за сегодня
        today_stats = await get_stats(user_id, "today")
        attempts = today_stats.get("events_count", {}).get("tiktok_attempt", 0)
        conscious = today_stats.get("events_count", {}).get("conscious_stop", 0)
        
        # 2. Получаем данные за неделю (осознанные дни)
        # Это сложная метрика, упростим до общего количества решений за неделю
        week_stats = await get_stats(user_id, "week")
        week_conscious = week_stats.get("events_count", {}).get("conscious_stop", 0)
        
        # 3. Данные дерева
        tree = TreeProgress(user_id)
        tree_text = "Дерево еще не посажено."
        streak = 0
        total_days = 0
        level_name = "семя"
        
        if tree.load():
            streak = tree.streak
            total_days = tree.total_days
            # Простая система названий уровней
            if tree.level == 1: level_name = "росток"
            elif tree.level == 2: level_name = "побег"
            elif tree.level == 3: level_name = "куст"
            elif tree.level >= 4: level_name = "дерево"
            
            tree_text = f"Дерево: уровень — {level_name}, осознанных дней всего — {total_days}"

        # Формируем текст (Созерцательный стиль)
        if attempts > 0:
            stats_message = (
                f"Сегодня ты {attempts} раз{'а' if attempts == 1 else 'а'} тянулся к TikTok. "
                f"{conscious} раз{'а' if conscious == 1 else 'а'} остановился.\n\n"
                f"За эту неделю было {week_conscious} осознанных решений. "
                f"Текущая серия — {streak} дн{'я' if streak == 1 else 'ей'}. Дерево это помнит.\n\n"
                f"{tree_text}"
            )
        else:
            stats_message = (
                "Сегодня попыток открыть TikTok не было.\n\n"
                f"За эту неделю — {week_conscious} осознанных решений. "
                f"Серия — {streak} дн{'я' if streak == 1 else 'ей'}.\n\n"
                f"{tree_text}"
            )

        # Кнопки возврата
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

# ... (твой код, функции callback_stats_period и т.д.) ...

async def main() -> None:
    """Запуск бота"""
    print("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())