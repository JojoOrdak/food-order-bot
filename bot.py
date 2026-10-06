import os
import logging
from threading import Thread

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_USERNAME = "@Mr_Ordakz"
CARD_NUMBER = "6219 8618 5268 3118"
CARD_NAME = "یاسین هلالی"

PRODUCTS = {
    "mayo": ("🌭 ساندویچ کالباس + سس مایونز", 110_000),
    "ketchup": ("🌭 ساندویچ کالباس + سس گوجه", 110_000),
    "special": ("🌭 ساندویچ کالباس + سس مخصوص", 120_000),
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tiny HTTP server for Render Web Service health checks.
web = Flask(__name__)

@web.get("/")
def home():
    return "Food bot is running."

@web.get("/health")
def health():
    return "OK"

def run_web():
    port = int(os.getenv("PORT", "10000"))
    web.run(host="0.0.0.0", port=port)

def toman(price):
    return f"{price:,} تومان"

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌭 ساندویچ کالباس", callback_data="sandwiches")]
    ])

def sandwich_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🥪 کالباس + سس مایونز | ۱۱۰ هزار", callback_data="mayo")],
        [InlineKeyboardButton("🥪 کالباس + سس گوجه | ۱۱۰ هزار", callback_data="ketchup")],
        [InlineKeyboardButton("🥪 کالباس + سس مخصوص | ۱۲۰ هزار", callback_data="special")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="home")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("selected_product", None)
    await update.message.reply_text(
        "🍔 *منوی غذا*\n\nبرای مشاهده ساندویچ‌ها روی گزینه زیر بزنید:",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "home":
        await query.edit_message_text(
            "🍔 *منوی غذا*\n\nبرای مشاهده ساندویچ‌ها انتخاب کنید:",
            parse_mode="Markdown", reply_markup=main_menu()
        )
        return

    if query.data == "sandwiches":
        await query.edit_message_text(
            "🌭 *انتخاب ساندویچ*\n\nیکی از گزینه‌ها را انتخاب کنید:",
            parse_mode="Markdown", reply_markup=sandwich_menu()
        )
        return

    if query.data in PRODUCTS:
        name, price = PRODUCTS[query.data]
        context.user_data["selected_product"] = query.data
        await query.edit_message_text(
            f"*{name}*\n\n"
            f"💰 قیمت: *{toman(price)}*\n\n"
            f"💳 شماره کارت:\n`{CARD_NUMBER}`\n\n"
            f"👤 به نام: *{CARD_NAME}*\n\n"
            "━━━━━━━━━━━━━━\n"
            "📸 بعد از پرداخت، از رسید پرداخت عکس بگیرید "
            f"و آن را به آیدی زیر ارسال کنید:\n\n"
            f"🆔 {OWNER_USERNAME}\n\n"
            "⚠️ لطفاً عکس واضح رسید را ارسال کنید.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="sandwiches")]
            ])
        )

async def receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected = context.user_data.get("selected_product")
    if not selected:
        await update.message.reply_text(
            "ابتدا از منوی غذا یک ساندویچ انتخاب کنید.",
            reply_markup=main_menu()
        )
        return

    name, price = PRODUCTS[selected]
    user = update.effective_user
    username = f"@{user.username}" if user.username else "بدون یوزرنیم"
    caption = (
        "📥 *رسید پرداخت جدید*\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🆔 آیدی: {username}\n"
        f"🔢 User ID: `{user.id}`\n\n"
        f"🍔 سفارش: {name}\n"
        f"💰 مبلغ: {toman(price)}"
    )

    owner_chat_id = os.getenv("OWNER_CHAT_ID", "").strip()
    if not owner_chat_id:
        await update.message.reply_text(
            "✅ رسید دریافت شد.\n\n"
            "برای ارسال خودکار رسید به صاحب بات، OWNER_CHAT_ID را در تنظیمات سرویس وارد کنید."
        )
        return

    try:
        chat_id = int(owner_chat_id)
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=update.message.photo[-1].file_id,
                caption=caption,
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode="Markdown"
            )
        await update.message.reply_text(
            "✅ رسید شما با موفقیت ارسال شد.\nلطفاً منتظر تأیید پرداخت بمانید."
        )
    except Exception:
        logger.exception("Receipt forwarding failed")
        await update.message.reply_text(
            "رسید دریافت شد، اما ارسال آن برای مدیریت با مشکل مواجه شد."
        )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 شناسه عددی شما:\n`{update.effective_user.id}`",
        parse_mode="Markdown"
    )

async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "لطفاً از دکمه‌های منو استفاده کنید.",
        reply_markup=main_menu()
    )

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.PHOTO, receipt))
    app.add_handler(MessageHandler(filters.ALL, fallback))

    app.run_polling()

if __name__ == "__main__":
    main()
