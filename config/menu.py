"""Клавиатуры бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- КНОПКИ ---
BTN_GO_TIKTOK = "Иду в TikTok"
BTN_SOS = "SOS"
BTN_STATS = "Статистика"
BTN_SUB = "Подписка"
BTN_CANCEL = "Отмена"
BTN_STOP = "Стоп"


# --- МЕНЮ БЕЗ ПОДПИСКИ ---
def menu_no_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
        ],
        [InlineKeyboardButton(text=BTN_SUB, callback_data="subscribe")],
    ])


# --- МЕНЮ С ПОДПИСКОЙ ---
def menu_with_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text=BTN_SOS, callback_data="sos"),
            InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
        ],
    ])


# --- СТАРТОВОЕ МЕНЮ БЕЗ ПОДПИСКИ ---
def menu_start_no_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
            InlineKeyboardButton(text=BTN_SUB, callback_data="subscribe"),
        ]
    ])


# --- СТАРТОВОЕ МЕНЮ С ПОДПИСКОЙ ---
def menu_start_with_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text=BTN_SOS, callback_data="sos"),
            InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
        ]
    ])


# --- QUICK PAUSE ---
def qp_reason_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Привычка", callback_data="qp_reason_habit"),
            InlineKeyboardButton(text="Усталость", callback_data="qp_reason_fatigue"),
        ],
        [
            InlineKeyboardButton(text="Отвлечься", callback_data="qp_reason_distraction"),
            InlineKeyboardButton(text="Интерес", callback_data="qp_reason_interest"),
        ],
    ])


def qp_time_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 мин", callback_data="qp_time_5"),
            InlineKeyboardButton(text="15 мин", callback_data="qp_time_15"),
            InlineKeyboardButton(text="30 мин", callback_data="qp_time_30"),
        ],
    ])


def qp_timer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BTN_STOP, callback_data="qp_stop"),
            InlineKeyboardButton(text=BTN_SOS, callback_data="sos")
        ]
    ])


# --- SOS (премиум) ---
def sos_priority_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1. Учёба/работа", callback_data="sos_prio_work"),
            InlineKeyboardButton(text="2. Сон", callback_data="sos_prio_sleep"),
        ],
        [
            InlineKeyboardButton(text="3. Спорт", callback_data="sos_prio_sport"),
            InlineKeyboardButton(text="4. Друзья/семья", callback_data="sos_prio_people"),
        ],
        [
            InlineKeyboardButton(text="5. Хобби", callback_data="sos_prio_hobby"),
        ],
    ])


def sos_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Оставить закрытым", callback_data="sos_close"),
            InlineKeyboardButton(text="Открыть всё равно", callback_data="sos_open"),
        ]
    ])


# --- ОПЛАТА ---
def paywall_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Включить за 149₽", callback_data="pay_unlock")],
    ])


def stats_keyboard(is_premium: bool) -> InlineKeyboardMarkup:
    """Клавиатура статистики - разная для премиума"""
    if is_premium:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
            [
                InlineKeyboardButton(text=BTN_SOS, callback_data="sos"),
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_menu"),  # Заменили на "Назад"
            ],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
            [
                InlineKeyboardButton(text=BTN_SUB, callback_data="subscribe"),
                InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_menu"),
            ]

        ])

"""Клавиатуры бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- КНОПКИ ---
BTN_GO_TIKTOK = "Иду в TikTok"
BTN_SOS = "SOS"
BTN_STATS = "Статистика"
BTN_SUB = "Подписка"
BTN_CANCEL = "Отмена"
BTN_STOP = "Стоп"
BTN_BACK = "Назад"


# --- ГЛАВНОЕ МЕНЮ ---
def menu_no_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [InlineKeyboardButton(text=BTN_STATS, callback_data="stats")],
        [InlineKeyboardButton(text=BTN_SUB, callback_data="subscribe")],
    ])


def menu_with_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text=BTN_SOS, callback_data="sos"),
            InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
        ],
    ])


def menu_start_no_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
            InlineKeyboardButton(text=BTN_SUB, callback_data="subscribe"),
        ]
    ])


def menu_start_with_sub() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
        [
            InlineKeyboardButton(text=BTN_SOS, callback_data="sos"),
            InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
        ]
    ])


# --- QUICK PAUSE ---
def qp_reason_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Привычка", callback_data="qp_reason_habit"),
            InlineKeyboardButton(text="Усталость", callback_data="qp_reason_fatigue"),
        ],
        [
            InlineKeyboardButton(text="Отвлечься", callback_data="qp_reason_distraction"),
            InlineKeyboardButton(text="Интерес", callback_data="qp_reason_interest"),
        ],
    ])


def qp_time_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="5 мин", callback_data="qp_time_5"),
            InlineKeyboardButton(text="15 мин", callback_data="qp_time_15"),
            InlineKeyboardButton(text="30 мин", callback_data="qp_time_30"),
        ],
    ])


def qp_timer_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=BTN_STOP, callback_data="qp_stop"),
            InlineKeyboardButton(text=BTN_SOS, callback_data="sos")
        ]
    ])


# --- SOS ---
def sos_priority_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1. Учёба/работа", callback_data="sos_prio_work"),
            InlineKeyboardButton(text="2. Сон", callback_data="sos_prio_sleep"),
        ],
        [
            InlineKeyboardButton(text="3. Спорт", callback_data="sos_prio_sport"),
            InlineKeyboardButton(text="4. Друзья/семья", callback_data="sos_prio_people"),
        ],
        [
            InlineKeyboardButton(text="5. Хобби", callback_data="sos_prio_hobby"),
        ],
    ])


def sos_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Оставить закрытым", callback_data="sos_act_close"),
            InlineKeyboardButton(text="Открыть всё равно", callback_data="sos_act_open"),
        ]
    ])


# --- ОПЛАТА ---
def paywall_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Включить за 149₽", callback_data="pay_unlock")],
    ])


def payment_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить 149₽", url=url)],
        [InlineKeyboardButton(text="Проверить оплату", callback_data="check_payment_status")]
    ])


def manage_sub_keyboard(is_active: bool, is_premium: bool = False) -> InlineKeyboardMarkup:
    if is_active:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Продлить +30 дней", callback_data="pay_unlock")],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_menu")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Купить 149₽", callback_data="pay_unlock")],
            [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_menu")]
        ])


# --- STATS ---
def stats_keyboard(is_premium: bool) -> InlineKeyboardMarkup:
    if is_premium:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
            [
                InlineKeyboardButton(text=BTN_SOS, callback_data="sos"),
                InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
            ],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=BTN_GO_TIKTOK, callback_data="go_tiktok")],
            [
                InlineKeyboardButton(text=BTN_STATS, callback_data="stats"),
                InlineKeyboardButton(text=BTN_SUB, callback_data="subscribe"),
            ],
        ])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_BACK, callback_data="back_to_menu")]
    ])