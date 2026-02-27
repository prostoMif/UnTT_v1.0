import os
import re
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiohttp import web

from config.texts import *
from config.menu import *
from config.texts import EXTENDED_MENU
from config.menu import menu_no_sub, menu_with_sub, paywall_keyboard, back_keyboard
from config.menu import stats_keyboard
# В bot.py добавить импорт
from datetime import timezone
import pytz

# # Функция получения московского времени
def get_moscow_time():
    return datetime.now(pytz.timezone('Europe/Moscow'))


# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ИМПОРТЫ МОДУЛЕЙ ====================
try:
    from stats.user_stats import UserStats, update_stats
except ImportError:
    UserStats = None
    update_stats = None
    logger.warning("stats.user_stats не найден")

try:
    from tree_progress.tree import TreeProgress
except ImportError:
    TreeProgress = None

try:
    from payment.yookassa_client import create_payment
except ImportError:
    create_payment = None

from yookassa import Payment, Configuration



# ==================== КОНСТАНТЫ ====================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
FREE_DAYS_LIMIT = 3
ADMIN_ID = 5782224611  # Твой ID

# ==================== СОСТОЯНИЯ ====================
class QuickPauseStates(StatesGroup):
    waiting_purpose = State()
    waiting_time = State()
    waiting_confirmation = State()

class SosStates(StatesGroup):
    waiting_priority = State()
    waiting_confirmation = State()

class PaymentStates(StatesGroup):
    waiting_for_payment = State()

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
TOKEN = os.getenv("BOT_TOKEN")
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)
active_timers = {}

# ==================== ПРОВЕРКИ ДОСТУПА ====================


async def get_user_status(user_id: int) -> dict:
    """Получить статус пользователя"""
    file_path = DATA_DIR / "user_preferences.json"
    if not file_path.exists():
        return {"is_paid": False, "registration_date": None}
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_data = data.get(str(user_id), {})
        
        sub_end_str = user_data.get("subscription_end_date")
        is_paid = False
        if sub_end_str:
            try:
                # ИСПРАВЛЕНО: используем московское время
                sub_end = datetime.fromisoformat(sub_end_str)
                moscow_now = get_moscow_time()
                if sub_end > moscow_now:
                    is_paid = True
            except ValueError:
                pass
        
        return {
            "is_paid": is_paid,
            "subscription_end_date": sub_end_str,
            "registration_date": user_data.get("registration_date")
        }
    except Exception:
        return {"is_paid": False, "registration_date": None}


async def update_user_status(user_id: int, key: str, value) -> None:
    """Обновить статус пользователя"""
    file_path = DATA_DIR / "user_preferences.json"
    data = {}
    
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    
    if str(user_id) not in data or not isinstance(data[str(user_id)], dict):
        data[str(user_id)] = {}
    
    data[str(user_id)][key] = value
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def is_premium(user_id: int) -> bool:
    """Проверка премиум статуса"""
    status = await get_user_status(user_id)
    return status.get("is_paid", False)


async def get_usage_days(user_id: int) -> int:
    """Сколько дней использует бота"""
    status = await get_user_status(user_id)
    reg_date_str = status.get("registration_date")
    
    if not reg_date_str:
        await update_user_status(user_id, "registration_date", get_moscow_time().isoformat())
        return 0
    
    try:
        reg_date = datetime.fromisoformat(reg_date_str)
        # Если время на сервере в UTC, а регистрация была по Москве
        moscow_tz = pytz.timezone('Europe/Moscow')
        now_moscow = datetime.now(moscow_tz)
        
        # Делаем reg_date aware если она naive
        if reg_date.tzinfo is None:
            reg_date = moscow_tz.localize(reg_date)
        
        days = (now_moscow - reg_date).days
        return days if days >= 0 else 0
    except Exception as e:
        logger.error(f"Ошибка подсчёта дней: {e}")
        return 0

async def check_access(user_id: int) -> bool:
    """Полный доступ — бесплатно навсегда для базовых функций"""
    return True  # Всегда доступно


