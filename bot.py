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

# Fixed Buttons for Group welcome
WELCOME_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("AHLFLK_VPN_PRO_APK_ရယူရန်", url="https://t.me/ahlflk2025channel/239")],
    [InlineKeyboardButton("VIP_Account_ဈေးနှုန်းကြည့်ရန်", url="https://t.me/ahlflk2025channel/22")],
    [InlineKeyboardButton("Admin_ကို_ဆက်သွယ်ရန်", url="@ahlflk2025")],
])

# Database
DB_FILE = "bot.db"
MAX_WARNS = 3

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS warns (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    ''')
    conn.commit()
    conn.close()

def get_warn_count(chat_id: int, user_id: int) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT count FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def add_warn(chat_id: int, user_id: int) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    current = get_warn_count(chat_id, user_id)
    new_count = current + 1
    if current == 0:
        c.execute("INSERT INTO warns (chat_id, user_id, count) VALUES (?, ?, ?)", (chat_id, user_id, new_count))
    else:
        c.execute("UPDATE warns SET count = ? WHERE chat_id = ? AND user_id = ?", (new_count, chat_id, user_id))
    conn.commit()
    conn.close()
    return new_count

def reset_warns(chat_id: int, user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    conn.commit()
    conn.close()

# Admin check
async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if chat.type == "private":
        return False
    member = await context.bot.get_chat_member(chat_id=chat.id, user_id=user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

# --- ပြင်ဆင်ထားသော Welcome Function ---
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Member အသစ်ဝင်လာရင် နှုတ်ဆက်စာ ပို့ပေးရန်"""
    # ChatMemberUpdate ဖြစ်မှသာ ဆက်လုပ်မည်
    if not update.chat_member:
        return
        
    new_chat_member = update.chat_member.new_chat_member
    new_status = new_chat_member.status

    # Member အသစ်ဖြစ်နေရမည် (Bot မဟုတ်ရ)
    if new_status == ChatMemberStatus.MEMBER and not new_chat_member.user.is_bot:
        user = new_chat_member.user
        chat = update.effective_chat

        caption = (
            f"👋 မင်္ဂလာပါ {user.mention_html()}!\n\n"
            f"🎉 <b>{chat.title}</b> မှ\n\n"
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
            # ၅ မိနစ်ကြာရင် ပြန်ဖျက်မည်
            await asyncio.sleep(300)
            await sent.delete()
        except Exception as e:
            logger.error(f"Error in welcome message: {e}")

# Clean service messages (Joined/Left system messages)
async def clean_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members or update.message.left_chat_member:
        try:
            await update.message.delete()
        except:
            pass

# Commands & Handlers
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "about":
        text = "🤖 <b>Bot အကြောင်း</b>\n\n👥 Group Management Bot ပါ။\n\n👨‍💻 Developer: @ahlflk2025"
    elif data == "help":
        text = "❓ <b>အကူအညီ (Admin Commands)</b>\n\n/warn - သတိပေး\n/warns - အမှတ်ကြည့်\n/resetwarns - အမှတ်ရှင်း\n/mute [နာရီ] - Mute\n/unmute - Unmute\n/ban - Ban\n/unban - Unban\n/rules - စည်းမျဉ်း\n\nReply ပြန်ပြီး သုံးပါ။"
    elif data == "contact":
        text = "📞 <b>ဆက်သွယ်ရန်</b>\n\n👇 Admin_Account\n\n👉 @ahlflk2025"
    elif data == "rules":
        text = "📜 <b>အဖွဲ့ စည်းမျဉ်း</b>\n\n1. ယဉ်ကျေးစွာ ပြောဆိုပါ\n2. Spam၊ Ads မလုပ်ပါနဲ့\n3. အဖွဲ့နဲ့ မသက်ဆိုင်တာ မမျှဝေပါနဲ့"
    else: return
    await query.edit_message_text(text=text, parse_mode=ParseMode.HTML)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 <b>အဖွဲ့ စည်းမျဉ်း</b>\n\n1. ယဉ်ကျေးစွာ ပြောဆိုပါ\n2. Spam မလုပ်ပါနဲ့", parse_mode=ParseMode.HTML)

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context): return
    reply_msg = update.message.reply_to_message
    if not reply_msg: return
    count = add_warn(update.effective_chat.id, reply_msg.from_user.id)
    await update.message.reply_text(f"⚠️ Warn {count}/{MAX_WARNS}")

async def warns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_msg = update.message.reply_to_message
    if not reply_msg: return
    count = get_warn_count(update.effective_chat.id, reply_msg.from_user.id)
    await update.message.reply_text(f"📊 Warn Count: {count}")

async def resetwarns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context): return
    reply_msg = update.message.reply_to_message
    if not reply_msg: return
    reset_warns(update.effective_chat.id, reply_msg.from_user.id)
    await update.message.reply_text("✅ Reset Successful")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context): return
    reply_msg = update.message.reply_to_message
    if not reply_msg: return
    await context.bot.restrict_chat_member(update.effective_chat.id, reply_msg.from_user.id, permissions={"can_send_messages": False})
    await update.message.reply_text("🔇 Muted")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context): return
    reply_msg = update.message.reply_to_message
    if not reply_msg: return
    await context.bot.restrict_chat_member(update.effective_chat.id, reply_msg.from_user.id, permissions={"can_send_messages": True, "can_send_media_messages": True, "can_send_polls": True, "can_send_other_messages": True, "can_add_web_page_previews": True})
    await update.message.reply_text("🔊 Unmuted")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context): return
    reply_msg = update.message.reply_to_message
    if not reply_msg: return
    await context.bot.ban_chat_member(update.effective_chat.id, reply_msg.from_user.id)
    await update.message.reply_text("⛔ Banned")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context): return
    reply_msg = update.message.reply_to_message
    if not reply_msg: return
    await context.bot.unban_chat_member(update.effective_chat.id, reply_msg.from_user.id)
    await update.message.reply_text("✅ Unbanned")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private": return
    keyboard = [[InlineKeyboardButton("📚 အကြောင်းအရာ", callback_data="about"), InlineKeyboardButton("❓ အကူအညီ", callback_data="help")]]
    await update.message.reply_text("👋 မင်္ဂလာပါ!", reply_markup=InlineKeyboardMarkup(keyboard))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# Main Logic
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("warns", warns_command))
    application.add_handler(CommandHandler("resetwarns", resetwarns_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("unmute", unmute_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    # --- ဒီအစီအစဉ်အတိုင်း ထားပေးပါ ---
    # ၁။ Member Update ကို အရင်ဖမ်းရန်
    application.add_handler(ChatMemberHandler(greet_new_member, ChatMemberHandler.CHAT_MEMBER))
    # ၂။ ပြီးမှ System message တွေကို ဖျက်ရန်
    application.add_handler(MessageHandler(filters.StatusUpdate.ALL, clean_service_messages))

    application.add_error_handler(error_handler)

    application.run_webhook(
        listen="0.0.0.0", port=PORT, url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET_TOKEN
    )

if __name__ == "__main__":
    main()
