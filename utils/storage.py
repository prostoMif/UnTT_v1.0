"""Модуль для сохранения и загрузки данных пользователей в JSON."""
import json
import os
from typing import Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Директория для хранения данных
STORAGE_DIR = "data"
USER_DATA_FILE = os.path.join(STORAGE_DIR, "users.json")


def _ensure_storage_dir() -> None:
    """Создаёт директорию для хранения, если её нет."""
    os.makedirs(STORAGE_DIR, exist_ok=True)


def _get_user_storage_path(user_id: int) -> str:
    """
    Возвращает путь к файлу данных пользователя.
    
    Args:
        user_id: ID пользователя
    
    Returns:
        str: Путь к файлу
    """
    return os.path.join(STORAGE_DIR, f"user_{user_id}.json")


def _load_all_users() -> dict:
    """
    Загружает все данные пользователей из общего файла.
    
    Returns:
        dict: Словарь с данными всех пользователей
    """
    _ensure_storage_dir()
    
    if not os.path.exists(USER_DATA_FILE):
        return {}
    
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки всех пользователей: {e}")
        return {}


def _save_all_users(users_data: dict) -> bool:
    """
    Сохраняет данные всех пользователей в общий файл.
    
    Args:
        users_data: Словарь с данными пользователей
    
    Returns:
        bool: Успех операции
    """
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения всех пользователей: {e}")
        return False


async def save_user_data(data: dict, storage_key: str = "users_data") -> bool:
    """Сохранение данных без создания моделей."""
    try:
        # Простое сохранение словаря, без BaseModel
        with open(f"{STORAGE_DIR}/{storage_key}.json", "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")
        return False

def load_user_data(storage_key: str = "users_data") -> dict:
    """Загрузка данных без создания моделей."""
    try:
        with open(f"{STORAGE_DIR}/{storage_key}.json", "r", encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")
        return {}


async def get_all_user_data(user_id: int) -> Optional[dict]:
    """
    Загружает все данные пользователя.
    
    Args:
        user_id: ID пользователя Telegram
    
    Returns:
        dict или None: Все данные пользователя
    """
    try:
        all_users = _load_all_users()
        user_str = str(user_id)
        
        if user_str in all_users:
            logger.info(f"Все данные загружены для user_id: {user_id}")
            return all_users[user_str]
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка загрузки всех данных для user_id {user_id}: {e}")
        return None


async def delete_user_data(user_id: int, key: str = None) -> bool:
    """
    Удаляет данные пользователя.
    
    Args:
        user_id: ID пользователя Telegram
        key: Ключ категории данных (если None — удаляет все данные пользователя)
    
    Returns:
        bool: Успех операции
    """
    try:
        all_users = _load_all_users()
        user_str = str(user_id)
        
        if user_str not in all_users:
            return True
        
        if key is None:
            # Удаляем всё
            del all_users[user_str]
            logger.info(f"Все данные удалены для user_id: {user_id}")
        else:
            # Удаляем конкретный ключ
            if key in all_users[user_str]:
                del all_users[user_str][key]
                logger.info(f"Данные '{key}' удалены для user_id: {user_id}")
        
        return _save_all_users(all_users)
        
    except Exception as e:
        logger.error(f"Ошибка удаления данных для user_id {user_id}: {e}")
        return False


async def update_user_data(user_id: int, key: str, updates: dict) -> bool:
    """
    Обновляет часть данных пользователя.
    
    Args:
        user_id: ID пользователя Telegram
        key: Ключ категории данных
        updates: Словарь с обновлениями
    
    Returns:
        bool: Успех операции
    """
    try:
        # Загружаем текущие данные
        current_data = await load_user_data(user_id, key) or {}
        
        # Обновляем
        current_data.update(updates)
        
        # Сохраняем
        return await save_user_data(user_id, current_data, key)
        
    except Exception as e:
        logger.error(f"Ошибка обновления данных для user_id {user_id}: {e}")
        return False


def get_storage_stats() -> dict:
    """
    Возвращает статистику хранилища.
    
    Returns:
        dict: Статистика
    """
    _ensure_storage_dir()
    
    stats = {
        "storage_dir": STORAGE_DIR,
        "total_users": 0,
        "files": []
    }
    
    try:
        # Считаем пользователей
        all_users = _load_all_users()
        stats["total_users"] = len(all_users)
        
        # Список файлов в директории
        if os.path.exists(STORAGE_DIR):
            files = os.listdir(STORAGE_DIR)
            stats["files"] = files
            stats["total_files"] = len(files)
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
    
    return stats


async def user_exists(user_id: int) -> bool:
    """
    Проверяет, существуют ли данные пользователя.
    
    Args:
        user_id: ID пользователя Telegram
    
    Returns:
        bool: Существует ли пользователь
    """
    all_users = _load_all_users()
    return str(user_id) in all_users
async def save_user_profile(user_id: int, profile: dict) -> bool:
    """Сохраняет профиль пользователя."""
    return await save_user_data(user_id, profile, "profile")

async def load_user_profile(user_id: int) -> Optional[dict]:
    """Загружает профиль пользователя."""
    return await load_user_data(user_id, "profile")