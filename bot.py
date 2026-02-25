import logging
import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ==================== CONFIG ====================
BOT_TOKEN = "8760557568:AAFhxPzGyMbSuN7nSoYo1ZNJab0rxNwUJDk"
ADMIN_IDS = [174415647, 6765669825]
MANAGER = "@liiina_newq"

# ==================== STATES ====================
WAITING_NFT_LINK = 1
WAITING_PAYMENT_METHOD = 2
WAITING_REQUISITES = 3
WAITING_PAYMENT_CONFIRMATION = 4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nft_bot")

# ==================== ВАЛЮТЫ ПОД КАЖДЫЙ МЕТОД ====================
PAYMENT_CURRENCY = [
    ("USDT", "USDT"),   # 0  CryptoBot
    ("USDT", "USDT"),   # 1  TRC20
    ("TON",  "TON"),    # 2  Tonkeeper
    ("UAH",  "грн"),    # 3  Украина
    ("RUB",  "руб"),    # 4  Россия
    ("USD",  "$"),      # 5  США
    ("BYN",  "руб"),    # 6  Беларусь
    ("KZT",  "тг"),     # 7  Казахстан
    ("UZS",  "сум"),    # 8  Узбекистан
    ("TRY",  "₺"),      # 9  Турция
    ("AZN",  "₼"),      # 10 Азербайджан
]

# Курсы к USD (февраль 2026)
RATES = {
    "USDT": 1,
    "TON":  5.26,    # ~5.26 TON за $1 (исправлено: теперь 1 TON = $0.19)
    "UAH":  41,
    "RUB":  90,
    "USD":  1,
    "BYN":  3.2,
    "KZT":  480,
    "UZS":  12800,
    "TRY":  32,
    "AZN":  1.7,
}

# ==================== NFT ЦЕНЫ (реальный рынок февраль 2026, floor price в USD) ====================
# ФИКС: Убраны алиасы, теперь точное соответствие
NFT_PRICES_USD = {
    # Топовые коллекции (голубые фишки)
    "plushpepe":   7500,   # Plush Pepe — фиксированная цена вместо рандома
    "dragon":      300,    # Dragon
    "crystalball": 150,    # Crystal Ball
    "diamondring": 250,    # Diamond Ring
    "heart":       100,    # Heart-themed
    "star":        80,     # Star-themed
    "lootbag":     110,    # Loot Bag
    "goldpepe":    500,    # Gold Pepe
    
    # Базовый сегмент (массовые коллекции)
    "cat":         25,     # Cat-themed
    "bear":        20,     # Bear-themed
    "dog":         15,     # Dog-themed
    "duck":        12,     # Duck-themed
    "bunny":       15,     # Jelly Bunny
    "santahat":    10,     # Santa Hat
    "cake":        8,      # Homemade Cake
    "wine":        8,      # Spiced Wine
    "hat":         10,     # Hat-themed
    "gift":        10,     # Gift-themed
}

# Алиасы для поиска (маппинг разных названий к ключам)
NFT_ALIASES = {
    "plush": "plushpepe",
    "pepe": "plushpepe",
    "crystal": "crystalball",
    "gem": "crystalball",
    "diamond": "diamondring",
    "loot": "lootbag",
    "gold": "goldpepe",
    "jelly": "bunny",
}

def estimate_price_usd(nft_name):
    """Оцениваем NFT по названию. Точное соответствие, без рандома."""
    name_lower = nft_name.lower().replace("-", "").replace("_", "")
    
    # Сначала проверяем точное совпадение с ключами
    for key, price in NFT_PRICES_USD.items():
        if key in name_lower:
            our_price = round(price * 1.30, 2)  # +30%
            return price, our_price
    
    # Проверяем по алиасам
    for alias, key in NFT_ALIASES.items():
        if alias in name_lower:
            price = NFT_PRICES_USD[key]
            our_price = round(price * 1.30, 2)
            return price, our_price
    
    # Неизвестный NFT — базовая цена 15 USDT
    base = 15.00
    our_price = round(base * 1.30, 2)
    return base, our_price

