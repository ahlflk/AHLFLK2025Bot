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
    [InlineKeyboardButton("AHLFLK_VPN_APK_ရယူရန်", url="https://t.me/AHLFLK2025channel/259")],
    [InlineKeyboardButton("VIP_Account_ဈေးနှုန်းကြည့်ရန်", url="https://t.me/AHLFLK2025channel/22")],
    [InlineKeyboardButton("Admin_ကို_ဆက်သွယ်ရန်", url="https://t.me/AHLFLK2025")],
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

# Welcome with Photo + Fixed Buttons
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_chat_member = update.chat_member.new_chat_member
    old_status = new_chat_member.old_chat_member.status if new_chat_member.old_chat_member else None
    new_status = new_chat_member.status

    if new_status != ChatMemberStatus.MEMBER or old_status not in [None, ChatMemberStatus.LEFT, ChatMemberStatus.KICKED]:
        return

    user = new_chat_member.user
    chat = update.effective_chat

    if user.is_bot:
        return

    caption = (
        f"👋 မင်္ဂလာပါ {user.mention_html()}!\n\n"
        f"🎉 <b>{chat.title}</b> မှ နွေးထွေးစွာ ကြိုဆိုပါတယ်။\n\n"
        f"အောက်ပါ buttons များကို အသုံးပြုနိုင်ပါပြီ ❤️"
    )

    sent = await context.bot.send_photo(
        chat_id=chat.id,
        photo=CHATBOT_LOGO_URL,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=WELCOME_BUTTONS,
    )

    await asyncio.sleep(300)
    try:
        await sent.delete()
    except:
        pass

# Button handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "about":
        text = "🤖 <b>Bot အကြောင်း</b>\n\nGroup Management Bot ပါ။\n\n👨‍💻 Developer: @AHLFLK2025"
    elif data == "help":
        text = (
            "❓ <b>အကူအညီ (Admin Commands)</b>\n\n"
            "/warn - သတိပေး\n/warns - အမှတ်ကြည့်\n/resetwarns - အမှတ်ရှင်း\n"
            "/mute [နာရီ] - Mute\n/unmute - Unmute\n/ban - Ban\n/unban - Unban\n/rules - စည်းမျဉ်း\n\nအားလုံး reply လုပ်ပြီး သုံးပါ။"
        )
    elif data == "contact":
        text = "📞 <b>ဆက်သွယ်ရန်</b>\n\n"
               "👇 Admin_Account\n"
               "👉 @AHLFLK2025\n\n"
    elif data == "rules":
        text = (
            "📜 <b>အဖွဲ့ စည်းမျဉ်း</b>\n\n"
            "1. ယဉ်ကျေးစွာ ပြောဆိုပါ\n"
            "2. Spam၊ Ads မလုပ်ပါနဲ့\n"
            "3. အဖွဲ့နဲ့ မသက်ဆိုင်တဲ့ အကြောင်းအရာများ မမျှဝေပါနဲ့\n\n"
            "စည်းမျဉ်းများ ချိုးဖောက်ပါက ဖယ်ရှားပါမည်။"
        )
    else:
        return

    await query.edit_message_text(text=text, parse_mode=ParseMode.HTML)

# Rules command
async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Group ထဲမှာသာ သုံးပါ။")
        return
    await update.message.reply_text(
        text=(
            "📜 <b>အဖွဲ့ စည်းမျဉ်း</b>\n\n"
            "1. ယဉ်ကျေးစွာ ပြောဆိုပါ\n"
            "2. Spam၊ Ads မလုပ်ပါနဲ့\n"
            "3. အဖွဲ့နဲ့ မသက်ဆိုင်တဲ့ အကြောင်းအရာများ မမျှဝေပါနဲ့\n\n"
            "စည်းမျဉ်းများ ချိုးဖောက်ပါက ဖယ်ရှားပါမည်။"
        ),
        parse_mode=ParseMode.HTML,
    )

# Moderation Commands
async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("❌ Admin များသာ သုံးခွင့်ရှိပါတယ်။")
        return

    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.from_user:
        await update.message.reply_text("⚠️ Warn လုပ်ချင်တဲ့ message ကို reply လုပ်ပြီး သုံးပါ။")
        return

    target_user = reply_msg.from_user
    chat_id = update.effective_chat.id
    user_id = target_user.id

    if target_user.is_bot:
        await update.message.reply_text("🤖 Bot ကို warn မလုပ်နိုင်ပါ။")
        return

    count = add_warn(chat_id, user_id)

    await update.message.reply_text(
        f"⚠️ <b>သတိပေး အမှတ် {count}/{MAX_WARNS}</b>\n"
        f"👤 {target_user.mention_html()} ကို သတိပေးလိုက်ပါပြီ။",
        parse_mode=ParseMode.HTML,
    )

    if count >= MAX_WARNS:
        try:
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⛔ {target_user.mention_html()} ကို အမှတ်ပြည့်သဖြင့် Ban လုပ်လိုက်ပါပြီ။",
                parse_mode=ParseMode.HTML,
            )
            reset_warns(chat_id, user_id)
        except Exception as e:
            logger.error(f"Auto-ban failed: {e}")

async def warns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.from_user:
        await update.message.reply_text("👀 Warn အမှတ်ကြည့်ချင်တဲ့ user ကို reply လုပ်ပြီး သုံးပါ။")
        return

    target_user = reply_msg.from_user
    chat_id = update.effective_chat.id
    count = get_warn_count(chat_id, target_user.id)

    await update.message.reply_text(
        f"📊 {target_user.mention_html()} ရဲ့ သတိပေး အမှတ်: <b>{count}/{MAX_WARNS}</b>",
        parse_mode=ParseMode.HTML,
    )

