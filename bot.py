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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_URL = os.getenv("PUBLIC_URL")
PORT = int(os.getenv("PORT", 10000))

# --- Settings ---
CHATBOT_LOGO_URL = "https://raw.githubusercontent.com/ahlflk/AHLFLK2025Bot/refs/heads/main/chatbot_logo.png"
MAX_WARNS = 3

# --- Keyboards ---
WELCOME_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("A_PRO_VPN_APK_ရယူရန်", url="https://t.me/ahlflk2025channel/23")],
    [InlineKeyboardButton("VIP_Account_ဈေးနှုန်းကြည့်ရန်", url="https://t.me/ahlflk2025channel/22")],
    [InlineKeyboardButton("Admin_ကို_ဆက်သွယ်ရန်", url="https://t.me/ahlflk2025")],
])

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS warns (chat_id INTEGER, user_id INTEGER, count INTEGER DEFAULT 0, PRIMARY KEY (chat_id, user_id))''')
    conn.commit()
    conn.close()

def update_warn(chat_id, user_id, reset=False):
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    if reset:
        c.execute("DELETE FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        new_count = 0
    else:
        c.execute("SELECT count FROM warns WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
        row = c.fetchone()
        new_count = (row[0] + 1) if row else 1
        c.execute("INSERT OR REPLACE INTO warns (chat_id, user_id, count) VALUES (?, ?, ?)", (chat_id, user_id, new_count))
    conn.commit()
    conn.close()
    return new_count

# --- Helper ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private": return True
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]

# --- Core Handlers ---

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User အသစ်ဝင်လာရင် ကြိုဆိုတဲ့အပိုင်း"""
    for user in update.message.new_chat_members:
        if user.is_bot: continue
        
        chat = update.effective_chat
        # သင်တောင်းဆိုထားတဲ့ format အတိုင်း ပြင်ဆင်ထားပါတယ်
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
                reply_markup=WELCOME_BUTTONS,
                parse_mode=ParseMode.HTML
            )
            # Welcome message ကို ၅ မိနစ်အကြာမှာ ဖျက်ပေးမယ်
            context.job_queue.run_once(lambda ctx: context.bot.delete_message(chat.id, sent.message_id), 300)
        except Exception as e:
            logger.error(f"Error in welcome: {e}")

    # 'Joined' service message ကို ဖျက်တယ်
    try: await update.message.delete()
    except: pass

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About, Help, Rules ခလုတ်တွေအတွက် logic"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "about":
        about_text = (
            "🤖 <b>Bot အကြောင်း</b>\n\n"
            "ဤ Bot သည် Group Member များအတွက် "
            "ပြုလုပ်ထားသော Management Bot ဖြစ်ပါသည်။\n\n"
            "✅ Developer: @ahlflk2025"
        )
        await query.message.reply_text(about_text, parse_mode=ParseMode.HTML)
        
    elif query.data == "rules":
        rules_text = (
            "📜 <b>အဖွဲ့စည်းမျဉ်းများ</b>\n\n"
            "၁။ ယဉ်ကျေးစွာ ပြောဆိုပါ။\n"
            "၂။ Group နှင့် မသက်ဆိုင်သော Spam/Link များ မပို့ရ။\n"
            "၃။ Rules နှင့် အညီ လွတ်လပ်စွာ ပြောဆိုဆွေးနွေး နိုင်ပါတယ်"
        )
        await query.message.reply_text(rules_text, parse_mode=ParseMode.HTML)

    elif query.data == "help":
        help_text = (
            "❓ <b>အကူအညီ (Admin Commands)</b>\n\n"
            "/warn - သတိပေးရန်\n"
            "/mute [နာရီ] - စကားပိတ်ရန်\n"
            "/unmute - ပြန်ဖွင့်ရန်\n"
            "/ban - ထုတ်ပစ်ရန်"
        )
        await query.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def anti_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin မဟုတ်သူများ Link ပို့ပါက ဖျက်ရန်"""
    if await is_admin(update, context): return
    
    if any(entity.type in ['url', 'text_link'] for entity in update.message.entities or []):
        try:
            await update.message.delete()
            # သတိပေးစာ ခဏပြမယ်
            warning = await update.message.reply_text(f"⚠️ {update.effective_user.mention_html()} Link ပို့ခွင့်မရှိပါ။", parse_mode=ParseMode.HTML)
            context.job_queue.run_once(lambda ctx: context.bot.delete_message(update.effective_chat.id, warning.message_id), 10)
        except: pass

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    reply = update.message.reply_to_message
    if not reply: return
    
    count = update_warn(update.effective_chat.id, reply.from_user.id)
    if count >= MAX_WARNS:
        await context.bot.ban_chat_member(update.effective_chat.id, reply.from_user.id)
        await update.message.reply_text(f"⛔ {reply.from_user.mention_html()} ကို Ban လိုက်ပါပြီ (၃ ကြိမ်ပြည့်)။", parse_mode=ParseMode.HTML)
        update_warn(update.effective_chat.id, reply.from_user.id, reset=True)
    else:
        await update.message.reply_text(f"⚠️ သတိပေးချက် ({count}/{MAX_WARNS}) ရရှိသွားပါပြီ။", parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📚 About", callback_data="about"), InlineKeyboardButton("📜 Rules", callback_data="rules")],
            [InlineKeyboardButton("❓ Help", callback_data="help")]
        ])
        await update.message.reply_text("👋 AHLFLK Management Bot မှ ကြိုဆိုပါတယ်။", reply_markup=kb)

# --- Main ---
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message Handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), anti_link_handler))
    # Leave service message ဖျက်ရန်
    application.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, lambda u, c: u.message.delete()))

    # Run
    if PUBLIC_URL:
        application.run_webhook(listen="0.0.0.0", port=PORT, url_path="webhook", 
                                webhook_url=f"{PUBLIC_URL}/webhook", allowed_updates=Update.ALL_TYPES)
    else:
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
