import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

import json
from config import BOT_TOKEN, ADMIN_ID

# Holatlar (states)
CHOOSING_LANG, CHOOSING_UC, ENTERING_PUBG_ID, CHOOSING_PAYMENT, SENDING_SCREENSHOT = range(5)

# Til fayllarini yuklash
with open("locale/uz.json", "r", encoding="utf-8") as f:
    uz = json.load(f)
with open("locale/ru.json", "r", encoding="utf-8") as f:
    ru = json.load(f)

lang_data = {"uz": uz, "ru": ru}

# Foydalanuvchilar tilini saqlash (oddiy dict, real loyihada DB yoki kesh tavsiya qilinadi)
user_lang = {}
user_data = {}

logging.basicConfig(level=logging.INFO)

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Tilni tanlang / Выберите язык:", reply_markup=reply_markup)
    return CHOOSING_LANG

# Til tanlandi
async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    user_lang[query.from_user.id] = lang
    user_data[query.from_user.id] = {}
    uc_list = lang_data[lang]["uc_options"]

    keyboard = [
        [InlineKeyboardButton(f"{uc['label']} – {uc['price']}", callback_data=f"uc_{uc['label']}")] for uc in uc_list
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=lang_data[lang]["choose_uc"], reply_markup=reply_markup)
    return CHOOSING_UC

# UC tanlandi
async def uc_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uc = query.data.split("_")[1]
    user_data[query.from_user.id]['uc_amount'] = uc
    lang = user_lang.get(query.from_user.id, "uz")
    await query.message.reply_text(lang_data[lang]["enter_pubg_id"])
    return ENTERING_PUBG_ID

# PUBG ID kiritildi
async def pubg_id_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    user_data[user_id]['pubg_id'] = text
    lang = user_lang.get(user_id, "uz")
    payment_methods = lang_data[lang]["payment_methods"]
    keyboard = [
        [InlineKeyboardButton(method, callback_data=f"pay_{method}")] for method in payment_methods
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(lang_data[lang]["choose_payment"], reply_markup=reply_markup)
    return CHOOSING_PAYMENT

# To'lov usuli tanlandi
async def payment_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    method = query.data.split("_")[1]
    user_data[user_id]['payment_method'] = method
    lang = user_lang.get(user_id, "uz")
    await query.message.reply_text(lang_data[lang]["send_screenshot"])
    await query.message.reply_text(lang_data[lang]["cards"])
    return SENDING_SCREENSHOT

# Screenshot yoki boshqa media keldi
async def screenshot_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_lang.get(user_id, "uz")
    data = user_data.get(user_id, {})
    caption = (
        f"📥 Yangi buyurtma:\n\n"
        f"UC: {data.get('uc_amount')}\n"
        f"PUBG ID: {data.get('pubg_id')}\n"
        f"To'lov turi: {data.get('payment_method')}\n\n"
        f"Foydalanuvchi: @{update.message.from_user.username or user_id}"
    )

    # Admin ga jo'natish
    if update.message.photo:
        photo = update.message.photo[-1]
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo.file_id, caption=caption)
    else:
        await context.bot.send_message(chat_id=ADMIN_ID, text=caption)

    await update.message.reply_text(lang_data[lang]["done"])
    # Tozalash
    user_data[user_id] = {}
    return ConversationHandler.END

# Cancel (bekor qilish)
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.")
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_LANG: [CallbackQueryHandler(language_selected, pattern="^lang_")],
            CHOOSING_UC: [CallbackQueryHandler(uc_chosen, pattern="^uc_")],
            ENTERING_PUBG_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, pubg_id_entered)],
            CHOOSING_PAYMENT: [CallbackQueryHandler(payment_chosen, pattern="^pay_")],
            SENDING_SCREENSHOT: [MessageHandler(filters.PHOTO | filters.Document.IMAGE, screenshot_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
