import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

from config.texts import *
from config.menu import *

# Импорты для статистики и оплаты (оставляем как было)
try:
    from stats.user_stats import UserStats, update_stats
except ImportError:
    UserStats = None
    update_stats = None

try:
    from payment.yookassa_client import create_payment
except ImportError:
    create_payment = None

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ПУТИ ---
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# --- СОСТОЯНИЯ FSM ---
class QuickPauseStates(StatesGroup):
    waiting_purpose = State()
    waiting_time = State()
    waiting_confirmation = State()

class SosStates(StatesGroup):
    waiting_priority = State()
    waiting_confirmation = State()


# ==================== ПРОВЕРКИ ДОСТУПА ====================

async def get_user_status(user_id: int) -> dict:
    """Получить статус пользователя"""
    status_file = DATA_DIR / "user_status.json"
    if not status_file.exists():
        return {"is_paid": False}
    
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id), {"is_paid": False})
    except:
        return {"is_paid": False}


async def update_user_status(user_id: int, key: str, value) -> None:
    """Обновить статус пользователя"""
    status_file = DATA_DIR / "user_status.json"
    
    try:
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    
    if str(user_id) not in data:
        data[str(user_id)] = {"is_paid": False}
    
    data[str(user_id)][key] = value
    
    with open(status_file, "w", encoding="utf-8") as f:
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
        return 0
    try:
        reg_date = datetime.fromisoformat(reg_date_str)
        return (datetime.now() - reg_date).days
    except:
        return 0


# ==================== СТАТИСТИКА ====================

async def get_today_stats(user_id: int) -> dict:
    """Статистика за сегодня (доступно всем)"""
    if not UserStats:
        return {"count": 0, "saved_time": "0 мин"}
    
    try:
        stats = UserStats(user_id)
        data = await stats._load_stats()
        
        today = datetime.now().date().isoformat()
        today_events = [
            e for e in data.get("events", {}).get("conscious_stop", [])
            if e.get("date") == today
        ]
        
        saved_minutes = len(today_events) * 15
        return {"count": len(today_events), "saved_time": f"{saved_minutes} мин"}
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"count": 0, "saved_time": "0 мин"}


async def get_full_stats(user_id: int) -> dict:
    """Полная статистика (только премиум)"""
    if not UserStats:
        return {"today": 0, "week_avg": 0, "days": 0}
    
    try:
        stats = UserStats(user_id)
        data = await stats._load_stats()
        
        today = datetime.now().date().isoformat()
        today_events = [
            e for e in data.get("events", {}).get("conscious_stop", [])
            if e.get("date") == today
        ]
        
        # Неделя
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        week_total = 0
        for event_type in ["conscious_stop", "quick_pause"]:
            events = data.get("events", {}).get(event_type, [])
            week_events = [e for e in events if e.get("date", "") >= week_ago]
            week_total += len(week_events)
        
        week_avg = week_total // 7 if week_total > 0 else 0
        days = await get_usage_days(user_id)
        
        return {
            "today": len(today_events),
            "week_avg": week_avg,
            "days": days,
            "saved": len(today_events) * 15
        }
    except Exception as e:
        logger.error(f"Full stats error: {e}")
        return {"today": 0, "week_avg": 0, "days": 0}


# ==================== ВЫБОР МЕНЮ ====================

async def get_main_menu(user_id: int) -> InlineKeyboardMarkup:
    """Главное меню - зависит от подписки"""
    if await is_premium(user_id):
        return menu_with_sub()
    return menu_no_sub()


async def get_start_menu(user_id: int) -> InlineKeyboardMarkup:
    """Стартовое меню"""
    if await is_premium(user_id):
        return menu_start_with_sub()
    return menu_start_no_sub()


# ==================== ОБРАБОТЧИКИ ====================

async def cmd_start(message: types.Message, state: FSMContext) -> None:
    """Старт бота"""
    user_id = message.from_user.id
    await state.clear()
    
    # Регистрация - сохраняем дату
    status = await get_user_status(user_id)
    if "registration_date" not in status:
        await update_user_status(user_id, "registration_date", datetime.now().isoformat())
    
    # Выбираем текст
    is_prem = await is_premium(user_id)
    text = START_WITH_SUB if is_prem else START_NO_SUB
    
    await message.answer(text, reply_markup=await get_start_menu(user_id))