async def activate_subscription(user_id: int, months: int = 1) -> datetime:
    """Активировать подписку"""
    status = await get_user_status(user_id)
    base_date = get_moscow_time()
    
    if status["is_paid"] and status["subscription_end_date"]:
        try:
            current_end = datetime.fromisoformat(status["subscription_end_date"])
            if current_end > base_date:
                base_date = current_end
        except:
            pass
    
    new_end = base_date + timedelta(days=30 * months)
    await update_user_status(user_id, "subscription_end_date", new_end.isoformat())
    return new_end


# ==================== СТАТИСТИКА ====================

async def get_today_stats(user_id: int) -> dict:
    """Статистика за сегодня"""
    file_path = DATA_DIR / "user_preferences.json"
    saved_minutes = 0
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_data = data.get(str(user_id), {})
        
        # Получаем сохраненное время за сегодня
        today = datetime.now().date().isoformat()
        last_date = user_data.get("saved_date")
        
        if last_date == today:
            saved_minutes = user_data.get("today_saved_minutes", 0)
    except:
        pass
    
    # Считаем количество осознанных остановок
    conscious_count = 0
    if UserStats:
        try:
            stats = UserStats(user_id)
            stats_data = await stats.get_stats("today")
            conscious_count = stats_data.get("events_count", {}).get("conscious_stop", 0)
        except:
            pass
    
    return {"count": conscious_count, "saved_time": f"{saved_minutes} мин"}

async def get_full_stats(user_id: int) -> dict:
    """Полная статистика (премиум)"""
    file_path = DATA_DIR / "user_preferences.json"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_data = data.get(str(user_id), {})
        
        today = get_moscow_time().date().isoformat()
        # ИСПРАВЛЕНО: берем реальные значения, а не вычисляем
        if user_data.get("saved_date") == today:
            saved_minutes = user_data.get("today_saved_minutes", 0)
        else:
            saved_minutes = 0
        total_saved = user_data.get("total_saved_minutes", 0)
    except:
        saved_minutes = 0
        total_saved = 0
    
    if not UserStats:
        return {
            "today": 0, "week": 0, "month": 0, "days": 0,
            "saved": saved_minutes, "total_saved": total_saved,
            "week_saved": 0, "month_saved": 0, "week_avg": 0, "month_avg": 0
        }
    
    try:
        stats = UserStats(user_id)
        
        today_data = await stats.get_stats("today")
        week_data = await stats.get_stats("week")
        month_data = await stats.get_stats("month")
        
        today_count = today_data.get("events_count", {}).get("conscious_stop", 0)
        week_count = week_data.get("events_count", {}).get("conscious_stop", 0)
        month_count = month_data.get("events_count", {}).get("conscious_stop", 0)
        
        days = await get_usage_days(user_id)
        
        # Средние
        week_avg = round(week_count / 7, 1) if week_count > 0 else 0
        month_avg = round(month_count / 30, 1) if month_count > 0 else 0
        
        # ИСПРАВЛЕНО: не умножаем на 15, используем реальное накопленное время
        week_saved = user_data.get("week_saved_minutes", 0)
        month_saved = user_data.get("month_saved_minutes", 0)
        
        return {
            "today": today_count,
            "week": week_count,
            "month": month_count,
            "days": days,
            "saved": saved_minutes,
            "total_saved": total_saved,
            "week_saved": week_saved,
            "month_saved": month_saved,
            "week_avg": week_avg,
            "month_avg": month_avg
        }
    except Exception as e:
        logger.error(f"Full stats error: {e}")
        return {
            "today": 0, "week": 0, "month": 0, "days": 0,
            "saved": 0, "total_saved": 0,
            "week_saved": 0, "month_saved": 0, "week_avg": 0, "month_avg": 0
        }
# ==================== МЕНЮ ====================

