import os
import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode, ChatMemberStatus

# --- Logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = f"{PUBLIC_URL}/webhook"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "my-secret-123")

# --- Settings ---
CHATBOT_LOGO_URL = "https://raw.githubusercontent.com/ahlflk/AHLFLK2025Bot/refs/heads/main/chatbot_logo.png"
MAX_WARNS = 3
DB_FILE = "management.db"

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS warns 
                 (chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0, 
                 PRIMARY KEY (chat_id, user_id))''')
    conn.commit()
    conn.close()

def get_warns(chat_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT count FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def add_warn(chat_id, user_id):
    count = get_warns(chat_id, user_id) + 1
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO warns (chat_id, user_id, count) VALUES (?, ?, ?)", (chat_id, user_id, count))
    conn.commit()
    conn.close()
    return count

def clear_warns(chat_id, user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    conn.commit()
    conn.close()

# --- Keyboards ---
WELCOME_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("A_VPN_PRO_APK_ရယူရန်", url="https://t.me/ahlflk2025channel/750")],
    [InlineKeyboardButton("VIP_Account_ဈေးနှုန်းကြည့်ရန်", url="https://t.me/ahlflk2025channel/22")],
    [InlineKeyboardButton("Admin_ကို_ဆက်သွယ်ရန်", url="https://t.me/ahlflk2025")],
])

START_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📚 About", callback_data="about"), InlineKeyboardButton("📜 Rules", callback_data="rules")],
    [InlineKeyboardButton("❓ Help", callback_data="help"), InlineKeyboardButton("📞 Contact", url="https://t.me/ahlflk2025")]
])

# --- Helper Function ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return True
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            f"👋 မင်္ဂလာပါ <b>{update.effective_user.first_name}</b>!\n\n"
            "ကျွန်ုပ်သည် AHLFLK Group Management Bot ဖြစ်ပါတယ်။\n"
            "အဖွဲ့ဝင်များကို စောင့်ကြည့်ရန်နှင့် စည်းကမ်းထိန်းသိမ်းရန် ကူညီပေးပါတယ်။",
            reply_markup=START_KEYBOARD,
            parse_mode=ParseMode.HTML
        )

async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets new members with the requested format"""
    for user in update.message.new_chat_members:
        if user.is_bot: continue
        
        chat = update.effective_chat
        # သင်တောင်းဆိုထားတဲ့ တစ်ကြောင်းချင်းစီ format
        caption = (
            f"👋 မင်္ဂလာပါ {user.mention_html()}!\n\n"
            f"🎉 <b>{chat.title}</b> မှ\n"
            f"🎊 နွေးထွေးစွာ ကြိုဆိုပါတယ်။"
        )
        
        try:
            sent_msg = await context.bot.send_photo(
                chat_id=chat.id,
                photo=CHATBOT_LOGO_URL,
                caption=caption,
                reply_markup=WELCOME_BUTTONS,
                parse_mode=ParseMode.HTML
            )
            # ၅ မိနစ်အကြာတွင် welcome message ကို ပြန်ဖျက်မည်
            context.job_queue.run_once(lambda ctx: context.bot.delete_message(chat.id, sent_msg.message_id), 300)
        except Exception as e:
            logger.error(f"Welcome failed: {e}")

    try: await update.message.delete()
    except: pass

async def anti_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin မဟုတ်သူများ Link ပို့ပါက ဖျက်ရန်"""
    if await is_admin(update, context): return
    
    if any(entity.type in ['url', 'text_link'] for entity in update.message.entities or []):
        try:
            await update.message.delete()
            warning = await update.message.reply_text(f"⚠️ {update.effective_user.mention_html()} Link ပို့ခွင့်မရှိပါ။")
            context.job_queue.run_once(lambda ctx: context.bot.delete_message(update.effective_chat.id, warning.message_id), 10)
        except: pass

async def warn_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    reply = update.message.reply_to_message
    if not reply: return await update.message.reply_text("⚠️ User ရဲ့ message ကို reply ပြန်ပြီး သုံးပါ။")
    
    target = reply.from_user
    count = add_warn(update.effective_chat.id, target.id)
    
    if count >= MAX_WARNS:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await update.message.reply_text(f"⛔ {target.mention_html()} ကို သတိပေးချက် ၃ ကြိမ်ပြည့်သဖြင့် Ban လိုက်ပါပြီ။", parse_mode=ParseMode.HTML)
        clear_warns(update.effective_chat.id, target.id)
    else:
        await update.message.reply_text(f"⚠️ {target.mention_html()} ကို သတိပေးလိုက်ပါပြီ။ ({count}/{MAX_WARNS})", parse_mode=ParseMode.HTML)

async def mute_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    reply = update.message.reply_to_message
    if not reply: return
    
    hours = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
    until = datetime.now() + timedelta(hours=hours)
    
    await context.bot.restrict_chat_member(
        update.effective_chat.id, 
        reply.from_user.id, 
        permissions={"can_send_messages": False},
        until_date=until
    )
    await update.message.reply_text(f"🔇 {reply.from_user.mention_html()} ကို {hours} နာရီကြာ Mute လိုက်ပါပြီ။", parse_mode=ParseMode.HTML)

async def unmute_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    reply = update.message.reply_to_message
    if not reply: return
    
    await context.bot.restrict_chat_member(
        update.effective_chat.id, 
        reply.from_user.id, 
        permissions={
            "can_send_messages": True, "can_send_media_messages": True,
            "can_send_polls": True, "can_send_other_messages": True,
            "can_add_web_page_previews": True
        }
    )
    await update.message.reply_text(f"🔊 {reply.from_user.mention_html()} စကားပြန်ပြောလို့ရပါပြီ။", parse_mode=ParseMode.HTML)

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "about":
        text = "🤖 <b>Bot အကြောင်း</b>\n\nဤ Bot သည် AHLFLK Group များအတွက် ပြုလုပ်ထားသော Management Bot ဖြစ်ပါသည်။\n\n👨‍💻 Developer: @ahlflk2025"
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)
    elif query.data == "rules":
        text = "📜 <b>Rules:</b>\n1. No Spam\n2. Respect Others\n3. No Illegal Links"
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)
    elif query.data == "help":
        text = "❓ <b>Help:</b>\n/warn - သတိပေးရန်\n/mute [နာရီ] - စကားပိတ်ရန်\n/unmute - ပြန်ဖွင့်ရန်\n/ban - ထုတ်ပစ်ရန်"
        await query.message.reply_text(text, parse_mode=ParseMode.HTML)

# --- Main Engine ---
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("warn", warn_member))
    application.add_handler(CommandHandler("mute", mute_member))
    application.add_handler(CommandHandler("unmute", unmute_member))
    application.add_handler(CommandHandler("ban", warn_member))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Message Handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), anti_link_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, lambda u, c: u.message.delete()))

    # Run Bot
    if PUBLIC_URL:
        application.run_webhook(
            listen="0.0.0.0", port=PORT, url_path="webhook",
            webhook_url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES
        )
    else:
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
