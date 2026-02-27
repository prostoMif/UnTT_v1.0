"""Модуль статистики пользователя."""
import logging
from datetime import datetime, timedelta
from typing import Dict
import os

from utils.storage import save_user_data, load_user_data
from daily_practice.schedule import get_moscow_time

logger = logging.getLogger(__name__)

class UserStats:
    """Класс для управления статистикой пользователя."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.stats_key = f"user_stats_{user_id}"
        self.data = None  # Данные будут загружены при первом запросе (lazy loading)

    def _create_default_stats(self) -> Dict:
        """Создает структуру статистики по умолчанию."""
        return {
            "user_id": self.user_id,
            "created_at": get_moscow_time().isoformat(),
            "events": {
                "quick_pause": [],
                "sos": [],
                "daily_practice": [],
                "tree_growth": [],
                "tiktok_attempt": [],
                "conscious_stop": []
            },
            "streaks": {
                "current": 0,
                "best": 0,
                "last_active_date": None
            },
            "summary": {
                "total_events": 0,
                "total_pauses": 0,
                "total_sos": 0,
                "total_practices": 0,
                "total_tree_growth": 0,
                "active_days": 0,
                "slips_today": 0
            },
            "last_slip_date": None
        }

    async def _load_stats(self) -> Dict:
        """Асинхронно загружает статистику пользователя."""
        try:
            # load_user_data - СИНХРОННАЯ функция, await НЕ нужен
            stats_data = load_user_data(self.stats_key)
            
            if not stats_data:
                # Если файла нет, создаем дефолтный и сохраняем
                stats_data = self._create_default_stats()
                await self._save_stats(stats_data)
                return stats_data
            
            # МИГРАЦИЯ: Проверяем, есть ли новые ключи в старом файле
            defaults = self._create_default_stats()
            
            # Проверяем секцию events
            if "events" not in stats_data:
                stats_data["events"] = defaults["events"]
            else:
                # Добавляем недостающие типы событий
                for event_type, default_list in defaults["events"].items():
                    if event_type not in stats_data["events"]:
                        stats_data["events"][event_type] = []
            
            # Проверяем остальные секции
            if "streaks" not in stats_data:
                stats_data["streaks"] = defaults["streaks"]
            if "summary" not in stats_data:
                stats_data["summary"] = defaults["summary"]
                
            return stats_data
                
        except Exception as e:
            logger.error(f"Ошибка загрузки статистики для user_id {self.user_id}: {e}")
            return self._create_default_stats()

    async def _save_stats(self, stats_data: Dict = None) -> bool:
        """Асинхронно сохраняет статистику пользователя."""
        try:
            data_to_save = stats_data or self.data
            data_to_save["updated_at"] = get_moscow_time().isoformat()
            
            # Меняем местами аргументы: сначала данные, потом ключ
            await save_user_data(data_to_save, self.stats_key)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики для user_id {self.user_id}: {e}")
            return False

    async def _update_streak(self) -> None:
        """Обновляет информацию о серии активных дней."""
        today = get_moscow_time().date()
        last_active = self.data["streaks"]["last_active_date"]
        
        if last_active:
            last_date = datetime.fromisoformat(last_active).date()
            delta = (today - last_date).days
            
            if delta == 0:
                return
            elif delta == 1:
                self.data["streaks"]["current"] += 1
            else:
                self.data["streaks"]["current"] = 1
            
            if self.data["streaks"]["current"] > self.data["streaks"]["best"]:
                self.data["streaks"]["best"] = self.data["streaks"]["current"]
        else:
            self.data["streaks"]["current"] = 1
            self.data["streaks"]["best"] = 1
        
        self.data["streaks"]["last_active_date"] = today.isoformat()
        self.data["summary"]["active_days"] += 1

    async def _add_event(self, event_type: str, event_data: Dict = None) -> None:
        """Добавляет событие в статистику."""
        event_data = event_data or {}
        event_data.update({
            "timestamp": get_moscow_time().isoformat(),
            "date": get_moscow_time().date().isoformat()
        })
        
        self.data["events"][event_type].append(event_data)
        self.data["summary"]["total_events"] += 1
        
        # Обновляем счетчики по типам
        if event_type == "quick_pause":
            self.data["summary"]["total_pauses"] += 1
        elif event_type == "sos":
            self.data["summary"]["total_sos"] += 1
        elif event_type == "daily_practice":
            self.data["summary"]["total_practices"] += 1
        elif event_type == "tree_growth":
            self.data["summary"]["total_tree_growth"] += 1
        
        # Обновляем streak
        await self._update_streak()
        
        # Сохраняем изменения
        await self._save_stats()

    async def update_stats(self, event_type: str, event_data: Dict = None) -> bool:
        """Публичный метод для обновления статистики."""
        try:
            # Если данные еще не загружены, загружаем их
            if self.data is None:
                self.data = await self._load_stats()
                
            await self._add_event(event_type, event_data)
            return True
        except Exception as e:
            logger.error(f"Ошибка в update_stats: {e}")
            return False

    async def get_stats(self, period: str = "total") -> Dict:
        """Получить статистику за период: today, week, month, total"""
        data = await self._load_stats()
        
        now = get_moscow_time()
        if period == "today":
            start_date = now.date()
        elif period == "week":
            start_date = (now - timedelta(days=7)).date()
        elif period == "month":
            start_date = (now - timedelta(days=30)).date()
        else:
            start_date = None
        
        result = {"events_count": {}}
        
        for event_type, events in data.get("events", {}).items():
            if start_date:
                count = sum(1 for e in events if e.get("date", "") >= start_date.isoformat())
            else:
                count = len(events)
            result["events_count"][event_type] = count
        
        return result

    async def increment_slip(self) -> int:
        """
        Увеличивает счетчик срывов за сегодня.
        Сбрасывает счетчик, если наступил новый день (после 7:00 МСК).
        Возвращает текущее значение счетчика.
        """
        now = get_moscow_time()
        
        # Логика "Новый день" начинается в 07:00
        # Если сейчас раньше 7 утра, считаем, что всё еще "вчерашний" день
        today_date = now.date()
        if now.hour < 7:
            today_date = today_date - timedelta(days=1)

        last_slip_str = self.data.get("last_slip_date")
        reset_needed = False

        if last_slip_str:
            # Парсим дату последнего срыва (хранится как ISO date string, YYYY-MM-DD)
            # Если хранится полный ISO timestamp, берем только дату
            try:
                if "T" in last_slip_str:
                    last_date = datetime.fromisoformat(last_slip_str).date()
                else:
                    last_date = datetime.strptime(last_slip_str, "%Y-%m-%d").date()
                
                if last_date < today_date:
                    reset_needed = True
            except Exception:
                reset_needed = True
        else:
            reset_needed = True

        if reset_needed:
            self.data["summary"]["slips_today"] = 0

        # Увеличиваем счетчик
        current_count = self.data["summary"].get("slips_today", 0) + 1
        self.data["summary"]["slips_today"] = current_count
        
        # Сохраняем дату последнего срыва (только дата, без времени)
        self.data["last_slip_date"] = today_date.isoformat()
        
        await self._save_stats()
        return current_count   
    
    

# --- Асинхронные обертки (добавить после класса) ---

async def update_stats(user_id: int, event_type: str, event_data: dict = None) -> bool:
    """Асинхронная функция-обертка для обновления статистики."""
    try:
        stats = UserStats(user_id)
        return await stats.update_stats(event_type, event_data)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка в async wrapper update_stats для user {user_id}: {e}")
        return False

async def get_stats(user_id: int, period: str = "total") -> dict:
    """Асинхронная функция-обертка для получения статистики."""
    try:
        stats = UserStats(user_id)
        return await stats.get_stats(period)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка в async wrapper get_stats для user {user_id}: {e}")
        return {}







# --- Асинхронные обертки (обязательно заменить старые) ---

async def update_stats(user_id: int, event_type: str, event_data: dict = None) -> bool:
    """Асинхронная функция-обертка для обновления статистики."""
    try:
        stats = UserStats(user_id)
        # ВАЖНО: Добавляем await, так как метод класса теперь асинхронный
        return await stats.update_stats(event_type, event_data)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка в async wrapper update_stats для user {user_id}: {e}")
        return False

async def get_stats(user_id: int, period: str = "total") -> dict:
    """Асинхронная функция-обертка для получения статистики."""
    try:
        stats = UserStats(user_id)
        # ВАЖНО: Добавляем await, так как метод класса теперь асинхронный
        return await stats.get_stats(period)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка в async wrapper get_stats для user {user_id}: {e}")
        return {}