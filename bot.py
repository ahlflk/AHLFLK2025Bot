import os
import logging
import asyncio
import sqlite3
from datetime import timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ChatMemberHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode, ChatMemberStatus

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set!")

PUBLIC_URL = os.getenv("PUBLIC_URL")
if not PUBLIC_URL:
    raise RuntimeError("PUBLIC_URL is not set!")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{PUBLIC_URL}{WEBHOOK_PATH}"
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET", "my-super-secret-token")
PORT = int(os.getenv("PORT", 10000))

# Settings
CHATBOT_LOGO_URL = "https://raw.githubusercontent.com/ahlflk/AHLFLK2025Bot/refs/heads/main/chatbot_logo.png"

WELCOME_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("AHLFLK_VPN_APK_ရယူရန်", url="https://t.me/ahlflk2025channel/259")],
    [InlineKeyboardButton("VIP_Account_ဈေးနှုန်းကြည့်ရန်", url="https://t.me/ahlflk2025channel/22")],
    [InlineKeyboardButton("Admin_ကို_ဆက်သွယ်ရန်", url="https://t.me/ahlflk2025")],
])

# Database functions
def init_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))''')
    conn.commit()
    conn.close()

def get_warn_count(chat_id: int, user_id: int) -> int:
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("SELECT count FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def add_warn(chat_id: int, user_id: int) -> int:
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    current = get_warn_count(chat_id, user_id)
    new_count = current + 1
    c.execute("INSERT OR REPLACE INTO warns (chat_id, user_id, count) VALUES (?, ?, ?)", (chat_id, user_id, new_count))
    conn.commit()
    conn.close()
    return new_count

def reset_warns(chat_id: int, user_id: int):
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    c.execute("DELETE FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    conn.commit()
    conn.close()

# Helper
async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type == "private": return False
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

# --- WELCOME FUNCTION (FIXED) ---
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """New member welcome logic using MessageHandler filters"""
    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
            
        chat = update.effective_chat
        caption = (
            f"👋 မင်္ဂလာပါ {user.mention_html()}!\n\n"
            f"🎉 <b>{chat.title}</b> မှ\n"
            f"🎊 နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
        )

        try:
            sent = await context.bot.send_photo(
                chat_id=chat.id,
                photo=CHATBOT_LOGO_URL,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=WELCOME_BUTTONS,
            )
            
            # Delete welcome message after 5 minutes
            context.job_queue.run_once(delete_msg, 300, data=(chat.id, sent.message_id))
        except Exception as e:
            logger.error(f"Welcome failed: {e}")

async def delete_msg(context: ContextTypes.DEFAULT_TYPE):
    chat_id, message_id = context.job_queue.current_job.data
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# --- OTHER HANDLERS ---
async def clean_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete 'user joined' or 'left' service messages"""
    try:
        await update.message.delete()
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("👋 AHLFLK Management Bot မှ ကြိုဆိုပါတယ်။")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context): return
    reply = update.message.reply_to_message
    if not reply: return await update.message.reply_text("Reply to a user to warn.")
    
    count = add_warn(update.effective_chat.id, reply.from_user.id)
    await update.message.reply_text(f"⚠️ {reply.from_user.mention_html()} ကို သတိပေးလိုက်ပါပြီ ({count}/3)", parse_mode=ParseMode.HTML)
    
    if count >= 3:
        await context.bot.ban_chat_member(update.effective_chat.id, reply.from_user.id)
        reset_warns(update.effective_chat.id, reply.from_user.id)

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    
    # User အသစ်ဝင်လာတာကို ဖမ်းတဲ့နေရာ (StatusUpdate filters ကို သုံးထားပါတယ်)
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    
    # Join/Leave စာသားတွေကို ဖျက်ချင်ရင် (Optional)
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, clean_service_messages))

    # Admin commands
    application.add_handler(CommandHandler("warn", warn_command))

    # Webhook run
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET_TOKEN,
        allowed_updates=Update.ALL_TYPES # အရေးကြီးသည်
    )

if __name__ == "__main__":
    main()