async def get_main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню"""
    if await is_premium(user_id):
        return menu_with_sub()
    return menu_no_sub()


async def get_start_menu(user_id: int) -> InlineKeyboardMarkup:
    """Стартовое меню"""
    if await is_premium(user_id):
        return menu_start_with_sub()
    return menu_start_no_sub()


async def get_menu_text(user_id: int) -> str:
    """Текст меню с цифрами"""
    stats = await get_today_stats(user_id)
    is_prem = await is_premium(user_id)
    
    if is_prem:
        return MENU_WITH_SUB.format(count=stats["count"], saved_time=stats["saved_time"])
    return MENU_NO_SUB.format(count=stats["count"], saved_time=stats["saved_time"])


# ==================== ТАЙМЕР ====================

async def quick_pause_timer_with_finish(user_id: int, minutes: int, bot_instance: Bot):
    """Фоновая задача: ждёт время и напоминает"""
    try:
        await asyncio.sleep(minutes * 60)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Я закончил", callback_data="qp_finish"),
                InlineKeyboardButton(text="Я остаюсь", callback_data="qp_timer_stay_action")
            ]
        ])
        
        await bot_instance.send_message(
            chat_id=user_id,
            text=f"Твои {minutes} минут прошли.\n\nТы всё ещё в приложении?",
            reply_markup=keyboard
        )
    except asyncio.CancelledError:
        pass
    finally:
        if user_id in active_timers:
            del active_timers[user_id]


def parse_duration(text: str) -> int:
    """Парсит время из текста"""
    text = text.lower().strip()
    match_hour = re.search(r'(\d+\.?\d*)\s*(час|ч|h)', text)
    if match_hour:
        return int(float(match_hour.group(1)) * 60)
    match_min = re.search(r'(\d+\.?\d*)', text)
    if match_min:
        return int(float(match_min.group(1)))
    return None


# ==================== ОБРАБОТЧИКИ ====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Расширенное меню с тарифами и хелпом"""
    user_id = message.from_user.id
    await state.clear()
    
    # Сохраняем дату регистрации ЕСЛИ ЕЁ НЕТ
    status = await get_user_status(user_id)
    if not status.get("registration_date"):
        await update_user_status(user_id, "registration_date", datetime.now().isoformat())
        logger.info(f"Новый пользователь {user_id}, сохранена дата регистрации")
    
    is_prem = await is_premium(user_id)
    
    # Статистика
    stats = await get_today_stats(user_id)
    
    # Текст меню
    text = EXTENDED_MENU.format(count=stats["count"], saved_time=stats["saved_time"])
    
    # Клавиатура расширенного меню
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Иду в TikTok", callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text="SOS", callback_data="sos") if is_prem else InlineKeyboardButton(text="SOS 🔒", callback_data="sos_locked"),
            InlineKeyboardButton(text="Статистика", callback_data="stats"),
        ],
        [
            InlineKeyboardButton(text="Подписка", callback_data="subscribe"),
            InlineKeyboardButton(text="Тарифы", callback_data="tariffs"),
        ],
        [InlineKeyboardButton(text="Помощь", callback_data="help")],
    ])
    
    await message.answer(text, reply_markup=keyboard)

