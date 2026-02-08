"""Модуль прогресса дерева осознанности (Тихая версия)."""
import json
import os
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class TreeProgress:
    """
    Класс для отслеживания прогресса дерева.
    Логика основана на количестве осознанных дней, а не XP.
    """
    
    def __init__(self, user_id: int, storage_dir: str = "data"):
        self.user_id = user_id
        self.storage_dir = storage_dir
        self.storage_file = os.path.join(storage_dir, f"tree_{user_id}.json")
        
        # Структура данных упрощена
        self.data = {
            "user_id": user_id,
            "total_days": 0,       # Всего осознанных дней
            "current_streak": 0,   # Текущая серия дней
            "last_active_date": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        os.makedirs(storage_dir, exist_ok=True)
        self.load()
    
    def load(self) -> bool:
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                return True
        except Exception as e:
            logger.error(f"Ошибка загрузки прогресса: {e}")
        return False
    
    def save(self) -> bool:
        try:
            self.data["updated_at"] = datetime.now().isoformat()
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения прогресса: {e}")
            return False

    def get_stage_name(self) -> str:
        """Возвращает название стадии на основе общего количества дней."""
        days = self.data.get("total_days", 0)
        
        if days >= 30:
            return "Полное дерево"
        elif days >= 15:
            return "Дерево с ветвями"
        elif days >= 7:
            return "Молодое дерево"
        elif days >= 3:
            return "Росток"
        elif days >= 1:
            return "Семя"
        else:
            return "Семя в земле"
            
    def get_stage_description(self) -> str:
        """Возвращает описание стадии."""
        days = self.data.get("total_days", 0)
        
        if days >= 30:
            return "Тридцать дней. Дерево сформировалось."
        elif days >= 15:
            return "Пятнадцать осознанных дней. Появились ветви."
        elif days >= 7:
            return "Семь дней подряд. Ствол окреп."
        elif days >= 3:
            return "Росток пробился. Три дня выбора."
        elif days >= 1:
            return "Семя в земле. Первый осознанный день."
        else:
            return "Пока пусто."

    async def add_day(self) -> dict:
        """
        Добавляет один осознанный день.
        Возвращает словарь с результатом (изменилась ли стадия).
        """
        result = {
            "success": True,
            "already_grown_today": False,
            "stage_changed": False,
            "new_stage": None,
            "total_days": self.data["total_days"]
        }
        
        today = date.today()
        last_date_str = self.data.get("last_active_date")
        
        # Проверяем, был ли уже рост сегодня
        if last_date_str:
            last_date = datetime.fromisoformat(last_date_str).date()
            if last_date == today:
                result["already_grown_today"] = True
                return result
        
        old_stage = self.get_stage_name()
        
        # Обновляем счетчики
        self.data["total_days"] += 1
        
        # Обновляем серию
        if last_date_str:
            last_date = datetime.fromisoformat(last_date_str).date()
            delta = (today - last_date).days
            if delta == 1:
                self.data["current_streak"] += 1
            else:
                self.data["current_streak"] = 1
        else:
            self.data["current_streak"] = 1
            
        self.data["last_active_date"] = today.isoformat()
        self.save()
        
        new_stage = self.get_stage_name()
        
        if old_stage != new_stage:
            result["stage_changed"] = True
            result["new_stage"] = new_stage
            
        result["total_days"] = self.data["total_days"]
        return result

    # Свойства для удобства обращения из bot.py
    @property
    def total_days(self):
        return self.data.get("total_days", 0)
    
    @property
    def streak(self):
        return self.data.get("current_streak", 0)
    
    @property
    def level(self): # Для совместимости со старыми вызовами, если останутся
        return self.total_days