async def callback_go_tiktok(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Старт: Иду в TikTok (доступно всем)"""
    await state.set_state(QuickPauseStates.waiting_purpose)
    
    # Учитываем попытку
    if update_stats:
        try:
            await update_stats(callback.from_user.id, "tiktok_attempt")
        except:
            pass
    
    await callback.message.edit_text(QP_REASON, reply_markup=qp_reason_keyboard())
    await callback.answer()


async def callback_qp_reason(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Выбор причины"""
    await state.update_data(reason=callback.data)
    await state.set_state(QuickPauseStates.waiting_time)
    
    await callback.message.edit_text(QP_TIME, reply_markup=qp_time_keyboard())
    await callback.answer()


async def callback_qp_time(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Выбор времени - запуск таймера"""
    minutes = int(callback.data.split("_")[-1])
    await state.update_data(minutes=minutes)
    await state.set_state(QuickPauseStates.waiting_confirmation)
    
    await callback.message.edit_text(
        QP_TIMER.format(minutes=minutes),
        reply_markup=qp_timer_keyboard()
    )
    await callback.answer()
    
    # Таймер в фоне
    await asyncio.sleep(minutes * 60)
    
    # Проверяем, не отменили ли
    current_state = await state.get_state()
    if current_state == QuickPauseStates.waiting_confirmation:
        await qp_timer_done(callback, state)


async def callback_qp_stop(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Остановка таймера раньше времени"""
    user_id = callback.from_user.id
    user_data = await state.get_data()
    planned = user_data.get("minutes", 0)
    saved = min(planned, 15)
    
    # Статистика
    if update_stats:
        try:
            await update_stats(user_id, "conscious_stop")
        except:
            pass
    
    await state.clear()
    
    await callback.message.edit_text(
        QP_STOPPED_EARLY.format(saved=saved),
        reply_markup=await get_main_menu(user_id)
    )
    await callback.answer()


async def qp_timer_done(callback: types.CallbackQuery, state: FSMContext):
    """Таймер завершён"""
    user_id = callback.from_user.id
    await callback.message.edit_text(QP_DONE)
    await asyncio.sleep(1)
    await callback.message.answer(
        await get_menu_text(user_id),
        reply_markup=await get_main_menu(user_id)
    )
    await state.clear()


async def get_menu_text(user_id: int) -> str:
    """Текст меню с цифрами"""
    stats = await get_today_stats(user_id)
    is_prem = await is_premium(user_id)
    
    if is_prem:
        return MENU_WITH_SUB.format(count=stats["count"], saved_time=stats["saved_time"])
    return MENU_NO_SUB.format(count=stats["count"], saved_time=stats["saved_time"])


async def callback_stats(callback: types.CallbackQuery) -> None:
    """Статистика - разная для бесплатного и премиума"""
    user_id = callback.from_user.id
    is_prem = await is_premium(user_id)
    
    if is_prem:
        # Полная статистика (премиум)
        stats = await get_full_stats(text)
        text = STATS_PREMIUM.format(
            today_count=stats["today"],
            saved_time=f"{stats['saved']} мин",
            days_count=stats["days"],
            week_avg=f"{stats['week_avg']}/день"
        )
    else:
        # Только сегодня (бесплатно)
        stats = await get_today_stats(user_id)
        text = STATS_FREE.format(
            today_count=stats["count"],
            saved_time=stats["saved_time"]
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=stats_keyboard(is_prem)
    )
    await callback.answer()


async def callback_sos(callback: types.CallbackQuery, state: FSMContext) -> None:
    """SOS - только для премиума!"""
    user_id = callback.from_user.id
    
    if not await is_premium(user_id):
        # Показываем что нужен премиум
        await callback.message.edit_text(
            SOS_NEED_PREMIUM,
            reply_markup=paywall_keyboard()
        )
        await callback.answer()
        return
    
    await state.set_state(SosStates.waiting_priority)
    await callback.message.edit_text(SOS_PRIORITY, reply_markup=sos_priority_keyboard())
    await callback.answer()


async def callback_sos_priority(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Выбор приоритета SOS"""
    priority_map = {
        "work": "Учёба/работа",
        "sleep": "Сон",
        "sport": "Спорт",
        "people": "Друзья/семья",
        "hobby": "Хобби"
    }
    
    prio = callback.data.split("_")[-1]
    choice = priority_map.get(prio, "Это")
    
    await state.update_data(priority=choice)
    await state.set_state(SosStates.waiting_confirmation)
    
    await callback.message.edit_text(
        SOS_CONFIRM.format(choice=choice),
        reply_markup=sos_confirm_keyboard()
    )
    await callback.answer()


async def callback_sos_close(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Оставил закрытым"""
    user_id = callback.from_user.id
    
    if update_stats:
        try:
            await update_stats(user_id, "conscious_stop")
        except:
            pass
    
    await state.clear()
    await callback.message.edit_text("Запомним.")
    await asyncio.sleep(0.5)
    await callback.message.answer(
        await get_menu_text(user_id),
        reply_markup=await get_main_menu(user_id)
    )
    await callback.answer()


async def callback_sos_open(callback: types.CallbackQuery, state: FSMContext) -> None:
    """Открыл всё равно"""
    await state.clear()
    await callback.message.edit_text("Ок.")
    await callback.answer()


async def callback_subscribe(callback: types.CallbackQuery) -> None:
    """Показать экран оплаты"""
    days = await get_usage_days(callback.from_user.id)
    
    if days >= 3:
        text = PAYLOCK_LIMITED
    else:
        text = PAYLOAD_3DAYS.format(days=days)
    
    try:
        await callback.message.edit_text(text, reply_markup=paywall_keyboard())
    except:
        await callback.message.answer(text, reply_markup=paywall_keyboard())
    
    await callback.answer()


async def callback_pay_unlock(callback: types.CallbackQuery) -> None:
    """Создание платежа"""
    user_id = callback.from_user.id
    
    if not create_payment:
        await callback.message.edit_text("Оплата временно недоступна.")
        await callback.answer()
        return
    
    try:
        payment_url = await create_payment(user_id, 14900)  # 149.00 руб
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 149₽", url=payment_url)],
            [InlineKeyboardButton(text="Проверить оплату", callback_data="check_payment")]
        ])
        
        await callback.message.edit_text(
            "Оплата:\n149₽ разово, без автосписания",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Payment error: {e}")
        await callback.message.edit_text("Ошибка создания платежа.")
    
    await callback.answer()


async def callback_check_payment(callback: types.CallbackQuery) -> None:
    """Проверка оплаты (упрощённо - в реальности вебхук)"""
    user_id = callback.from_user.id
    
    # Здесь должна быть проверка через YooKassa API
    # Для упрощения - сразу активируем (в реальности - проверять статус)
    await update_user_status(user_id, "is_paid", True)
    
    await callback.message.edit_text("Оплата прошла! Premium активирован.")
    await asyncio.sleep(1)
    await callback.message.answer(
        START_WITH_SUB,
        reply_markup=menu_start_with_sub()
    )
    await callback.answer()


# ==================== РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ====================

def register_handlers(dp: Dispatcher):
    # Команды
    dp.message.register(cmd_start, Command("start"))
    
    # Quick Pause
    dp.callback_query.register(callback_go_tiktok, F.data == "go_tiktok")
    dp.callback_query.register(callback_qp_reason, F.data.startswith("qp_reason_"))
    dp.callback_query.register(callback_qp_time, F.data.startswith("qp_time_"))
    dp.callback_query.register(callback_qp_stop, F.data == "qp_stop")
    
    # Статистика
    dp.callback_query.register(callback_stats, F.data == "stats")
    
    # SOS (премиум)
    dp.callback_query.register(callback_sos, F.data == "sos")
    dp.callback_query.register(callback_sos_priority, F.data.startswith("sos_prio_"))
    dp.callback_query.register(callback_sos_close, F.data == "sos_close")
    dp.callback_query.register(callback_sos_open, F.data == "sos_open")
    
    # Подписка
    dp.callback_query.register(callback_subscribe, F.data == "subscribe")
    dp.callback_query.register(callback_pay_unlock, F.data == "pay_unlock")
    dp.callback_query.register(callback_check_payment, F.data == "check_payment")


# ==================== ЗАПУСК ====================

async def main():
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher(storage=MemoryStorage())
    
    register_handlers(dp)
    
    # Удаляем вебхук и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())