def convert_price(usd_amount, currency_code):
    rate = RATES.get(currency_code, 1)
    if currency_code in ("USDT", "USD"):
        return round(usd_amount, 2)
    if currency_code == "TON":
        return round(usd_amount / 0.19, 2)  # 1 TON = $0.19
    return round(usd_amount * rate, 0)

def format_price(amount, pay_idx):
    currency_code, currency_label = PAYMENT_CURRENCY[pay_idx]
    converted = convert_price(amount, currency_code)
    if currency_code in ("USDT", "USD"):
        return f"${converted} {currency_code}"
    elif currency_code == "TON":
        return f"{converted} TON"
    else:
        return f"{int(converted)} {currency_label}"

def is_nft_link(text):
    return bool(re.match(r'https?://t\.me/nft/[\w\-]+', text.strip()))

def get_lang(context):
    return context.user_data.get("lang", "ru")

# ==================== TEXTS ====================

WELCOME_RU = (
    "🎁 *Добро пожаловать в Автоматическую Скупку NFT-подарков в Telegram!*\n\n"
    "Мы — профессиональный сервис по выкупу NFT-подарков выше рыночной стоимости.\n"
    "Наш бот автоматически оценивает ваш NFT по характеристикам: модель, фон, узор — "
    "и предлагает вам цену *на 30% выше рынка* 📈\n\n"
    "Тысячи успешных сделок. Быстрые выплаты. Полная безопасность.\n\n"
    "Выберите действие ниже 👇"
)

WELCOME_EN = (
    "🎁 *Welcome to the Automatic NFT Gift Buyout service in Telegram!*\n\n"
    "We are a professional service that purchases NFT gifts above market value.\n"
    "Our bot automatically evaluates your NFT by characteristics: model, background, pattern — "
    "and offers you a price *30% above the market* 📈\n\n"
    "Thousands of successful deals. Fast payouts. Full security.\n\n"
    "Choose an action below 👇"
)

# ==================== KEYBOARDS ====================

def lang_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

def main_menu_keyboard(lang):
    if lang == "ru":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Продать NFT", callback_data="sell")],
            [InlineKeyboardButton("⚙️ Как проводится сделка?", callback_data="how_deal")],
            [InlineKeyboardButton("🆘 Поддержка", callback_data="support")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Sell NFT", callback_data="sell")],
            [InlineKeyboardButton("⚙️ How is the deal conducted?", callback_data="how_deal")],
            [InlineKeyboardButton("🆘 Support", callback_data="support")],
        ])

def payment_keyboard(lang):
    methods = PAYMENT_METHODS_RU if lang == "ru" else PAYMENT_METHODS_EN
    buttons = []
    for i, method in enumerate(methods):
        buttons.append([InlineKeyboardButton(method, callback_data=f"pay_{i}")])
    buttons.append([InlineKeyboardButton(
        "◀️ Назад" if lang == "ru" else "◀️ Back", callback_data="back_main"
    )])
    return InlineKeyboardMarkup(buttons)

def confirm_keyboard(lang):
    yes = "✅ Да, согласен" if lang == "ru" else "✅ Yes, I agree"
    no = "❌ Нет" if lang == "ru" else "❌ No"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(yes, callback_data="confirm_yes")],
        [InlineKeyboardButton(no, callback_data="confirm_no")],
    ])

def deal_keyboard(lang):
    """Клавиатура для этапа сделки с кнопкой оплаты"""
    if lang == "ru":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Я оплатил", callback_data="paid")],
            [InlineKeyboardButton("⛓️ В меню", callback_data="back_main")],
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 I paid", callback_data="paid")],
            [InlineKeyboardButton("⛓️ Main menu", callback_data="back_main")],
        ])

def back_keyboard(lang):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "◀️ Главное меню" if lang == "ru" else "◀️ Main menu",
            callback_data="back_main"
        )
    ]])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🖼 Изменить баннер", callback_data="admin_banner")],
        [InlineKeyboardButton("💬 Все сделки", callback_data="admin_deals")],
        [InlineKeyboardButton("🚫 Заблокировать юзера", callback_data="admin_ban")],
    ])

