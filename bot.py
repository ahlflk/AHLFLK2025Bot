import os
import logging
import asyncio
import sqlite3
from datetime import datetime
from dateutil.parser import parse as parse_date

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ChatMemberHandler,
    MessageHandler,
    filters,
    ConversationHandler,
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
CHANNEL_ID = "@AHLFLK2025channel"  # သင့် channel username
CHATBOT_LOGO_URL = "https://raw.githubusercontent.com/ahlflk/AHLFLK2025Bot/refs/heads/main/chatbot_logo.png"  # သင့် ပုံ raw URL

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

# Welcome with Photo + Buttons
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

    keyboard = [
        [InlineKeyboardButton("📜 စည်းမျဉ်းများ", callback_data="rules")],
        [InlineKeyboardButton("❓ အကူအညီ", callback_data="help")],
        [InlineKeyboardButton("🌐 ဝက်ဘ်ဆိုက်", url="https://example.com")],
    ]
    if chat.username:
        keyboard.append([InlineKeyboardButton("👥 အဖွဲ့ link", url=f"https://t.me/{chat.username}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    caption = (
        f"👋 မင်္ဂလာပါ {user.mention_html()}!\n\n"
        f"🎉 <b>{chat.title}</b> မှ\n\n"
        f"နွေးထွေးစွာ ကြိုဆိုပါတယ်။\n\n"
    )

    sent = await context.bot.send_photo(
        chat_id=chat.id,
        photo=CHATBOT_LOGO_URL,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
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
            "/mute [နာရီ] - Mute\n/unmute - Unmute\n/ban - Ban\n/unban - Unban\n/rules - စည်းမျဉ်း\n"
            "/post - Channel ထဲ ကြိုတင်တင်ရန်\n\nအားလုံး reply လုပ်ပြီး သုံးပါ။"
        )
    elif data == "contact":
        text = "📞 <b>ဆက်သွယ်ရန်</b>\n\n👉 @AHLFLK2025"
    elif data == "rules":
        text = (
            "📜 <b>အဖွဲ့ စည်းမျဉ်း</b>\n\n"
            "1. ယဉ်ကျေးစွာ ဆက်ဆံပါ\n"
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
            "1. ယဉ်ကျေးစွာ ဆက်ဆံပါ\n"
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
                text=f"⛔ {target_user.mention_html()} ကို အမှတ်ပြည့်သဖြင့် ban လုပ်လိုက်ပါပြီ။",
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
        await update.message.reply_text("🤖 Bot ကို ban မလုပ်နိုင်ပါ။")
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
            f"✅ {target_user.mention_html()} ကို unban လုပ်ပြီး ပြန်ဝင်ခွင့်ပေးလိုက်ပါပြီ။",
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await update.message.reply_text("❌ Unban လုပ်မရပါ (သို့မဟုတ် မူလကတည်းက ban မထားပါ)။")
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

# /post Conversation States
WAITING_PHOTO, WAITING_CAPTION, WAITING_BUTTONS, WAITING_TIME, WAITING_FILE = range(5)

pending_posts = {}

async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("Private chat မှာသာ သုံးပါ။")
        return ConversationHandler.END

    pending_posts[update.effective_user.id] = {}
    await update.message.reply_text("📸 Channel ထဲ တင်ချင်တဲ့ ပုံကို အရင်ပို့ပါ။")
    return WAITING_PHOTO

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_file = update.message.photo[-1].file_id
    pending_posts[user_id]["photo"] = photo_file

    await update.message.reply_text("✍️ Caption ရေးပို့ပါ။ (မလိုရင် /skip)")
    return WAITING_CAPTION

async def receive_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.text == "/skip":
        pending_posts[user_id]["caption"] = ""
    else:
        pending_posts[user_id]["caption"] = update.message.text_html

    await update.message.reply_text("🔘 Buttons ထည့်ချင်ရင် အောက်ပါ format နဲ့ ရေးပါ။\nText1 | url1\nText2 | url2\n\nမလိုရင် /skip")
    return WAITING_BUTTONS

async def receive_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.text == "/skip":
        pending_posts[user_id]["buttons"] = []
    else:
        lines = update.message.text.strip().split("\n")
        buttons = []
        for line in lines:
            if "|" in line:
                text, url = line.split("|", 1)
                buttons.append([InlineKeyboardButton(text.strip(), url=url.strip())])
        pending_posts[user_id]["buttons"] = buttons

    await update.message.reply_text("📅 တင်ချင်တဲ့ အချိန်ကို ရေးပါ။ (ဥပမာ: tomorrow 6:00 သို့မဟုတ် 2025-12-25 06:00 သို့မဟုတ် now)")
    return WAITING_TIME

async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    time_text = update.message.text.strip().lower()

    if time_text == "now":
        post_time = datetime.now()
    else:
        try:
            post_time = parse_date(time_text)
        except:
            await update.message.reply_text("❌ အချိန် မမှန်ပါ။ ထပ်ကြိုးစားပါ။")
            return WAITING_TIME

    pending_posts[user_id]["time"] = post_time

    await update.message.reply_text("📄 File ထည့်ချင်ရင် ပို့ပါ။ မလိုရင် /skip")
    return WAITING_FILE

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.message.document:
        pending_posts[user_id]["file"] = update.message.document.file_id
    else:
        pending_posts[user_id]["file"] = None

    data = pending_posts.pop(user_id)

    delay = (data["time"] - datetime.now()).total_seconds()
    if delay < 0:
        delay = 0

    context.job_queue.run_once(
        send_scheduled_post,
        when=delay,
        data=data,
        name=f"post_{user_id}"
    )

    await update.message.reply_text(f"✅ Post ကို {data['time'].strftime('%Y-%m-%d %H:%M')} မှာ တင်ရန် စီစဉ်ပြီးပါပြီ။")
    return ConversationHandler.END

async def skip_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await receive_file(update, context)

async def cancel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pending_posts.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ ရပ်လိုက်ပါပြီ။")
    return ConversationHandler.END

async def send_scheduled_post(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data

    keyboard = InlineKeyboardMarkup(data.get("buttons", [])) if data.get("buttons") else None

    try:
        await context.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=data["photo"],
            caption=data.get("caption", ""),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )

        if data.get("file"):
            await context.bot.send_document(
                chat_id=CHANNEL_ID,
                document=data["file"],
            )
    except Exception as e:
        logger.error(f"Scheduled post failed: {e}")

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
        "👋 မင်္ဂလာပါ!\n\n",
        reply_markup=reply_markup,
    )

# Main
def main():
    init_db()
    logger.info("Bot starting...")

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
    application.add_handler(ChatMemberHandler(greet_new_member, chat_member_types=ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, clean_service_messages))

    # /post conversation
    post_conv = ConversationHandler(
        entry_points=[CommandHandler("post", post_command)],
        states={
            WAITING_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            WAITING_CAPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_caption), CommandHandler("skip", receive_caption)],
            WAITING_BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_buttons), CommandHandler("skip", receive_buttons)],
            WAITING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)],
            WAITING_FILE: [MessageHandler(filters.Document.ALL, receive_file), CommandHandler("skip", skip_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel_post)],
    )
    application.add_handler(post_conv)

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
    