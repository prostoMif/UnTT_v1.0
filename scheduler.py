"""Система напоминаний для дневной практики."""
import asyncio
from datetime import datetime, time
from typing import List, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.memory import MemoryJobStore
import pytz

from daily_check.check import save_daily_data
from daily_practice.schedule import get_user_practice_status, get_moscow_time
from utils.storage import load_user_data


# Настройка таймзоны Москвы
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

class ReminderScheduler:
    """Класс для управления системой напоминаний."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            timezone=MOSCOW_TZ,
            jobstores={
                'default': MemoryJobStore()
            },
            executors={
                'default': AsyncIOExecutor()
            },
            job_defaults={
                'coalesce': False,
                'max_instances': 1
            }
        )
    
    def start(self):
        """Запуск планировщика."""
        self.scheduler.start()
        self._schedule_daily_reminders()
    
    def stop(self):
        """Остановка планировщика."""
        self.scheduler.shutdown()
    
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
    
    async def send_daily_reminders(self):
        """Отправка напоминаний пользователям, которые не выполнили практику."""
        try:
            print(f"[{get_moscow_time()}] Начинаю отправку напоминаний...")
            
            # Получаем список всех пользователей
            users_to_remind = await self._get_users_needing_reminder()
            
            if not users_to_remind:
                print("Нет пользователей для напоминания")
                return
            
            print(f"Найдено {len(users_to_remind)} пользователей для напоминания")
            
            # Отправляем напоминания
            for user_data in users_to_remind:
                await self._send_reminder_to_user(user_data)
                
        except Exception as e:
            print(f"Ошибка при отправке напоминаний: {e}")
    
    async def _get_users_needing_reminder(self) -> List[Dict]:
        """Получение списка пользователей, которым нужно отправить напоминание."""
        try:
            # Загружаем всех пользователей из storage
            all_users_data = load_user_data()
            
            users_to_remind = []
            today = get_moscow_time().date()
            
            for user_id, user_data in all_users_data.items():
                user_id = int(user_id)
                
                # Проверяем статус практики пользователя
                practice_status = await get_user_practice_status(user_id)
                
                # Проверяем, выполнял ли пользователь практику сегодня
                last_completion_date = practice_status.get('last_completion_date')
                
                if last_completion_date:
                    last_date = datetime.fromisoformat(last_completion_date).date()
                    
                    # Если последняя практика была сегодня - пропускаем
                    if last_date == today:
                        continue
                
                # Если практика не выполнялась сегодня - добавляем в список
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
        username = user_data.get('username', '')
        full_name = user_data.get('full_name', 'Друг')
        
        reminder_text = (
            f"⏰ Напоминание, {full_name}!\n\n"
            "📅 Сегодня еще не выполнена дневная практика.\n\n"
            "🌱 Помни: каждый день важен для твоего роста!\n"
            "💪 Пропустишь день - и прогресс остановится.\n\n"
            "Выполни практику сейчас, чтобы не потерять достижения! 🚀"
        )
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📚 Начать практику",
                callback_data="daily_practice"
            )]
        ])
        
        # Используем self.bot вместо bot
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

# Глобальный экземпляр планировщика
reminder_scheduler = ReminderScheduler()

async def start_reminder_system():
    """Запуск системы напоминаний."""
    reminder_scheduler.start()
    print("Система напоминаний запущена. Напоминания будут приходить в 19:00 МСК")

async def stop_reminder_system():
    """Остановка системы напоминаний."""
    reminder_scheduler.stop()
    print("Система напоминаний остановлена")