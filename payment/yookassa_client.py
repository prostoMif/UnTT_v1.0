import os
import yookassa
from yookassa import Configuration, Payment
import logging
from datetime import datetime, timedelta

# Настройка конфигурации ЮKassa
Configuration.account_id = os.getenv("YOOKASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOOKASSA_SECRET_KEY")

logger = logging.getLogger(__name__)

async def create_payment(user_id: int, return_url: str) -> str | None:
    """
    Создает платеж в ЮKassa и возвращает URL для оплаты.
    """
    try:
        payment = Payment.create({
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
            "test": True
        })

        logger.info(f"Платеж создан: {payment.id} для пользователя {user_id}")
        # Получаем confirmation_url
        if payment.confirmation and payment.confirmation.confirmation_url:
            return payment.confirmation.confirmation_url
        return None
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        return None

def calculate_subscription_end_date(months: int = 1) -> str:
    """Вычисляет дату окончания подписки."""
    return (datetime.now() + timedelta(days=30 * months)).isoformat()