import os
import time
import asyncio
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

keyboard = ReplyKeyboardMarkup(
    [["📡 مراقبة تيك توك"], ["▶️ دخول رابط فيديو"]],
    resize_keyboard=True
)

# حالات المستخدم
USER_STATE = {}
WATCH_DATA = {}  # chat_id -> {username, last_video_id, last_live}

# ---------- أدوات مساعدة ----------
def extract_username_from_url(url: str) -> str | None:
    # يقبل روابط مثل https://www.tiktok.com/@username
    if "tiktok.com/@" in url:
        return url.split("tiktok.com/@")[-1].split("/")[0]
    return None

def get_tiktok_info(username: str):
    # فحص بسيط (غير رسمي)
    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    text = r.text

    is_live = '"isLive":true' in text
    # محاولة بدائية لاستخراج آخر فيديو
    last_video_id = None
    marker = '"id":"'
    if marker in text:
        last_video_id = text.split(marker)[1].split('"')[0]

    has_story = '"hasStory":true' in text

    return is_live, last_video_id, has_story

# ---------- أوامر ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("اختر أمر 👇", reply_markup=keyboard)

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.message.chat_id

    if text == "📡 مراقبة تيك توك":
        USER_STATE[chat_id] = "WAIT_TT_ACCOUNT"
        await update.message.reply_text("أرسل رابط حساب تيك توك 👇")

    elif text == "▶️ دخول رابط فيديو":
        USER_STATE[chat_id] = "WAIT_VIDEO_URL"
        await update.message.reply_text("أرسل رابط فيديو تيك توك 👇")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    state = USER_STATE.get(chat_id)

    if state == "WAIT_TT_ACCOUNT":
        username = extract_username_from_url(text)
        if not username:
            await update.message.reply_text("❌ الرابط غير صحيح، أرسل رابط حساب تيك توك")
            return

        WATCH_DATA[chat_id] = {
            "username": username,
            "last_video_id": None,
            "last_live": False
        }
        USER_STATE[chat_id] = None
        await update.message.reply_text(f"✅ تم بدء المراقبة للحساب @{username}")

    elif state == "WAIT_VIDEO_URL":
        if "tiktok.com" not in text:
            await update.message.reply_text("❌ هذا ليس رابط تيك توك")
            return

        headers = {"User-Agent": "Mozilla/5.0"}
        for _ in range(3):
            try:
                requests.get(text, headers=headers, timeout=15)
                time.sleep(15)
            except:
                pass

        USER_STATE[chat_id] = None
        await update.message.reply_text("✅ تم الدخول للرابط 3 مرات للتأكد")

# ---------- مهمة المراقبة ----------
async def watcher(app):
    while True:
        for chat_id, data in WATCH_DATA.items():
            try:
                username = data["username"]
                is_live, last_video_id, has_story = get_tiktok_info(username)

                if is_live and not data["last_live"]:
                    await app.bot.send_message(chat_id, f"🔴 @{username} بدأ لايف")

                if last_video_id and data["last_video_id"] and last_video_id != data["last_video_id"]:
                    await app.bot.send_message(chat_id, f"📹 @{username} نشر فيديو جديد")

                if has_story:
                    await app.bot.send_message(chat_id, f"🟡 @{username} عنده ستوري")

                data["last_live"] = is_live
                data["last_video_id"] = last_video_id

            except Exception as e:
                print("Watcher error:", e)

        await asyncio.sleep(60)

# ---------- التشغيل ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^(📡 مراقبة تيك توك|▶️ دخول رابط فيديو)$"), handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    asyncio.create_task(watcher(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