# ==================== TEXTS (продолжение) ====================

HOW_DEAL_RU = (
    "🤝 *Как проводится сделка?*\n\n"
    "1. Вы присылаете ссылку на NFT-подарок\n"
    "2. Бот считает рыночную цену по параметрам: модель, фон, узор\n"
    "3. Вы выбираете способ оплаты\n"
    "4. Бот озвучивает свою сумму в вашей валюте\n\n"
    "_Пример:_ Я предлагаю вам за ваш NFT `https://t.me/nft/PlushPepe-2133` — *520 грн*\n"
    "Если согласны — нажмите *Да*, если нет — *Нет*\n\n"
    "5. При согласии — отправьте NFT менеджеру @liiina_newq\n"
    "6. Менеджер проверяет подарок и переводит оплату на ваши реквизиты\n"
    "7. После получения оплаты нажмите *💸 Я оплатил*\n\n"
    "⚡ Среднее время сделки: 5–15 минут"
)

HOW_DEAL_EN = (
    "🤝 *How is the deal conducted?*\n\n"
    "1. You send the NFT gift link\n"
    "2. The bot calculates market price by: model, background, pattern\n"
    "3. You choose a payment method\n"
    "4. The bot announces its offer in your currency\n\n"
    "_Example:_ I offer you for your NFT `https://t.me/nft/PlushPepe-2133` — *$8,983 USDT*\n"
    "If you agree — press *Yes*, if not — *No*\n\n"
    "5. If agreed — send the NFT to @liiina_newq\n"
    "6. The manager verifies the gift and transfers payment to your details\n"
    "7. After receiving payment, press *💸 I paid*\n\n"
    "⚡ Average deal time: 5–15 minutes"
)

SELL_ASK_LINK_RU = (
    "🔗 *Отправьте ссылку на ваш NFT-подарок*\n\n"
    "Формат: `https://t.me/nft/НазваниеНФТ-Номер`\n\n"
    "⚠️ Принимаются только NFT-подарки Telegram. "
    "Убедитесь что ссылка ведёт именно на NFT, а не на что-то другое."
)

SELL_ASK_LINK_EN = (
    "🔗 *Send the link to your NFT gift*\n\n"
    "Format: `https://t.me/nft/NFTName-Number`\n\n"
    "⚠️ Only Telegram NFT gifts are accepted. "
    "Make sure the link leads to an NFT, not something else."
)

PAYMENT_METHODS_RU = [
    "💎 CryptoBot (USDT)",
    "🔷 TRC20 (USDT)",
    "💎 Tonkeeper (TON)",
    "🇺🇦 Карта — Украина (UAH)",
    "🇷🇺 Карта — Россия (RUB)",
    "🇺🇸 Карта — США (USD)",
    "🇧🇾 Карта — Беларусь (BYN)",
    "🇰🇿 Карта — Казахстан (KZT)",
    "🇺🇿 Карта — Узбекистан (UZS)",
    "🇹🇷 Карта — Турция (TRY)",
    "🇦🇿 Карта — Азербайджан (AZN)",
]

PAYMENT_METHODS_EN = [
    "💎 CryptoBot (USDT)",
    "🔷 TRC20 (USDT)",
    "💎 Tonkeeper (TON)",
    "🇺🇦 Card — Ukraine (UAH)",
    "🇷🇺 Card — Russia (RUB)",
    "🇺🇸 Card — USA (USD)",
    "🇧🇾 Card — Belarus (BYN)",
    "🇰🇿 Card — Kazakhstan (KZT)",
    "🇺🇿 Card — Uzbekistan (UZS)",
    "🇹🇷 Card — Turkey (TRY)",
    "🇦🇿 Card — Azerbaijan (AZN)",
]

# ==================== HELPER ====================

