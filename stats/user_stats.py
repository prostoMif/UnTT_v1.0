"""Модуль статистики пользователя."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from collections import defaultdict
import json
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
        """Загружает статистику пользователя."""
        try:
            stats_data = load_user_data(self.stats_key)
            if not stats_data:
                # Создаем новую статистику
                stats_data = self._create_default_stats()
                self._save_stats(stats_data)
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
                "tree_growth": []
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
                # Сегодня уже была активность
                return
            elif delta == 1:
                # Продолжаем серию
                self.data["streaks"]["current"] += 1
            else:
                # Серия прервана
                self.data["streaks"]["current"] = 1
            
            # Обновляем лучшую серию
            if self.data["streaks"]["current"] > self.data["streaks"]["best"]:
                self.data["streaks"]["best"] = self.data["streaks"]["current"]
        else:
            # Первая активность
            self.data["streaks"]["current"] = 1
            self.data["streaks"]["best"] = 1
        
        self.data["streaks"]["last_active_date"] = today.isoformat()
        self.data["summary"]["active_days"] += 1
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.stats_key = f"user_stats_{user_id}"
        
        # Создаем директорию для статистики
        stats_dir = "data/stats"
        os.makedirs(stats_dir, exist_ok=True)
        
        self.data = self._load_stats()
    
    def update_stats(self, event_type: str, event_data: Dict = None) -> bool:
        """
        Обновляет статистику пользователя.
        
        Args:
            event_type: Тип события ('quick_pause', 'sos', 'daily_practice', 'tree_growth')
            event_data: Дополнительные данные события
            
        Returns:
            bool: Успех обновления
        """
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
    
    def _add_event(self, event_type: str, event_data: Dict = None) -> None:
        """Добавляет событие в статистику."""
        event_data = event_data or {}
        event_data.update({
            "timestamp": get_moscow_time().isoformat(),
            "date": get_moscow_time().date().isoformat()
        })
        
        print(f"Добавляем событие {event_type} для user_id {self.user_id}")  # Отладка
        
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
    
        print(f"Статистика обновлена: {self.data['summary']}")  # Отладка
    
    def get_stats(self, period: str = "total") -> Dict:
        """
        Получает статистику пользователя за указанный период.
        
        Args:
            period: Период ('day', 'week', 'month', 'total')
            
        Returns:
            Dict: Статистика за период
        """
        try:
            today = get_moscow_time().date()
            
            if period == "day":
                start_date = today
            elif period == "week":
                start_date = today - timedelta(days=7)
            elif period == "month":
                start_date = today - timedelta(days=30)
            else:  # total
                start_date = datetime.min.date()
            
            # Фильтруем события за период
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
                    "tree_growth": 0
                },
                "streak_info": self.data["streaks"].copy(),
                "total_events": 0
            }
            
            # Подсчитываем события за период
            for event_type, events in self.data["events"].items():
                for event in events:
                    event_date = datetime.fromisoformat(event["timestamp"]).date()
                    if event_date >= start_date and event_date <= today:
                        period_stats["events_count"][event_type] += 1
                        period_stats["total_events"] += 1
            
            return period_stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"error": str(e)}


# Удобные функции для использования в других модулях
async def update_stats(user_id: int, event_type: str, event_data: Dict = None) -> bool:
    """
    Обновляет статистику пользователя.
    
    Args:
        user_id: ID пользователя
        event_type: Тип события
        event_data: Дополнительные данные
        
    Returns:
        bool: Успех обновления
    """
    stats = UserStats(user_id)
    return stats.update_stats(event_type, event_data)


async def get_stats(user_id: int, period: str = "total") -> Dict:
    """
    Получает статистику пользователя.
    
    Args:
        user_id: ID пользователя
        period: Период ('day', 'week', 'month', 'total')
        
    Returns:
        Dict: Статистика
    """
    stats = UserStats(user_id)
    return stats.get_stats(period)


async def get_user_stats_summary(user_id: int) -> Dict:
    """
    Получает общую сводку по статистике пользователя.
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Dict: Сводка статистики
    """
    stats = UserStats(user_id)
    
    return {
        "user_id": user_id,
        "total_stats": stats.data["summary"],
        "streak_info": stats.data["streaks"],
        "recent_activity": {
            "today": stats.get_stats("day"),
            "this_week": stats.get_stats("week"),
            "this_month": stats.get_stats("month"),
            "all_time": stats.get_stats("total")
        }
    }