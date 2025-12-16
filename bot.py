import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ChatMemberHandler

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

# ========================
# Handlers
# ========================

# Private chat မှာ /start ပဲ အလုပ်လုပ်မယ်
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Private chat မှာ ပဲ အလုပ်လုပ်မယ်
    if update.effective_chat.type != "private":
        return

    keyboard = [
        [
            InlineKeyboardButton("📚 အကြောင်းအရာ", callback_data='about'),
            InlineKeyboardButton("❓ အကူအညီ", callback_data='help'),
        ],
        [
            InlineKeyboardButton("🌐 ဝက်ဘ်ဆိုက်", url='https://example.com'),
            InlineKeyboardButton("📞 ဆက်သွယ်ရန်", callback_data='contact'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 မင်္ဂလာပါ!\n\n",
        reply_markup=reply_markup
    )

# Group/Supergroup ထဲ အဖွဲ့ဝင်အသစ် ဝင်လာရင် ကြိုဆိုမယ်
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_chat_member = update.chat_member.new_chat_member

    if (new_chat_member.status == "member" and 
        new_chat_member.old_chat_member.status in ["left", "kicked", None]):
        
        user = new_chat_member.user

        keyboard = [
            [
                InlineKeyboardButton("📜 စည်းမျဉ်းများ", callback_data='rules'),
                InlineKeyboardButton("👥 အဖွဲ့သားများ နှုတ်ဆက်ရန်", 
                    url=f"https://t.me/{update.effective_chat.username}" if update.effective_chat.username else "https://t.me"),
            ],
            [InlineKeyboardButton("❓ အကူအညီ", callback_data='help')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_text = (
            f"👋 မင်္ဂလာပါ! {user.mention_html()}!\n\n"
            f"🎉 <b>{update.effective_chat.title}</b> မှ\n\n"
            f"ကြိုဆိုပါတယ်။\n\n"
        )

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_text,
            parse_mode='HTML',
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

# Inline Button နှိပ်ရင် တုံ့ပြန်မယ်
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'about':
        await query.edit_message_text(
            text="🤖 <b>Bot အကြောင်း</b>\n\n"
                 "ဒီ Bot က Group Management နဲ့ Member အသစ်များကို အလိုအလျောက် ကြိုဆိုရန် အတွက် ဖန်တီးထားခြင်း ဖြစ်ပါတယ်။\n\n"
                 "👨‍💻 Developer: @AHLFLK2025",
            parse_mode='HTML'
        )
    elif query.data == 'help':
        await query.edit_message_text(
            text="❓ <b>အကူအညီ</b>\n\n"
                 "- /start ကို နှိပ်ပါ\n"
                 "❓ အကူအညီ လိုအပ်ပါက\n\n"
                 "👇 Admin ကို ဆက်သွယ်ရန်"
                 "👉 Admin: @AHLFLK2025",
            parse_mode='HTML'
        )
    elif query.data == 'contact':
        await query.edit_message_text(
            text="📞 <b>ဆက်သွယ်ရန်</b>\n\n"
                 "❓ အကူအညီ လိုအပ်ပါက\n\n"
                 "👇 Admin ကို ဆက်သွယ်ရန်"
                 "👉 Admin: @AHLFLK2025",
            parse_mode='HTML'
        )
    elif query.data == 'rules':
        await query.edit_message_text(
            text="📜 <b>အဖွဲ့ စည်းမျဉ်း</b>\n\n"
                 "1. ယဉ်ကျေးစွာ ဆက်ဆံပါ\n"
                 "2. Spam၊ Ads မလုပ်ပါနဲ့\n"
                 "3. အဖွဲ့နဲ့ မသက်ဆိုင်တဲ့ အကြောင်းအရာများ မမျှဝေပါနဲ့\n\n"
                 "စည်းမျဉ်းများ ချိုးဖောက်ပါက Group မှ ဖယ်ရှားပါမယ်။",
            parse_mode='HTML'
        )

# ========================
# Main Function
# ========================

def main():
    logger.info("Building application...")
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers ထည့်ခြင်း (echo ဖြုတ်လိုက်ပါပြီ)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(ChatMemberHandler(greet_new_member, chat_member_types=ChatMemberHandler.CHAT_MEMBER))

    logger.info("Setting up webhook: %s", WEBHOOK_URL)

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET_TOKEN,
    )

if __name__ == "__main__":
    main()