@dp.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Справка"""
    await message.answer(HELP_TEXT)


@dp.message(Command("tariffs"))
async def cmd_tariffs(message: types.Message) -> None:
    """Тарифы"""
    user_id = message.from_user.id
    status = await get_user_status(user_id)
    
    text = TARIFFS
    
    if status["is_paid"] and status["subscription_end_date"]:
        try:
            end_date = datetime.fromisoformat(status["subscription_end_date"])
            text += f"\n\nПодписка до: {end_date.strftime('%d.%m.%Y')}"
        except:
            pass
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Управление подпиской", callback_data="manage_subscription")]
    ])
    
    await message.answer(text, reply_markup=keyboard)


@dp.message(Command("cancel"))
@dp.callback_query(F.data == "cancel_action")
async def cancel_action(event: types.Message | types.CallbackQuery, state: FSMContext):
    """Отмена"""
    await state.clear()
    
    if isinstance(event, types.CallbackQuery):
        user_id = event.from_user.id
        await event.message.answer(CANCEL_TEXT, reply_markup=await get_main_menu(user_id))
        await event.answer()
    else:
        user_id = event.from_user.id
        await event.answer(CANCEL_TEXT, reply_markup=await get_main_menu(user_id))


@dp.message(Command("unstart"))
async def cmd_unstart(message: types.Message):
    """Сброс данных пользователя"""
    user_id = message.from_user.id
    
    # Удаляем предпочтения
    file_path = DATA_DIR / "user_preferences.json"
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if str(user_id) in data:
                del data[str(user_id)]
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except:
            pass
    
    # Удаляем дерево
    tree_file = DATA_DIR / f"tree_{user_id}.json"
    if tree_file.exists():
        tree_file.unlink()
    
    # Удаляем статистику
    stats_file = DATA_DIR / f"user_stats_{user_id}.json"
    if stats_file.exists():
        stats_file.unlink()
    
    await message.answer("Данные удалены. Начни заново: /start")


# ==================== АДМИН КОМАНДЫ ====================

@dp.message(Command("grant"))
async def cmd_grant_access(message: types.Message):
    """Выдать подписку"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Формат: /grant <user_id> [месяцы]")
            return
        
        target_id = int(args[1])
        months = int(args[2]) if len(args) >= 3 else 1
        
        end_date = await activate_subscription(target_id, months)
        await message.answer(f"Подписка для {target_id} до {end_date.strftime('%d.%m.%Y')}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@dp.message(Command("stats_admin"))
async def cmd_admin_stats(message: types.Message) -> None:
    """Статистика бота (админ)"""
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    
    file_path = DATA_DIR / "user_preferences.json"
    if not file_path.exists():
        await message.answer("Нет данных.")
        return
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    total = len(data)
    paid = sum(1 for u in data.values() if u.get("subscription_end_date"))
    
    await message.answer(f"Пользователей: {total}\nПодписок: {paid}")


# ==================== QUICK PAUSE ====================

@dp.callback_query(F.data == "go_tiktok")
async def callback_go_tiktok(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Старт сценария"""
    await state.set_state(QuickPauseStates.waiting_purpose)
    
    if update_stats:
        try:
            await update_stats(callback.from_user.id, "tiktok_attempt")
        except:
            pass
    
    await callback.message.edit_text(QP_START)
    await asyncio.sleep(1)
    await callback.message.answer(QP_REASON, reply_markup=qp_reason_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("qp_reason_"))
async def callback_qp_reason(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Выбор причины"""
    reasons_map = {
        "habit": "привычка", "fatigue": "усталость",
        "distraction": "отвлечение", "interest": "интерес"
    }
    reason = reasons_map.get(callback.data.split("_")[-1], "причина")
    
    await state.update_data(reason=reason)
    await callback.message.edit_text(f"За этим стоит: {reason}.")
    await asyncio.sleep(0.5)
    # Убираем кнопки - только текст
    await callback.message.answer(QP_TIME)
    await state.set_state(QuickPauseStates.waiting_time)
    await callback.answer()


@dp.message(QuickPauseStates.waiting_time)
async def process_time_input(message: types.Message, state: FSMContext):
    """Ввод времени текстом"""
    minutes = parse_duration(message.text)
    if not minutes or minutes <= 0:
        await message.answer("Напиши время: 5 минут, 1 час, 30")
        return
    
    user_id = message.from_user.id
    start_time = datetime.now()
    
    await state.update_data(planned_minutes=minutes, start_time=start_time.isoformat())
    
    task = asyncio.create_task(quick_pause_timer_with_finish(user_id, minutes, message.bot))
    active_timers[user_id] = task
    
    await message.answer(
        f"Таймер: {minutes} мин.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Я закончил", callback_data="qp_finish")]
        ])
    )


