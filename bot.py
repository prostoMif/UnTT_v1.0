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
        "unTT.\n"
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
async def callback_onboarding_info(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Когда рука тянется к TikTok, ты заходишь сюда первым.\n"
        "unTT спрашивает: зачем сейчас, сколько времени.\n"
        "Ты отвечаешь. Дерево отмечает выбор.\n"
        "Только первые 5 дней. Дальше — по твоему решению.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Понял", callback_data="onboarding_understood")]
        ])
    )
    await callback.answer()

# Хэндлер для кнопки "Понял" и "Начать" (Переход к Шагу 4)
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


@dp.callback_query(F.data == "quick_pause")
async def callback_quick_pause(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("⏸️ Зачем ты открываешь TikTok?")
    await state.set_state(QuickPauseStates.waiting_purpose)
    
    # Обновляем статистику - ВАЖНО!
    try:
        from stats.user_stats import update_stats
        await update_stats(callback.from_user.id, "quick_pause")
        print(f"Статистика quick_pause обновлена для user_id {callback.from_user.id}")
    except Exception as e:
        print(f"Ошибка обновления статистики quick_pause: {e}")
        logger.error(f"Ошибка обновления статистики quick_pause: {e}")
    
# Обработчики для QuickPause
@dp.message(QuickPauseStates.waiting_purpose)
async def handle_purpose(message: types.Message, state: FSMContext):
    purpose = message.text.strip()
    await state.update_data(purpose=purpose)
    
    await message.answer(
        f"✅ Цель: {purpose}\n\n"
        "Сколько минут планируешь провести в TikTok?"
    )
    await state.set_state(QuickPauseStates.waiting_time)

@dp.message(QuickPauseStates.waiting_time)
async def handle_time(message: types.Message, state: FSMContext):
    time_str = message.text.strip()
    await state.update_data(time_str=time_str)
    
    data = await state.get_data()
    
    await message.answer(
        f"📋 Подтверждение:\n"
        f"🎯 Цель: {data['purpose']}\n"
        f"⏰ Время: {time_str}\n\n"
        "Напиши 'да' для подтверждения или 'нет' для отмены"
    )
    await state.set_state(QuickPauseStates.confirmation)

@dp.message(QuickPauseStates.confirmation)
async def handle_confirmation(message: types.Message, state: FSMContext):
    confirmation = message.text.strip().lower()
    
    if confirmation in ['да', 'yes', 'подтверждаю']:
        data = await state.get_data()
        
        # Здесь вызывай функцию сохранения
        # await save_pause_data(message.from_user.id, data)
        
        await message.answer(
            "✅ Быстрая пауза установлена!",
            reply_markup=get_main_keyboard()
        )
        await state.clear()
    else:
        await message.answer("❌ Пауза отменена.")
        await state.clear()



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

@dp.callback_query(F.data.startswith("stats_"))
async def callback_stats_period(callback: types.CallbackQuery):
    """Обработка выбора периода статистики"""
    period = callback.data.replace("stats_", "")
    user_id = callback.from_user.id
    
    # Пока заглушка - показываем базовую статистику
    await callback.message.answer(
        f"📊 <b>Статистика за {period}</b>\n\n"
        f"🎯 Всего практик: 0\n"
        f"⭐ Получено XP: 0\n\n"
        f"Начните выполнять практики для отслеживания прогресса!",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к статистике", callback_data="stats")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "tree_progress")
@dp.callback_query(F.data == "tree_progress")
async def callback_tree_progress(callback: types.CallbackQuery):
    """Обработка кнопки 'Дерево прогресса'"""
    user_id = callback.from_user.id
    
    try:
        tree = TreeProgress(user_id)
        if tree.load():
            progress_text = tree.get_progress_text()
            await callback.message.edit_text(
                progress_text,
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
        else:
            await callback.message.edit_text(
                "🌱 Твой прогресс загружается...\n\n"
                "Начни выполнять практики, чтобы увидеть рост своего дерева!",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка загрузки прогресса: {e}")
        await callback.message.edit_text(
            "🌱 Продолжай практиковаться!\n\n"
            "Дерево покажет твой прогресс после первых практик.",
            reply_markup=get_main_keyboard()
        )
    
    await callback.answer()

    
async def handle_practice(message: types.Message, state: FSMContext):
    if message.text.strip().lower() in ['готово', 'выполнил', 'done']:
        data = await state.get_data()
        
        # Сохранение данных практики
        await save_daily_data(message.from_user.id, data)
        
        # ОБНОВЛЕНИЕ СТАТИСТИКИ И ДЕРЕВА ПРОГРЕССА
        user_id = message.from_user.id
        practice_data = {
            'completed_at': datetime.now(MOSCOW_TZ).isoformat(),
            'type': 'daily_practice',
            'xp': 5  # Добавляем XP за практику
        }
        
        try:
            # Обновляем статистику
            await update_user_stats(user_id, practice_data)
            
            # Обновляем дерево прогресса
            tree_progress = TreeProgress(user_id)
            tree_progress.load()  # Загружаем данные
            await tree_progress.add_completion(xp_gain=5)  # Добавляем XP
            
            await message.answer(
                "📊 Дневная отметка выполнена!\n\n"
                "💫 Статистика обновлена!",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")
            await message.answer(
                "📊 Практика выполнена!\n\n"
                "⚠️ Не удалось обновить статистику",
                reply_markup=get_main_keyboard()
            )
        
        await state.clear()
    else:
        await message.answer("Напиши 'готово' когда выполнишь практику.")
        
        
@dp.callback_query(F.data == "daily_practice")           
async def callback_daily_practice(callback: types.CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Дневная практика'"""
    await callback.answer()
    
    try:
        # Получаем текущий день недели (0-6, где 0 - понедельник)
        from datetime import datetime
        from scheduler import get_moscow_time
        
        current_time = get_moscow_time()
        day_of_week = current_time.weekday()  # 0 = понедельник, 6 = воскресенье
        
        # Получаем контент дневной практики для текущего дня
        practice_content = get_daily_practice(day=day_of_week + 1)  # +1 потому что функция ожидает 1-30
        
        # Форматируем текст практики
        practice_text = (
            f"📚 <b>Дневная практика</b>\n\n"
            f"<b>{practice_content.get('title', 'Практика дня')}</b>\n\n"
            f"{practice_content.get('instruction', 'Выполните упражнение осознанности')}\n\n"
            f"💫 Сложность: {practice_content.get('difficulty', 'easy')}\n"
            f"🏆 Опыт: {practice_content.get('xp', 5)} XP"
        )
        
        # Отправляем пользователю практику
        await callback.message.edit_text(
            practice_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выполнил практику", callback_data="practice_done")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Детальная ошибка в callback_daily_practice: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Полный traceback: {traceback.format_exc()}")
        
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при загрузке практики. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )



# Обработчик завершения практики
@dp.callback_query(F.data == "practice_done")
@dp.callback_query(F.data == "practice_done")
async def callback_practice_done(callback: types.CallbackQuery, state: FSMContext):
    """Обработка завершения практики"""
    await callback.answer()
    
    user_id = callback.from_user.id
    
    try:
        # Сохраняем данные о выполненной практике
        practice_data = {
            'completed_at': datetime.now().isoformat(),
            'type': 'daily_practice',
            'xp': 5
        }
        
        await save_daily_data(user_id, practice_data)
        
        # Обновляем статистику - ВАЖНО!
        try:
            from stats.user_stats import update_stats
            stats_updated = await update_stats(user_id, "daily_practice", practice_data)
            print(f"Статистика обновлена: {stats_updated}")  # Отладочный вывод
        except Exception as stats_error:
            print(f"Ошибка обновления статистики: {stats_error}")
            logger.error(f"Ошибка обновления статистики: {stats_error}")
        
        # Обновляем дерево прогресса
        try:
            tree_progress = TreeProgress(user_id, storage_dir="data")
            tree_result = await tree_progress.add_completion(xp_gain=5)
            
            # Если дерево выросло - обновляем статистику роста
            if tree_result.get("leveled_up"):
                await update_stats(user_id, "tree_growth", {
                    "old_level": tree_result["old_level"],
                    "new_level": tree_result["new_level"],
                    "xp_gained": tree_result["xp_gained"]
                })
                print(f"Статистика роста дерева обновлена")
            
            # Отправляем подтверждение
            level_up_text = ""
            if tree_result.get("leveled_up"):
                level_up_text = f"\n🎉 Поздравляем! Достигнут уровень {tree_result['new_level']}!"
            
            if tree_result.get("already_grown_today"):
                growth_text = "\n💫 За сегодня уже был рост. Но XP начислены!"
            else:
                growth_text = "\n🌱 Дерево выросло на 1 день!"
            
            await callback.message.edit_text(
                f"🎉 Отлично! Дневная практика выполнена!\n\n"
                f"💫 Ты молодец, продолжай в том же духе!"
                f"{growth_text}"
                f"{level_up_text}",
                reply_markup=get_main_keyboard()
            )
            
        except Exception as tree_error:
            print(f"Ошибка дерева прогресса: {tree_error}")
            logger.error(f"Ошибка дерева прогресса: {tree_error}")
            await callback.message.edit_text(
                "🎉 Отлично! Дневная практика выполнена!\n\n"
                "💫 Ты молодец, продолжай в том же духе!",
                reply_markup=get_main_keyboard()
            )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении практики: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при сохранении. Попробуйте еще раз.",
            reply_markup=get_main_keyboard()
        )
                
# Обработчик кнопки "Назад"
@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await callback.answer()
    
    await callback.message.edit_text(
        "Главное меню. Выберите действие:",
        reply_markup=get_main_keyboard()
    )
        
@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Операция отменена.", reply_markup=get_main_keyboard())


@dp.callback_query(F.data == "sos")
async def callback_sos(callback: CallbackQuery) -> None:
    """Обработка кнопки 'SOS'"""
    user_id = callback.from_user.id
    await callback.message.edit_text("🆘 Отправка SOS...")
    
    try:
        await handle_sos(user_id)
        await callback.message.edit_text(
            "🆘 SOS отправлен! Помощь в пути.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка в handle_sos: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка. Попробуйте снова.",
            reply_markup=get_main_keyboard()
        )

@dp.callback_query(F.data == "stats")
async def callback_stats(callback: types.CallbackQuery):
    """Обработка кнопки 'Статистика'"""
    user_id = callback.from_user.id
    
    try:
        # Получаем статистику пользователя
        from stats.user_stats import get_user_stats_summary
        stats_summary = await get_user_stats_summary(user_id)
        
        # Создаем красивое представление статистики
        total_stats = stats_summary["total_stats"]
        streak_info = stats_summary["streak_info"]
        
        stats_text = (
            f"📊 <b>Твоя статистика</b>\n\n"
            f"🎯 <b>Осознанные действия:</b>\n"
            f"• Быстрые паузы: {total_stats['total_pauses']}\n"
            f"• Дневные практики: {total_stats['total_practices']}\n"
            f"• SOS обращения: {total_stats['total_sos']}\n"
            f"• Рост дерева: {total_stats['total_tree_growth']}\n\n"
            f"🔥 <b>Серии активности:</b>\n"
            f"• Текущая: {streak_info['current']} дней\n"
            f"• Лучшая: {streak_info['best']} дней\n\n"
            f"📅 <b>Всего активных дней:</b> {total_stats['active_days']}\n\n"
            f"💪 <b>Молодец!</b> Каждое осознанное действие приближает к цели!"
        )
        
        # Создаем клавиатуру с периодами
        period_keyboard = [
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data="stats_today"),
                InlineKeyboardButton(text="📅 Неделя", callback_data="stats_week")
            ],
            [
                InlineKeyboardButton(text="📅 Месяц", callback_data="stats_month"),
                InlineKeyboardButton(text="📊 Всё время", callback_data="stats_total")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
            ]
        ]
        
        await callback.message.edit_text(
            stats_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=period_keyboard)
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await callback.message.edit_text(
            "📊 Статистика загружается...\n\nПродолжай практиковаться!",
            reply_markup=get_main_keyboard()
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("stats_"))
async def callback_stats_period(callback: types.CallbackQuery):
    """Обработка выбора периода статистики"""
    period = callback.data.replace("stats_", "")
    user_id = callback.from_user.id
    
    try:
        from stats.user_stats import get_stats
        period_stats = await get_stats(user_id, period)
        
        events_count = period_stats["events_count"]
        
        period_names = {
            "today": "сегодня",
            "week": "на этой неделе", 
            "month": "в этом месяце",
            "total": "за всё время"
        }
        
        stats_text = (
            f"📊 <b>Статистика {period_names.get(period, period)}</b>\n\n"
            f"⏸️ Быстрые паузы: {events_count['quick_pause']}\n"
            f"📚 Дневные практики: {events_count['daily_practice']}\n"
            f"🆘 SOS обращения: {events_count['sos']}\n"
            f"🌱 Рост дерева: {events_count['tree_growth']}\n\n"
            f"🎯 Всего осознанных действий: {period_stats['total_events']}\n\n"
            f"💫 Отличная работа! Продолжай в том же духе!"
        )
        
        await callback.message.edit_text(
            stats_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к статистике", callback_data="stats")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики за период: {e}")
        await callback.message.edit_text(
            "📊 Статистика за период загружается...",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад к статистике", callback_data="stats")]
            ])
        )
    
    await callback.answer()

async def main() -> None:
    """Запуск бота"""
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