async def safe_edit(query, text, keyboard=None):
    try:
        if keyboard:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await query.edit_message_text(text, parse_mode="Markdown")
    except Exception:
        try:
            if keyboard:
                await query.edit_message_caption(caption=text, parse_mode="Markdown", reply_markup=keyboard)
            else:
                await query.edit_message_caption(caption=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"safe_edit failed: {e}")

# ==================== HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🌍 Выберите язык / Choose your language:",
        reply_markup=lang_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = get_lang(context)

    if data == "lang_ru":
        context.user_data["lang"] = "ru"
        await safe_edit(query, WELCOME_RU, main_menu_keyboard("ru"))
        return

    if data == "lang_en":
        context.user_data["lang"] = "en"
        await safe_edit(query, WELCOME_EN, main_menu_keyboard("en"))
        return

    if data == "back_main":
        text = WELCOME_RU if lang == "ru" else WELCOME_EN
        await safe_edit(query, text, main_menu_keyboard(lang))
        context.user_data.clear()
        return

    if data == "how_deal":
        text = HOW_DEAL_RU if lang == "ru" else HOW_DEAL_EN
        await safe_edit(query, text, back_keyboard(lang))
        return

    if data == "support":
        if lang == "ru":
            text = f"🆘 *Поддержка*\n\nПо всем вопросам обращайтесь к менеджеру: {MANAGER}\n\nМы работаем 24/7 и ответим вам в течение нескольких минут!"
        else:
            text = f"🆘 *Support*\n\nFor all questions, contact the manager: {MANAGER}\n\nWe work 24/7 and will reply within minutes!"
        await safe_edit(query, text, back_keyboard(lang))
        return

    if data == "sell":
        context.user_data["state"] = WAITING_NFT_LINK
        text = SELL_ASK_LINK_RU if lang == "ru" else SELL_ASK_LINK_EN
        await safe_edit(query, text, back_keyboard(lang))
        return

    if data.startswith("pay_"):
        idx = int(data.split("_")[1])
        methods = PAYMENT_METHODS_RU if lang == "ru" else PAYMENT_METHODS_EN
        method = methods[idx]
        context.user_data["payment"] = method
        context.user_data["pay_idx"] = idx
        context.user_data["state"] = WAITING_REQUISITES

        nft_link = context.user_data.get("nft_link", "https://t.me/nft/PlushPepe-2133")
        base_usd = context.user_data.get("base_price", 15)
        our_usd = context.user_data.get("our_price", 19.5)

        price_str = format_price(our_usd, idx)
        market_str = format_price(base_usd, idx)

        if lang == "ru":
            text = (
                f"💳 *Способ оплаты:* {method}\n\n"
                f"📎 *Ваш NFT:* `{nft_link}`\n"
                f"🏷 Рыночная стоимость: ~{market_str}\n"
                f"💰 *Наше предложение: {price_str} (+30%)*\n\n"
                "📝 Введите ваши реквизиты для получения оплаты:"
            )
        else:
            text = (
                f"💳 *Payment method:* {method}\n\n"
                f"📎 *Your NFT:* `{nft_link}`\n"
                f"🏷 Market value: ~{market_str}\n"
                f"💰 *Our offer: {price_str} (+30%)*\n\n"
                "📝 Enter your payment details:"
            )
        await safe_edit(query, text, back_keyboard(lang))
        return

    if data == "confirm_yes":
        nft_link = context.user_data.get("nft_link", "")
        our_usd = context.user_data.get("our_price", 0)
        pay_idx = context.user_data.get("pay_idx", 0)
        price_str = format_price(our_usd, pay_idx)
        payment = context.user_data.get("payment", "")
        requisites = context.user_data.get("requisites", "")

        # Отправляем подтверждение с кнопкой оплаты
        if lang == "ru":
            text = (
                "✅ *Сделка подтверждена!*\n\n"
                "📋 *Детали сделки:*\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💵 Сумма: *{price_str}*\n"
                f"💳 Способ: {payment}\n"
                f"📝 Реквизиты: `{requisites}`\n\n"
                f"📤 *Отправьте NFT менеджеру* {MANAGER}\n\n"
                "После отправки NFT и получения оплаты нажмите кнопку ниже 👇"
            )
        else:
            text = (
                "✅ *Deal confirmed!*\n\n"
                "📋 *Deal details:*\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💵 Amount: *{price_str}*\n"
                f"💳 Method: {payment}\n"
                f"📝 Details: `{requisites}`\n\n"
                f"📤 *Send the NFT to manager* {MANAGER}\n\n"
                "After sending the NFT and receiving payment, press the button below 👇"
            )
        
        await safe_edit(query, text, deal_keyboard(lang))
        context.user_data["state"] = WAITING_PAYMENT_CONFIRMATION

        # Уведомление админов
        user = query.from_user
        admin_text = (
            "🔔 *Новая сделка!*\n"
            f"👤 Пользователь: @{user.username or user.id} ({user.id})\n"
            f"📎 NFT: {nft_link}\n"
            f"💵 Сумма: {price_str}\n"
            f"💳 Метод: {payment}\n"
            f"📝 Реквизиты: {requisites}"
        )
        try:
            for admin_id in ADMIN_IDS:
                await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Admin notify failed: {e}")
        return

    if data == "confirm_no":
        if lang == "ru":
            text = "❌ Вы отказались от сделки. Если передумаете — мы всегда готовы!\n\nВозвращайтесь в главное меню 👇"
        else:
            text = "❌ You declined the deal. If you change your mind — we're always ready!\n\nReturn to the main menu 👇"
        await safe_edit(query, text, back_keyboard(lang))
        context.user_data.clear()
        return

    if data == "paid":
        # Обработка нажатия кнопки "Я оплатил"
        nft_link = context.user_data.get("nft_link", "")
        price_str = format_price(context.user_data.get("our_price", 0), context.user_data.get("pay_idx", 0))
        
        if lang == "ru":
            text = (
                "💸 *Спасибо за подтверждение!*\n\n"
                "Менеджер уже получил уведомление и скоро свяжется с вами для завершения сделки.\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💰 Сумма: {price_str}\n\n"
                "Если у вас возникли вопросы — обратитесь к менеджеру @liiina_newq"
            )
        else:
            text = (
                "💸 *Thank you for confirmation!*\n\n"
                "The manager has been notified and will contact you shortly to complete the deal.\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💰 Amount: {price_str}\n\n"
                "If you have any questions — contact the manager @liiina_newq"
            )
        
        await safe_edit(query, text, back_keyboard(lang))
        
        # Уведомление админам о подтверждении оплаты
        user = query.from_user
        admin_text = (
            "💰 *Подтверждение оплаты!*\n"
            f"👤 Пользователь: @{user.username or user.id} ({user.id})\n"
            f"📎 NFT: {nft_link}\n"
            f"💵 Сумма: {price_str}\n"
            "✅ Пользователь подтвердил получение оплаты"
        )
        try:
            for admin_id in ADMIN_IDS:
                await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Admin notify failed: {e}")
        
        context.user_data.clear()
        return

    # ==================== ADMIN PANEL ====================
    if data == "admin_stats":
        await safe_edit(
            query,
            "📊 *Статистика бота*\n\n"
            "👥 Пользователей: —\n"
            "💰 Сделок: —\n"
            "📈 Объём выплат: —\n\n"
            "_Подключите БД для реальной статистики_",
            admin_keyboard()
        )
        return

    if data == "admin_broadcast":
        await safe_edit(
            query,
            "📢 *Рассылка*\n\nДля рассылки подключите базу данных и сохраняйте user\\_id пользователей.",
            admin_keyboard()
        )
        return

    if data == "admin_banner":
        await safe_edit(
            query,
            "🖼 *Изменение баннера*\n\nОтправьте новое фото боту. (Требует реализации хранилища)",
            admin_keyboard()
        )
        return

    if data == "admin_deals":
        await safe_edit(
            query,
            "💬 *Все сделки*\n\nПодключите базу данных для просмотра истории сделок.",
            admin_keyboard()
        )
        return

    if data == "admin_ban":
        await safe_edit(
            query,
            "🚫 *Блокировка*\n\nВведите /ban USER\\_ID для блокировки пользователя.",
            admin_keyboard()
        )
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    lang = get_lang(context)
    text = update.message.text.strip()

    if state == WAITING_NFT_LINK:
        if not is_nft_link(text):
            if lang == "ru":
                err = "⚠️ *Ошибка!* Это не похоже на ссылку NFT-подарка.\n\nПожалуйста, отправьте корректную ссылку:\n`https://t.me/nft/НазваниеНФТ-Номер`"
            else:
                err = "⚠️ *Error!* This doesn't look like an NFT gift link.\n\nPlease send a valid link:\n`https://t.me/nft/NFTName-Number`"
            await update.message.reply_text(err, parse_mode="Markdown")
            return

        context.user_data["nft_link"] = text
        nft_name = text.split("/nft/")[-1].split("-")[0]
        base_usd, our_usd = estimate_price_usd(nft_name)
        context.user_data["base_price"] = base_usd
        context.user_data["our_price"] = our_usd
        context.user_data["state"] = WAITING_PAYMENT_METHOD

        if lang == "ru":
            msg = (
                "🔍 *Анализ NFT завершён!*\n\n"
                f"📎 NFT: `{text}`\n"
                f"🏷 Рыночная стоимость: ~${base_usd} USDT\n"
                f"💰 *Наше предложение: ${our_usd} USDT (+30%)*\n\n"
                "Выберите способ получения оплаты — сумма будет пересчитана в вашу валюту 👇"
            )
        else:
            msg = (
                "🔍 *NFT Analysis complete!*\n\n"
                f"📎 NFT: `{text}`\n"
                f"🏷 Market value: ~${base_usd} USDT\n"
                f"💰 *Our offer: ${our_usd} USDT (+30%)*\n\n"
                "Choose your payment method — the amount will be converted to your currency 👇"
            )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=payment_keyboard(lang))
        return

    if state == WAITING_REQUISITES:
        context.user_data["requisites"] = text
        nft_link = context.user_data.get("nft_link", "")
        our_usd = context.user_data.get("our_price", 0)
        base_usd = context.user_data.get("base_price", 0)
        pay_idx = context.user_data.get("pay_idx", 0)
        payment = context.user_data.get("payment", "")
        context.user_data["state"] = None

        price_str = format_price(our_usd, pay_idx)
        market_str = format_price(base_usd, pay_idx)

        if lang == "ru":
            msg = (
                "📋 *Итог сделки:*\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💳 Способ оплаты: {payment}\n"
                f"🏷 Рынок: ~{market_str}\n"
                f"💵 Сумма: *{price_str}*\n"
                f"📝 Реквизиты: `{text}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💬 Я предлагаю вам за ваш NFT `{nft_link}` сумму *{price_str}*\n\n"
                "Если согласны — нажмите *Да*, если нет — *Нет* 👇"
            )
        else:
            msg = (
                "📋 *Deal summary:*\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💳 Payment method: {payment}\n"
                f"🏷 Market: ~{market_str}\n"
                f"💵 Amount: *{price_str}*\n"
                f"📝 Details: `{text}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"💬 I offer you for your NFT `{nft_link}` the sum of *{price_str}*\n\n"
                "If you agree — press *Yes*, if not — *No* 👇"
            )
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=confirm_keyboard(lang))
        return

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Доступ запрещён.")
        return

    caption = (
        "🛡 *ADMIN PANEL*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 NFT Auto-Buyout Bot\n"
        "👥 Управление пользователями\n"
        "💰 Контроль сделок\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите действие:"
    )
    banner_url = "https://telegra.ph/file/562db3a3a06a4c4a35b71.jpg"
    try:
        await update.message.reply_photo(
            photo=banner_url,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=admin_keyboard()
        )
    except Exception:
        await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=admin_keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
