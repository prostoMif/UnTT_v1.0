"""Модуль прогресса дерева осознанности."""
import json
import os
from datetime import datetime, date
from typing import Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


class TreeProgress:
    """
    Класс для отслеживания прогресса дерева осознанности.
    
    Каждый пользователь имеет своё дерево, которое растёт
    при выполнении практик и осознанных действий.
    """
    
    # Константы для уровней роста
    STAGES = [
        {"name": "🌱 Росток", "level": 0, "ascii": """
        .
       .|.
       .|.
      ..|..
      .'|'.
        """},
        {"name": "🌿 Саженец", "level": 1, "ascii": """
         /\\
        /  \\
       /    \\
      /  /\\  \\
     /  /  \\  \\
    /  /    \\  \\
       |    |
       |    |
       |____|
        """},
        {"name": "🌳 Молодое дерево", "level": 2, "ascii": """
           \\   |   /
            \\  |  /
         ------+------
             /|\\
            / | \\
           /  |  \\
          /   |   \\
         /    |    \\
        /     |     \\
       /______|______\\
        """},
        {"name": "🌲 Взрослое дерево", "level": 3, "ascii": """
              \\   |   /
               \\  |  /
            ------+------
               /|\\
              / | \\
             /  |  \\
            /   |   \\
           /    |    \\
          /     |     \\
         /______|______\\
        ~~~~~~~~~~~~~~~~~~
        """},
        {"name": "🌸 Цветущее дерево", "level": 4, "ascii": """
             *   *   *
              \\ | /
           ---(+)---
               /|\\
              / | \\
             /  |  \\
            /   |   \\
           /    |    \\
          /     |     \\
         /______|______\\
        ~~~~~~~~~~~~~~~~~~
        """},
        {"name": "🏆 Дерево мудрости", "level": 5, "ascii": """
         \\|/
        -(*)-
         /|\\
         /|\\
        / | \\
       /  |  \\
      /   |   \\
     /    |    \\
    /_____ _____\\
    ~~~~~~~~~~~~~~
    *** 🎋 🎋 ***
        """}
    ]
    
    def __init__(self, user_id: int, storage_dir: str = "data"):
        """
        Инициализация прогресса дерева пользователя.
        
        Args:
            user_id: ID пользователя Telegram
            storage_dir: Директория для хранения данных
        """
        self.user_id = user_id
        self.storage_dir = storage_dir
        self.storage_file = os.path.join(storage_dir, f"tree_{user_id}.json")
        
        # Данные прогресса
        self.data = {
            "user_id": user_id,
            "level": 0,
            "xp": 0,
            "xp_to_next_level": 10,
            "streak": 0,
            "total_days": 0,
            "growth_days": 0,
            "skip_days": 0,
            "last_action_date": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Создаём директорию для хранения, если не существует
        os.makedirs(storage_dir, exist_ok=True)
        
        # Загружаем существующие данные
        self.load()
    
    def load(self) -> bool:
        """
        Загружает прогресс пользователя из JSON файла.
        
        Returns:
            bool: Успех загрузки
        """
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info(f"Прогресс загружен для user_id: {self.user_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка загрузки прогресса: {e}")
        return False
    
    def save(self) -> bool:
        """
        Сохраняет прогресс пользователя в JSON файл.
        
        Returns:
            bool: Успех сохранения
        """
        try:
            # Обновляем время последнего изменения
            self.data["updated_at"] = datetime.now().isoformat()
            
            # Создаем директорию если не существует
            os.makedirs(self.storage_dir, exist_ok=True)
            
            # Сохраняем данные в JSON файл
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Прогресс сохранён для user_id: {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения прогресса для user_id {self.user_id}: {e}")
            return False
    
    def _check_streak(self) -> bool:
        """
        Проверяет и обновляет серию дней.
        
        Returns:
            bool: True если серия сохранена, False если прервана
        """
        today = date.today()
        last_date_str = self.data.get("last_action_date")
        
        if last_date_str:
            last_date = datetime.fromisoformat(last_date_str).date()
            delta = (today - last_date).days
            
            if delta == 1:
                # Подряд идущий день
                return True
            elif delta == 0:
                # Сегодня уже была активность
                return True
            else:
                # Серия прервана
                self.data["streak"] = 0
        
        return True
    
    def _level_up(self) -> bool:
        """
        Проверяет необходимость повышения уровня.
        
        Returns:
            bool: True если уровень повышен
        """
        if self.data["xp"] >= self.data["xp_to_next_level"]:
            self.data["level"] += 1
            self.data["xp"] = self.data["xp"] - self.data["xp_to_next_level"]
            self.data["xp_to_next_level"] = int(self.data["xp_to_next_level"] * 1.5)
            logger.info(f"user_id {self.user_id} достиг уровня {self.data['level']}")
            return True
        return False
    
    async def grow(self, xp_gain: int = 5) -> dict:
        """
        Рост дерева при успешном выполнении практики.
        
        Args:
            xp_gain: Количество XP за действие (по умолчанию 5)
        
        Returns:
            dict: Результат роста
        """
        result = {
            "success": True,
            "leveled_up": False,
            "old_level": self.data["level"],
            "new_level": self.data["level"],
            "xp_gained": xp_gain,
            "current_xp": self.data["xp"],
            "xp_needed": self.data["xp_to_next_level"],
            "already_grown_today": False  # НОВОЕ: флаг роста сегодня
        }
        
        # Проверяем, не было ли уже роста сегодня
        today = datetime.now().date()
        last_action_date = self.data.get("last_action_date")
        
        if last_action_date:
            last_date = datetime.fromisoformat(last_action_date).date()
            if last_date == today:
                # Уже был рост сегодня, не добавляем день роста
                result["already_grown_today"] = True
                # Но все равно добавляем XP за осознанное действие
                self.data["xp"] += xp_gain
            else:
                # Новый день - полный рост
                self._check_streak()
                self.data["xp"] += xp_gain
                self.data["growth_days"] += 1
                self.data["total_days"] += 1
                self.data["streak"] += 1
        else:
            # Первое действие
            self._check_streak()
            self.data["xp"] += xp_gain
            self.data["growth_days"] += 1
            self.data["total_days"] += 1
            self.data["streak"] += 1
        
        self.data["last_action_date"] = datetime.now().isoformat()
        
        # Проверяем повышение уровня
        if self._level_up():
            result["leveled_up"] = True
            result["new_level"] = self.data["level"]
        
        self.save()
        
        logger.info(f"Дерево выросло для user_id: {self.user_id}")
        return result
    
    
    async def skip_day(self) -> dict:
        """
        День без роста (пропуск практики).
        
        Returns:
            dict: Результат пропуска
        """
        result = {
            "success": True,
            "streak_reset": False,
            "current_streak": self.data["streak"],
            "skip_days": self.data["skip_days"]
        }
        
        today = date.today()
        last_date_str = self.data.get("last_action_date")
        
        if last_date_str:
            last_date = datetime.fromisoformat(last_date_str).date()
            delta = (today - last_date).days
            
            if delta > 1:
                # Серия прервана
                self.data["streak"] = 0
                result["streak_reset"] = True
                result["current_streak"] = 0
        
        self.data["skip_days"] += 1
        self.data["total_days"] += 1
        self.data["last_action_date"] = datetime.now().isoformat()
        
        self.save()
        
        logger.info(f"День пропущен для user_id: {self.user_id}")
        return result
    
    async def snapshot(self) -> dict:
        """
        Возвращает визуализацию текущего состояния дерева.
        
        Returns:
            dict: Данные о текущем состоянии дерева
        """
        level = min(self.data["level"], len(self.STAGES) - 1)
        stage = self.STAGES[level]
        
        next_stage = None
        if level < len(self.STAGES) - 1:
            next_stage = self.STAGES[level + 1]
        
        progress_percent = (self.data["xp"] / self.data["xp_to_next_level"]) * 100
        
        return {
            "user_id": self.user_id,
            "stage": stage["name"],
            "level": self.data["level"],
            "ascii_art": stage["ascii"],
            "xp": self.data["xp"],
            "xp_to_next": self.data["xp_to_next_level"],
            "progress_percent": round(progress_percent, 1),
            "streak": self.data["streak"],
            "growth_days": self.data["growth_days"],
            "total_days": self.data["total_days"],
            "next_stage": next_stage["name"] if next_stage else "Максимальный уровень!",
            "next_stage_level": (level + 1) if next_stage else None
        }
    
    def get_stats(self) -> dict:
        """
        Возвращает полную статистику пользователя.
        
        Returns:
            dict: Статистика прогресса
        """
        return {
            "user_id": self.user_id,
            "level": self.data["level"],
            "xp": self.data["xp"],
            "xp_to_next_level": self.data["xp_to_next_level"],
            "streak": self.data["streak"],
            "total_growth_days": self.data["growth_days"],
            "total_skip_days": self.data["skip_days"],
            "total_days": self.data["total_days"],
            "created_at": self.data["created_at"]
        }
    
    async def reset(self) -> bool:
        """
        Сбрасывает прогресс пользователя.
        
        Returns:
            bool: Успех сброса
        """
        self.data = {
            "user_id": self.user_id,
            "level": 0,
            "xp": 0,
            "xp_to_next_level": 10,
            "streak": 0,
            "total_days": 0,
            "growth_days": 0,
            "skip_days": 0,
            "last_action_date": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.save()
        logger.info(f"Прогресс сброшен для user_id: {self.user_id}")
        return True
    
    async def add_completion(self, xp_gain: int = 5) -> dict:
        """
        Добавляет завершенную практику к прогрессу.
        
        Args:
            xp_gain: Количество XP за практику
            
        Returns:
            dict: Результат обновления прогресса
        """
        try:
            # Используем существующий метод grow
            result = await self.grow(xp_gain)
            
            logger.info(f"Прогресс обновлен для пользователя {self.user_id}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса: {e}")
            return {"success": False, "error": str(e)}
    
    def get_progress_text(self) -> str:
        """
        Возвращает текстовое представление прогресса.
        
        Returns:
            str: Текст с информацией о прогрессе
        """
        try:
            # Получаем снапшот синхронно
            level = min(self.data["level"], len(self.STAGES) - 1)
            stage = self.STAGES[level]
            
            next_stage = None
            if level < len(self.STAGES) - 1:
                next_stage = self.STAGES[level + 1]
            
            progress_percent = (self.data["xp"] / self.data["xp_to_next_level"]) * 100
            
            progress_text = (
                f"🌳 <b>Твоё дерево прогресса</b>\n\n"
                f"📊 <b>Стадия:</b> {stage['name']}\n"
                f"⭐ <b>Уровень:</b> {self.data['level']}\n"
                f"💫 <b>XP:</b> {self.data['xp']}/{self.data['xp_to_next_level']} ({progress_percent:.1f}%)\n"
                f"🔥 <b>Серия:</b> {self.data['streak']} дней\n"
                f"🌱 <b>Дней роста:</b> {self.data['growth_days']}\n"
                f"📅 <b>Всего дней:</b> {self.data['total_days']}\n\n"
            )
            
            if next_stage:
                progress_text += f"<b>Следующая стадия:</b> {next_stage['name']}\n\n"
            else:
                progress_text += "<b>Поздравляем!</b> Достигнут максимальный уровень!\n\n"
            
            progress_text += stage['ascii']
            
            return progress_text
            
        except Exception as e:
            logger.error(f"Ошибка получения текста прогресса: {e}")
            return "🌱 Продолжай практиковаться!\n\nДерево покажет твой прогресс после первых практик."


# Функция для удобного создания экземпляра
async def get_tree_progress(user_id: int) -> TreeProgress:
    """
    Создаёт и возвращает экземпляр TreeProgress.
    
    Args:
        user_id: ID пользователя Telegram
    
    Returns:
        TreeProgress: Экземпляр класса прогресса
    """
    return TreeProgress(user_id)