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
        self.data = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Загружает статистику пользователя с поддержкой старых форматов."""
        try:
            stats_data = load_user_data(self.stats_key)
            if not stats_data:
                # Если файла нет, создаем дефолтный
                stats_data = self._create_default_stats()
                self._save_stats(stats_data)
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
                "active_days": 0
            }
        }
    
    def _save_stats(self, stats_data: Dict = None) -> bool:
        """Сохраняет статистику пользователя."""
        try:
            data_to_save = stats_data or self.data
            data_to_save["updated_at"] = get_moscow_time().isoformat()
            save_user_data(self.stats_key, data_to_save)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики для user_id {self.user_id}: {e}")
            return False
    
    def _add_event(self, event_type: str, event_data: Dict = None) -> None:
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
        self._update_streak()
        
        # Сохраняем изменения
        self._save_stats()
    
    def _update_streak(self) -> None:
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
    
    def update_stats(self, event_type: str, event_data: Dict = None) -> bool:
        """Обновляет статистику пользователя."""
        try:
            if event_type not in self.data["events"]:
                logger.warning(f"Неизвестный тип события: {event_type}")
                return False
            
            self._add_event(event_type, event_data)
            logger.info(f"Статистика обновлена для user_id {self.user_id}: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления статистики: {e}")
            return False
    
    def get_stats(self, period: str = "total") -> Dict:
        """Получает статистику пользователя за указанный период."""
        try:
            today = get_moscow_time().date()
            
            if period == "day":
                start_date = today
            elif period == "week":
                start_date = today - timedelta(days=7)
            elif period == "month":
                start_date = today - timedelta(days=30)
            else:
                start_date = datetime.min.date()
            
            period_stats = {
                "period": period,
                "date_range": {
                    "from": start_date.isoformat(),
                    "to": today.isoformat()
                },
                "events_count": {
                    "quick_pause": 0,
                    "sos": 0,
                    "daily_practice": 0,
                    "tree_growth": 0,
                    "tiktok_attempt": 0,
                    "conscious_stop": 0
                },
                "streak_info": self.data["streaks"].copy(),
                "total_events": 0
            }
            
            for event_type, events in self.data["events"].items():
                for event in events:
                    event_date = datetime.fromisoformat(event["timestamp"]).date()
                    if event_date >= start_date and event_date <= today:
                        if event_type in period_stats["events_count"]:
                            period_stats["events_count"][event_type] += 1
                            period_stats["total_events"] += 1
            
            return period_stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"error": str(e)}    

# Вспомогательные асинхронные функции
async def update_stats(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    stats = UserStats(user_id)
    return stats.update_stats(event_type, event_data)

async def get_stats(user_id: int, period: str = "total") -> Dict:
    stats = UserStats(user_id)
    return stats.get_stats(period)