async def resetwarns_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("❌ Admin များသာ သုံးခွင့်ရှိပါတယ်။")
        return

    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.from_user:
        await update.message.reply_text("🗑️ Warn ရှင်းချင်တဲ့ user ကို reply လုပ်ပြီး သုံးပါ။")
        return

    target_user = reply_msg.from_user
    chat_id = update.effective_chat.id
    reset_warns(chat_id, target_user.id)

    await update.message.reply_text(
        f"✅ {target_user.mention_html()} ရဲ့ သတိပေး အမှတ်များကို ရှင်းလိုက်ပါပြီ။",
        parse_mode=ParseMode.HTML,
    )

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("❌ Admin များသာ သုံးခွင့်ရှိပါတယ်။")
        return

    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.from_user:
        await update.message.reply_text("🔇 Mute လုပ်ချင်တဲ့ message ကို reply လုပ်ပြီး သုံးပါ။")
        return

    target_user = reply_msg.from_user
    chat_id = update.effective_chat.id
    user_id = target_user.id

    if target_user.is_bot:
        await update.message.reply_text("🤖 Bot ကို mute မလုပ်နိုင်ပါ။")
        return

    hours = 1
    if context.args:
        try:
            hours = int(context.args[0])
            hours = max(1, min(hours, 168))
        except:
            pass

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions={"can_send_messages": False},
            until_date=timedelta(hours=hours),
        )
        await update.message.reply_text(
            f"🔇 {target_user.mention_html()} ကို <b>{hours} နာရီ</b> mute လုပ်လိုက်ပါပြီ။",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text("❌ Mute လုပ်မရပါ။ Bot ကို admin အခွင့်အရေး ပေးပါ။")
        logger.error(f"Mute failed: {e}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("❌ Admin များသာ သုံးခွင့်ရှိပါတယ်။")
        return

    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.from_user:
        await update.message.reply_text("🔊 Unmute လုပ်ချင်တဲ့ message ကို reply လုပ်ပြီး သုံးပါ။")
        return

    target_user = reply_msg.from_user
    chat_id = update.effective_chat.id
    user_id = target_user.id

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_polls": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True,
            },
        )
        await update.message.reply_text(
            f"🔊 {target_user.mention_html()} ကို unmute လုပ်ပြီး စကားပြောခွင့် ပြန်ပေးလိုက်ပါပြီ။",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text("❌ Unmute လုပ်မရပါ။")
        logger.error(f"Unmute failed: {e}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("❌ Admin များသာ သုံးခွင့်ရှိပါတယ်။")
        return

    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.from_user:
        await update.message.reply_text("⛔ Ban လုပ်ချင်တဲ့ message ကို reply လုပ်ပြီး သုံးပါ။")
        return

    target_user = reply_msg.from_user
    chat_id = update.effective_chat.id
    user_id = target_user.id

    if target_user.is_bot:
        await update.message.reply_text("🤖 Bot ကို Ban မလုပ်နိုင်ပါ။")
        return

    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await update.message.reply_text(
            f"⛔ {target_user.mention_html()} ကို အဖွဲ့ကနေ ဖယ်ရှားလိုက်ပါပြီ။",
            parse_mode=ParseMode.HTML,
        )
        reset_warns(chat_id, user_id)
    except Exception as e:
        await update.message.reply_text("❌ Ban လုပ်မရပါ။ Bot ကို Ban users ခွင့်ပြုပါ။")
        logger.error(f"Ban failed: {e}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("❌ Admin များသာ သုံးခွင့်ရှိပါတယ်။")
        return

    reply_msg = update.message.reply_to_message
    if not reply_msg or not reply_msg.from_user:
        await update.message.reply_text("✅ Unban လုပ်ချင်တဲ့ message ကို reply လုပ်ပြီး သုံးပါ။")
        return

    target_user = reply_msg.from_user
    chat_id = update.effective_chat.id
    user_id = target_user.id

    try:
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id, only_if_banned=True)
        await update.message.reply_text(
            f"✅ {target_user.mention_html()} ကို Unban လုပ်ပြီး ပြန်ဝင်ခွင့်ပေးလိုက်ပါပြီ။",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text("❌ Unban လုပ်မရပါ (သို့မဟုတ် မူလကတည်းက Ban မထားပါ)။")
        logger.error(f"Unban failed: {e}")

# Clean service messages
async def clean_service_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members or update.message.left_chat_member:
        try:
            await update.message.delete()
        except:
            pass

# Error handler
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception while handling an update:", exc_info=context.error)

# Private /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    keyboard = [
        [InlineKeyboardButton("📚 အကြောင်းအရာ", callback_data="about"),
         InlineKeyboardButton("❓ အကူအညီ", callback_data="help")],
        [InlineKeyboardButton("🌐 ဝက်ဘ်ဆိုက်", url="https://example.com"),
         InlineKeyboardButton("📞 ဆက်သွယ်ရန်", callback_data="contact")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 မင်္ဂလာပါ!\n\nGroup Management Bot ပါ။",
        reply_markup=reply_markup,
    )

# Main
def main():
    init_db()
    logger.info("Bot starting...")

    application = Application.builder().token(BOT_TOKEN).build()

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
    application.add_handler(ChatMemberHandler(greet_new_member, chat_member_types=ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, clean_service_messages))

    application.add_error_handler(error_handler)

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET_TOKEN,
    )

if __name__ == "__main__":
    main()