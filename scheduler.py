"""Система напоминаний для дневной практики и проверки подписок."""
import asyncio
import os
import json
from datetime import datetime, time, timedelta
from typing import List, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
import pytz
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Импорты из твоего проекта
from daily_check.check import save_daily_data
from daily_practice.schedule import get_user_practice_status, get_moscow_time
from utils.storage import load_user_data

# Настройка таймзоны Москвы
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Глобальная переменная для хранения экземпляра планировщика
_scheduler_instance = None

class ReminderScheduler:
    """Класс для управления системой напоминаний."""
    
    def __init__(self, bot):
        """Инициализация планировщика при создании объекта."""
        self.scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)
        self.bot = bot
        
        # Планируем задачи сразу при инициализации
        self._schedule_subscription_checks()
        self._schedule_daily_reminders()

    def _schedule_subscription_checks(self):
        """Добавляет задачу проверки подписок в планировщик."""
        self.scheduler.add_job(
            self.check_subscriptions_and_remind,
            'interval',
            days=1,  # Раз в день
            id='check_subscription_reminders',
            replace_existing=True
        )

    def _schedule_daily_reminders(self):
        """Планирование ежедневных напоминаний в 19:00 МСК."""
        self.scheduler.add_job(
            self.send_daily_reminders,
            'cron',
            hour=19,
            minute=0,
            id='daily_reminder',
            replace_existing=True
        )

    async def check_subscriptions_and_remind(self):
        """Проверяет окончания подписок и отправляет напоминания."""
        file_path = "data/user_preferences.json"
        if not os.path.exists(file_path):
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            now = datetime.now()
            reminder_threshold = timedelta(days=2) # Напоминать за 2 дня

            for user_id_str, user_data in data.items():
                user_id = int(user_id_str)
                sub_end_str = user_data.get("subscription_end_date")
                
                if sub_end_str:
                    try:
                        sub_end = datetime.fromisoformat(sub_end_str)
                        time_left = sub_end - now

                        # Если осталось 2 дня или меньше, но подписка еще активна
                        if timedelta(0) < time_left <= reminder_threshold:
                            days_left = time_left.days + 1 # Округление
                            await self._send_subscription_reminder(user_id, days_left)
                            
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Ошибка проверки подписок: {e}")

    async def _send_subscription_reminder(self, user_id: int, days_left: int):
        """Отправляет напоминание о подписке."""
        text = (
            f"⏳ <b>Внимание!</b>\n\n"
            f"Твоя подписка на unTT закончится через {days_left} дн.\n\n"
            f"Чтобы не потерять прогресс дерева, продли доступ заранее."
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Продлить подписку", callback_data="pay_unlock")]
        ])
        
        try:
            await self.bot.send_message(user_id, text, parse_mode="HTML", reply_markup=keyboard)
        except Exception as e:
            print(f"Не удалось отправить напоминание {user_id}: {e}")

    async def send_daily_reminders(self):
        """Отправка напоминаний пользователям, которые не выполнили практику."""
        try:
            print(f"[{get_moscow_time()}] Начинаю отправку напоминаний о практике...")
            
            users_to_remind = await self._get_users_needing_reminder()
            
            if not users_to_remind:
                print("Нет пользователей для напоминания")
                return
            
            print(f"Найдено {len(users_to_remind)} пользователей для напоминания")
            
            for user_data in users_to_remind:
                await self._send_reminder_to_user(user_data)
                
        except Exception as e:
            print(f"Ошибка при отправке напоминаний: {e}")
    
    async def _get_users_needing_reminder(self) -> List[Dict]:
        """Получение списка пользователей, которым нужно отправить напоминание."""
        try:
            all_users_data = load_user_data()
            users_to_remind = []
            today = get_moscow_time().date()
            
            for user_id, user_data in all_users_data.items():
                user_id = int(user_id)
                practice_status = await get_user_practice_status(user_id)
                last_completion_date = practice_status.get('last_completion_date')
                
                if last_completion_date:
                    last_date = datetime.fromisoformat(last_completion_date).date()
                    if last_date == today:
                        continue
                
                users_to_remind.append({
                    'user_id': user_id,
                    'username': user_data.get('username', 'Пользователь'),
                    'full_name': user_data.get('full_name', 'Без имени')
                })
            
            return users_to_remind
            
        except Exception as e:
            print(f"Ошибка при получении списка пользователей: {e}")
            return []
    
    async def _send_reminder_to_user(self, user_data: Dict):
        """Отправка напоминания конкретному пользователю."""
        try:
            user_id = user_data['user_id']
            full_name = user_data.get('full_name', 'Друг')
            
            reminder_text = (
                f"⏰ Напоминание, {full_name}!\n\n"
                "📅 Сегодня еще не выполнена дневная практика.\n\n"
                "🌱 Помни: каждый день важен для твоего роста!\n"
                "💪 Пропустишь день - и прогресс остановится.\n\n"
                "Выполни практику сейчас, чтобы не потерять достижения! 🚀"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📚 Начать практику", callback_data="daily_practice")]
            ])
            
            if self.bot:
                await self.bot.send_message(
                    chat_id=user_id,
                    text=reminder_text,
                    reply_markup=keyboard
                )
            else:
                print(f"Bot не инициализирован, не могу отправить сообщение пользователю {user_id}")
            
            print(f"Напоминание отправлено пользователю {user_id}")
            
        except Exception as e:
            print(f"Ошибка отправки напоминания пользователю {user_data['user_id']}: {e}")

    def start(self):
        """Запуск планировщика."""
        if not self.scheduler.running:
            self.scheduler.start()
            print("Планировщик запущен.")
    
    def stop(self):
        """Остановка планировщика."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("Планировщик остановлен.")

# Функции для управления извне (из bot.py)

async def start_reminder_system(bot):
    """Запуск системы напоминаний."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ReminderScheduler(bot)
        _scheduler_instance.start()
        print("Система напоминаний инициализирована и запущена.")
    else:
        print("Система напоминаний уже запущена.")

async def stop_reminder_system():
    """Остановка системы напоминаний."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None
        print("Система напоминаний остановлена.")