@dp.callback_query(F.data == "qp_finish")
async def callback_qp_finish(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Завершение (нажал Я закончил)"""
    user_id = callback.from_user.id
    
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    data = await state.get_data()
    start_time_str = data.get("start_time")
    planned_minutes = data.get("planned_minutes", 0)
    
    actual_minutes = 0
    if start_time_str:
        try:
            start_dt = datetime.fromisoformat(start_time_str)
            actual_minutes = int((datetime.now() - start_dt).total_seconds() // 60)
        except:
            pass
    
    # Считаем сэкономленное время: запланированное - проведенное
    saved_minutes = planned_minutes - actual_minutes
    
    # Формируем текст
    if saved_minutes > 0:
        praise = f"Ты вышел на {saved_minutes} мин раньше. Это победа."
    elif saved_minutes < 0:
        praise = f"Ты провел {actual_minutes} мин. На {abs(saved_minutes)} мин дольше."
    else:
        praise = "Ты вернулся."
    
    # Сохраняем сэкономленное время
    if saved_minutes > 0:
        await update_user_saved_time(user_id, saved_minutes)
    
    if update_stats:
        try:
            await update_stats(user_id, "conscious_stop")
        except:
            pass
    
    await callback.message.edit_text(f"{praise}\n\nДерево отмечает выбор.")
    await asyncio.sleep(1)
    await callback.message.answer(await get_menu_text(user_id), reply_markup=await get_main_menu(user_id))
    await state.clear()
    await callback.answer()

async def update_user_saved_time(user_id: int, minutes: int) -> None:
    """Сохранить сэкономленное время за сегодня"""
    file_path = DATA_DIR / "user_preferences.json"
    data = {}
    
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    
    if str(user_id) not in data or not isinstance(data[str(user_id)], dict):
        data[str(user_id)] = {}
    
    user_data = data[str(user_id)]
    today = get_moscow_time().date().isoformat()
    
    # Если новый день — сбрасываем сегодня
    last_date = user_data.get("saved_date")
    if last_date != today:
        user_data["today_saved_minutes"] = 0
    
    # Добавляем к сегодня
    current_today = user_data.get("today_saved_minutes", 0)
    user_data["today_saved_minutes"] = current_today + minutes
    
    # Нарастающий итог за всё время (не сбрасывается)
    user_data["total_saved_minutes"] = user_data.get("total_saved_minutes", 0) + minutes
    
    user_data["saved_date"] = today
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
@dp.callback_query(F.data == "qp_stop")
async def callback_qp_stop(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Остановка таймера"""
    user_id = callback.from_user.id
    data = await state.get_data()
    planned = data.get("planned_minutes", 0)
    start_time_str = data.get("start_time")
    
    # Считаем сколько реально провел
    actual_minutes = 0
    if start_time_str:
        try:
            start_dt = datetime.fromisoformat(start_time_str)
            actual_minutes = int((datetime.now() - start_dt).total_seconds() // 60)
        except:
            pass
    
    # Сэкономленное время
    saved = planned - actual_minutes
    
    if saved > 0:
        await update_user_saved_time(user_id, saved)
    
    if update_stats:
        try:
            await update_stats(user_id, "conscious_stop")
        except:
            pass
    
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    await state.clear()
    await callback.message.edit_text(QP_STOPPED_EARLY.format(saved=saved))
    await callback.answer()





@dp.callback_query(F.data == "qp_timer_stay_action")
async def callback_qp_timer_stay(callback: types.CallbackQuery) -> None:
    """Остался в TikTok"""
    user_id = callback.from_user.id
    
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    await callback.message.edit_text("Мы отметили этот момент.")
    await asyncio.sleep(1)
    await callback.message.answer(await get_menu_text(user_id), reply_markup=await get_main_menu(user_id))
    await callback.answer()


# ==================== STATS ====================

@dp.callback_query(F.data == "stats")
async def callback_stats(callback: types.CallbackQuery) -> None:
    """Статистика"""
    user_id = callback.from_user.id
    is_prem = await is_premium(user_id)
    
    if is_prem:
        stats = await get_full_stats(user_id)
        text = STATS_PREMIUM.format(
            today_count=stats["today"],
            saved=stats["saved"],
            week_count=stats["week"],
            week_saved=stats["week_saved"],
            month_count=stats["month"],
            month_saved=stats["month_saved"],
            days_count=stats["days"],
            week_avg=stats["week_avg"],
            month_avg=stats["month_avg"]
        )
    else:
        stats = await get_today_stats(user_id)
        text = STATS_FREE.format(
            today_count=stats["count"],
            saved_time=stats["saved_time"]
        )
    
    await callback.message.edit_text(text, reply_markup=stats_keyboard(is_prem))
    await callback.answer()


# ==================== SOS (только премиум) ====================

@dp.callback_query(F.data == "sos")
async def callback_sos(callback: types.CallbackQuery, state: FSMContext) -> None:
    """SOS - только для премиума!"""
    user_id = callback.from_user.id
    
    if not await is_premium(user_id):
        await callback.message.edit_text(SOS_NEED_PREMIUM, reply_markup=paywall_keyboard())
        await callback.answer()
        return
    
    await state.set_state(SosStates.waiting_priority)
    await callback.message.edit_text(SOS_START, reply_markup=sos_priority_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("sos_prio_"))
async def callback_sos_priority(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Выбор приоритета"""
    priority_map = {
        "work": "Учёба/работа", "sleep": "Сон", "sport": "Спорт",
        "people": "Друзья/семья", "hobby": "Хобби"
    }
    prio = callback.data.split("_")[-1]
    choice = priority_map.get(prio, "Это")
    
    await state.update_data(priority=choice)
    await state.set_state(SosStates.waiting_confirmation)
    
    await callback.message.edit_text(SOS_CONFIRM.format(choice=choice), reply_markup=sos_confirm_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("sos_act_"))
async def callback_sos_action(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Результат SOS"""
    action = callback.data.split("_")[-1]
    user_id = callback.from_user.id
    data = await state.get_data()
    priority = data.get("priority", "Это")
    
    await state.clear()
    
    if action == "close":
        if update_stats:
            try:
                await update_stats(user_id, "conscious_stop")
            except:
                pass
        text = "TikTok остаётся закрытым. Выбор отмечен."
    else:
        text = "TikTok открыт. Мы зафиксировали момент."
    
    await callback.message.edit_text(text, reply_markup=await get_main_menu(user_id))
    await callback.answer()


# ==================== ПОДПИСКА ====================

@dp.callback_query(F.data == "subscribe")
@dp.callback_query(F.data == "manage_subscription")
async def callback_subscribe(callback: types.CallbackQuery) -> None:
    """Управление подпиской"""
    user_id = callback.from_user.id
    status = await get_user_status(user_id)
    is_prem = await is_premium(user_id)
    
    if status["is_paid"] and status["subscription_end_date"]:
        try:
            end_date = datetime.fromisoformat(status["subscription_end_date"])
            date_str = end_date.strftime("%d.%m.%Y")
            days_left = (end_date - get_moscow_time()).days
            
            text = f"Подписка Premium\nАктивна до: {date_str} ({days_left} дн.)"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Продлить +30 дней", callback_data="pay_unlock")],
                [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
            ])
        except:
            text = "Подписка активна"
            keyboard = manage_sub_keyboard(True)
    else:
        days = await get_usage_days(user_id)
        
        # Предложение на 3 день
        if days >= 3:
            text = """Premium:

149₽/мес
- SOS
- Статистика за неделю
- Тренды"""
        else:
            text = """Premium:

149₽/мес
- SOS
- Статистика за неделю
- Тренды

Бесплатно доступны все базовые функции."""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Купить 149₽", callback_data="pay_unlock")],
            [InlineKeyboardButton(text="Назад", callback_data="back_to_menu")]
        ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "pay_unlock")
async def callback_pay(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Создание платежа"""
    user_id = callback.from_user.id
    
    if await is_premium(user_id):
        await callback.answer("Подписка уже активна!", show_alert=True)
        return
    
    return_url = f"https://t.me/UnTT1_bot"
    
    if not create_payment:
        await callback.message.edit_text("Оплата недоступна.")
        await callback.answer()
        return
    
    try:
        payment_url, payment_id = await create_payment(user_id, return_url)
        
        await state.update_data(last_payment_id=payment_id)
        await state.set_state(PaymentStates.waiting_for_payment)
        
        await callback.message.edit_text(
            PAYMENT_SECURITY,
            reply_markup=payment_keyboard(payment_url)
        )
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await callback.message.edit_text("Ошибка создания платежа.")
    
    await callback.answer()


@dp.callback_query(F.data == "check_payment_status")
async def callback_check_payment(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Проверка оплаты"""
    user_id = callback.from_user.id
    data = await state.get_data()
    payment_id = data.get("last_payment_id")
    
    if not payment_id:
        await callback.answer("Информация о платеже утеряна. Попробуйте заново.", show_alert=True)
        return
    
    await callback.answer("Проверяю...")
    
    def check_payment():
        Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
        Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")
        return Payment.find_one(payment_id)
    
    try:
        payment = await asyncio.to_thread(check_payment)
        
        if payment.status == "succeeded":
            await activate_subscription(user_id)
            await state.clear()
            
            await callback.message.edit_text(
                "Оплата прошла! Premium активирован.",
                reply_markup=menu_start_with_sub()
            )
        elif payment.status == "pending":
            await callback.answer("Оплата в обработке. Подождите.", show_alert=True)
        else:
            await callback.answer(f"Статус: {payment.status}", show_alert=True)
    except Exception as e:
        logger.error(f"Payment check error: {e}")
        await callback.answer("Ошибка проверки.", show_alert=True)


# ==================== НАВИГАЦИЯ ====================

@dp.callback_query(F.data == "back_to_menu")
async def callback_back(callback: types.CallbackQuery) -> None:
    """Назад в меню"""
    user_id = callback.from_user.id
    await callback.message.answer(await get_menu_text(user_id), reply_markup=await get_main_menu(user_id))
    await callback.answer()


# ==================== WEBHOOK ====================

async def handle_webhook(request: web.Request) -> web.Response:
    secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    if secret != os.getenv("WEBHOOK_SECRET"):
        return web.Response(status=403, text="Forbidden")
    
    try:
        update = types.Update(**await request.json())
        await dp.feed_webhook_update(bot, update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    
    return web.Response(status=200)


async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="OK")

@dp.callback_query(F.data == "sos_locked")
async def callback_sos_locked(callback: types.CallbackQuery) -> None:
    """SOS заблокирован для бесплатных"""
    await callback.message.edit_text(
        "SOS доступен в Premium.\n\n"
        "149₽/мес — SOS, расширенная статистика, тренды.",
        reply_markup=paywall_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "tariffs")
async def callback_tariffs(callback: types.CallbackQuery) -> None:
    """Тарифы"""
    is_prem = await is_premium(callback.from_user.id)
    
    status = await get_user_status(callback.from_user.id)
    sub_text = ""
    if status["is_paid"] and status["subscription_end_date"]:
        try:
            end_date = datetime.fromisoformat(status["subscription_end_date"])
            sub_text = f"\n\nВаша подписка до: {end_date.strftime('%d.%m.%Y')}"
        except:
            pass
    
    text = f"""Тарифы UnTT

Premium (149₽/мес):
• SOS — экстренная помощь
• Статистика за неделю/месяц
• Тренды и средние
• Безлимитный SOS

Бесплатно:
• Иду в TikTok
• Статистика за сегодня{sub_text}"""
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить Premium", callback_data="subscribe")] if not is_prem else InlineKeyboardButton(text="Назад", callback_data="back_to_menu")
    ]))
    await callback.answer()


