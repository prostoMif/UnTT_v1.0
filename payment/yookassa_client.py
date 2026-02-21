import os
import asyncio
import yookassa
from yookassa import Configuration, Payment
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Настройка конфигурации ЮKassa
shop_id = os.getenv("YOOKASSA_SHOP_ID")
secret_key = os.getenv("YOOKASSA_SECRET_KEY")

# ДОБАВЛЕНО: Проверка наличия ключей при старте
if not shop_id or not secret_key:
    logger.critical("КРИТИЧЕСКАЯ ОШИБКА: YOOKASSA_SHOP_ID или YOOKASSA_SECRET_KEY не найдены в переменных окружения!")
    # Раскомментируй строку ниже, чтобы бот падал при старте, если ключей нет
    # raise ValueError("Yookassa credentials are missing in environment variables")
else:
    Configuration.account_id = shop_id
    Configuration.secret_key = secret_key

async def create_payment(user_id: int, return_url: str) -> tuple[str | None, str | None]:
    """
    Создает платеж в ЮKassa.
    Возвращает кортеж: (confirmation_url, payment_id)
    """
    if not Configuration.account_id or not Configuration.secret_key:
        logger.error("Попытка создать платеж без настроенных ключей API.")
        return None, None

    try:
        payment_dict = {
            "amount": {
                "value": "149.00",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": f"Подписка UnTT (User ID: {user_id})",
            "metadata": {
                "user_id": str(user_id)
            },
            "test": True # Сюда потом поставим False для боевого режима
        }
        
        payment = await asyncio.to_thread(Payment.create, payment_dict)

        logger.info(f"Платеж создан: {payment.id} для пользователя {user_id}")
        
        url = None
        if payment.confirmation and payment.confirmation.confirmation_url:
            url = payment.confirmation.confirmation_url
            
        return url, payment.id
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        return None, None

def calculate_subscription_end_date(months: int = 1) -> str:
    """Вычисляет дату окончания подписки."""
    return (datetime.now() + timedelta(days=30 * months)).isoformat()