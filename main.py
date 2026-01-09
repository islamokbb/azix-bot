import os
import time
import threading
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from TikTokLive import TikTokLiveClient
from TikTokApi import TikTokApi

# ====== إعدادات ======
BOT_TOKEN = os.getenv("BOT_TOKEN")

keyboard = ReplyKeyboardMarkup(
    [
        ["📡 مراقبة تيك توك", "▶️ دخول رابط فيديو"],
        ["📊 معلومات الحساب (API)", "🔴 مراقبة لايف (API)"],
        ["⛔ إيقاف مراقبة لايف"]
    ],
    resize_keyboard=True
)

USER_STATE = {}
WATCH_DATA = {}
LIVE_CLIENTS = {}  # chat_id -> TikTokLiveClient

# ====== أدوات ======
def clean_username(text):
    text = text.strip()
    if text.startswith("@"):
        text = text[1:]
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._"
    if not all(c in allowed for c in text):
        return None
    return text


# ====== أوامر ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اختر أمر 👇", reply_markup=keyboard)


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    if text == "📡 مراقبة تيك توك":
        USER_STATE[chat_id] = "WAIT_MONITOR"
        await update.message.reply_text("أرسل يوزر تيك توك 👇")

    elif text == "▶️ دخول رابط فيديو":
        USER_STATE[chat_id] = "WAIT_VIDEO"
        await update.message.reply_text("أرسل رابط فيديو تيك توك 👇")

    elif text == "📊 معلومات الحساب (API)":
        USER_STATE[chat_id] = "WAIT_API_INFO"
        await update.message.reply_text("أرسل يوزر تيك توك 👇")

    elif text == "🔴 مراقبة لايف (API)":
        USER_STATE[chat_id] = "WAIT_API_LIVE"
        await update.message.reply_text("أرسل يوزر تيك توك 👇")

    elif text == "⛔ إيقاف مراقبة لايف":
        client = LIVE_CLIENTS.get(chat_id)
        if client:
            client.stop()
            del LIVE_CLIENTS[chat_id]
            await update.message.reply_text("⛔ تم إيقاف مراقبة اللايف")
        else:
            await update.message.reply_text("ℹ️ لا يوجد لايف مراقَب حالياً")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text
    state = USER_STATE.get(chat_id)

    # ====== مراقبة Scraping (كما هي) ======
    if state == "WAIT_MONITOR":
        username = clean_username(text)
        if not username:
            await update.message.reply_text("❌ يوزر غير صحيح")
            return

        WATCH_DATA[chat_id] = {
            "username": username,
            "last_video_id": None,
            "last_live": False
        }

        USER_STATE[chat_id] = None
        await update.message.reply_text(f"✅ تم بدء مراقبة @{username}")

    # ====== دخول رابط فيديو ======
    elif state == "WAIT_VIDEO":
        if "tiktok.com" not in text:
            await update.message.reply_text("❌ هذا ليس رابط تيك توك")
            return

        headers = {"User-Agent": "Mozilla/5.0"}
        for _ in range(3):
            try:
                requests.get(text, headers=headers, timeout=10)
                time.sleep(10)
            except:
                pass

        USER_STATE[chat_id] = None
        await update.message.reply_text("✅ تم الدخول للرابط 3 مرات")

    # ====== معلومات الحساب (API) ======
    elif state == "WAIT_API_INFO":
        username = clean_username(text)
        if not username:
            await update.message.reply_text("❌ يوزر غير صحيح")
            return

        try:
            with TikTokApi() as api:
                user = api.user(username=username)
                info = user.info()
                stats = info.get("stats", {})

            msg = (
                f"📊 معلومات الحساب (API)\n\n"
                f"👤 @{username}\n"
                f"👥 المتابعين: {stats.get('followerCount', 'غير متوفر')}\n"
                f"👤 يتابع: {stats.get('followingCount', 'غير متوفر')}\n"
                f"❤️ الإعجابات: {stats.get('heartCount', 'غير متوفر')}\n"
                f"🎥 عدد الفيديوهات: {stats.get('videoCount', 'غير متوفر')}"
            )

            await update.message.reply_text(msg)

        except Exception as e:
            await update.message.reply_text("❌ فشل جلب معلومات الحساب من API")

        USER_STATE[chat_id] = None

    # ====== مراقبة لايف (API) ======
    elif state == "WAIT_API_LIVE":
        username = clean_username(text)
        if not username:
            await update.message.reply_text("❌ يوزر غير صحيح")
            return

        if chat_id in LIVE_CLIENTS:
            await update.message.reply_text("⚠️ يوجد لايف مراقَب بالفعل")
            USER_STATE[chat_id] = None
            return

        await update.message.reply_text(f"⏳ بدء مراقبة لايف @{username}")

        def run_live():
            client = TikTokLiveClient(unique_id=username)
            LIVE_CLIENTS[chat_id] = client

            @client.on("connect")
            async def on_connect(event):
                await context.bot.send_message(
                    chat_id,
                    f"🔴 @{username} بدأ لايف (API)"
                )

            client.run()

        threading.Thread(target=run_live, daemon=True).start()
        USER_STATE[chat_id] = None


# ====== تشغيل ======
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.Regex(
                "^(📡 مراقبة تيك توك|▶️ دخول رابط فيديو|📊 معلومات الحساب \\(API\\)|🔴 مراقبة لايف \\(API\\)|⛔ إيقاف مراقبة لايف)$"
            ),
            handle_buttons
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()


if __name__ == "__main__":
    main()