@dp.callback_query(F.data == "help")
async def callback_help(callback: types.CallbackQuery) -> None:
    """Помощь"""
    text = """Справка UnTT

/start — Главное меню
/menu — Простое меню
/cancel — Отмена

Кнопки:
• Иду в TikTok — осознанный таймер
• SOS — экстренная помощь (Premium)
• Статистика — твой прогресс
• Подписка — Premium функции

Поддержка: @prosto_m1f"""
    
    await callback.message.edit_text(text, reply_markup=back_keyboard())
    await callback.answer()

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext) -> None:
    """Простое меню без подписки и тарифов"""
    user_id = message.from_user.id
    await state.clear()
    
    is_prem = await is_premium(user_id)
    
    if is_prem:
        text = MENU_WITH_SUB.format(
            count=(await get_today_stats(user_id))["count"],
            saved_time=(await get_today_stats(user_id))["saved_time"]
        )
        await message.answer(text, reply_markup=menu_with_sub())
    else:
        text = MENU_NO_SUB.format(
            count=(await get_today_stats(user_id))["count"],
            saved_time=(await get_today_stats(user_id))["saved_time"]
        )
        await message.answer(text, reply_markup=menu_no_sub())


# ==================== MAIN ====================

async def main():
    port = int(os.getenv("PORT", 10000))
    webhook_url = os.getenv("WEBHOOK_URL")
    webhook_path = os.getenv("WEBHOOK_PATH", "/webhook")
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    
    if not webhook_url:
        logger.critical("WEBHOOK_URL не задан!")
        return
    
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(url=webhook_url, secret_token=webhook_secret)
    
    app = web.Application()
    app.router.add_post(webhook_path, handle_webhook)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host='0.0.0.0', port=port)
    await site.start()
    
    logger.info(f"Бот запущен на порту {port}")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except:
        pass
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())