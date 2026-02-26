"""
Тексты бота — все сообщения в одном месте
"""

# --- ГЛАВНОЕ МЕНЮ ---
MENU_NO_SUB = """Сегодня
Осознанных моментов: {count} Сэкономлено: {saved_time}

[ Иду в TikTok ] [ SOS ] [ Статистика ] [ Подписка ]"""

MENU_WITH_SUB = """Сегодня
Осознанных моментов: {count} Сэкономлено: {saved_time}

[ Иду в TikTok ] [ SOS ] [ Статистика ]"""

# --- СТАРТ ---
START_NO_SUB = """UnTT
Когда соберёшься открыть TikTok — нажми кнопку.

[ Иду в TikTok ] [ Статистика ] [ Подписка ]"""

START_WITH_SUB = """UnTT
Когда соберёшься открыть TikTok — нажми кнопку.

[ Иду в TikTok ] [ SOS ] [ Статистика ]"""

# --- QUICK PAUSE ---
QP_REASON = """Что за этим стоит?"""

QP_TIME = """Сколько времени планируешь?"""

QP_TIMER = """Таймер: {minutes} мин

[ Стоп ] [ SOS ]"""

QP_STOPPED_EARLY = """Вышел на {saved} раньше.

[ Статистика ] [ SOS ]"""

QP_DONE = """Готово."""

# --- STATS ---
STATS_FREE = """Сегодня: {today_count} моментов  Сэкономлено: {saved_time}

Среднее за неделю: {week_avg}"""

STATS_PREMIUM = """Сегодня: {today_count} моментов  Сэкономлено: {saved_time}

Дней с ботом: {days_count}

Недельный тренд: {week_trend}"""

# --- SOS ---
SOS_PRIORITY = """Что сейчас важнее TikTok?

1. Учёба/работа  2. Сон  3. Спорт
4. Друзья/семья  5. Хобби"""

SOS_CONFIRM = """{choice} важнее.
TikTok подождёт."""

# --- PAYWALL ---
PAYLOAD_COUNTDOWN = """10... 9... 8..."""

PAYLOAD_3DAYS = """Ты используешь {days} дней.

Premium:
- Статистика по дням недели
- Тренды и средние
- Безлимитный SOS

149₽/мес   [ Включить ]"""

PAYLOCK_LIMITED = """Лимит бесплатных дней исчерпан.

[ Подписка 149₽ ]"""

# --- NIGHT MODE ---
NIGHT_MODE = """Ночь. Лимит: 10 минут."""

# --- CANCEL ---
CANCEL = """Отмена"""

# --- OTHER ---
HELP_TEXT = """UnTT — бот для осознанного использования TikTok

/start — Главное меню
/cancel — Отмена
/help — Справка"""

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