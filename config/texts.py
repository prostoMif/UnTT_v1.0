"""
Тексты бота — все сообщения в одном месте
"""

# --- ГЛАВНОЕ МЕНЮ ---
MENU_NO_SUB = """Сегодня
Осознанных моментов: {count} Сэкономлено: {saved_time}"""

MENU_WITH_SUB = """Сегодня
Осознанных моментов: {count} Сэкономлено: {saved_time}"""

# --- СТАРТ ---
START_NO_SUB = """UnTT
Когда соберёшься открыть TikTok — нажми кнопку."""

START_WITH_SUB = """UnTT
Когда соберёшься открыть TikTok — нажми кнопку."""

# --- QUICK PAUSE ---
QP_START = "Ты собираешься открыть TikTok."
QP_REASON = "Что за этим стоит?"
QP_TIME = "Сколько времени планируешь?"
QP_TIMER = "Таймер: {minutes} мин\n\n"
QP_STOPPED_EARLY = "Вышел на {saved} раньше.\n\n"
QP_DONE = "Готово."
# --- STATS ---
STATS_FREE = """Сегодня: {today_count} моментов  Сэкономлено: {saved_time}

Среднее за неделю: {week_avg}"""

STATS_PREMIUM = """Сегодня: {today_count} моментов  Сэкономлено: {saved_time}

Дней с ботом: {days_count}

Недельный тренд: {week_trend}"""

# --- SOS ---
SOS_START = "Тянет открыть TikTok.\n\nЧто сейчас важнее этого?"
SOS_PRIORITY = """Что сейчас важнее TikTok?

1. Учёба/работа  2. Сон  3. Спорт
4. Друзья/семья  5. Хобби"""
SOS_CONFIRM = "{choice} важнее.\nTikTok подождёт."
SOS_NEED_PREMIUM = "SOS доступен в Premium.\n\n"


# --- PAYWALL ---
PAYLOAD_COUNTDOWN = """10... 9... 8..."""

PAYLOAD_3DAYS = """Ты используешь {days} дней.

Premium:
- Статистика по дням недели
- Тренды и средние
- Безлимитный SOS

149₽/мес   """

PAYLOCK_LIMITED = """Лимит бесплатных дней исчерпан."""

PAYMENT_SECURITY = """Безопасность платежа:
- Данные карты не хранятся ботом
- Платеж через ЮKassa
- Без автосписания

После оплаты нажмите "Проверить оплату"."""


# --- TRIAL ---
TRIAL_MESSAGE = "Первые 3 дня — полный доступ. Дальше решишь сам."

# --- NIGHT MODE ---
NIGHT_MODE = """Ночь. Лимит: 10 минут."""

# --- CANCEL ---
CANCEL_TEXT = """Отмена"""

# --- OTHER ---
HELP_TEXT = """Справка по боту

/start — Главное меню
/cancel — Отмена
/tariffs — Тарифы
/help — Справка

Поддержка: @prosto_m1f"""

TARIFFS = """149₽/мес
Без автосписания
Отмена в любой момент"""

# --- BUTTONS ---
BTN_GO_TIKTOK = "Иду в TikTok"
BTN_SOS = "SOS"
BTN_STATS = "Статистика"
BTN_SUB = "Подписка"
BTN_CANCEL = "Отмена"
BTN_STOP = "Стоп"
BTN_PAY = "Включить"

# --- УПРАВЛЕНИЕ ПОДПИСКОЙ ---
MANAGE_SUB_ACTIVE = "Подписка активна до: {date}\n\n[ Продлить ] [ Назад ]"
MANAGE_SUB_INACTIVE = "Нет активной подписки.\n\n[ Купить 149₽ ]"


EXTENDED_MENU = """UnTT
Добро пожаловать!

Осознанных моментов сегодня: {count}
Сэкономлено времени: {saved_time}"""
