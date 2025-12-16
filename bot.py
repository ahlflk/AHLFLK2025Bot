import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, ChatMemberHandler, filters

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables (Render မှာ ထည့်ထားရမည်)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set!")

PUBLIC_URL = os.getenv("PUBLIC_URL")  # ဥပမာ: https://your-bot.onrender.com (slash မပါ)
if not PUBLIC_URL:
    raise RuntimeError("PUBLIC_URL is not set!")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{PUBLIC_URL}{WEBHOOK_PATH}"
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET", "my-super-secret-token")

PORT = int(os.getenv("PORT", 10000))

# ========================
# Handlers
# ========================

# /start command (private chat မှာပဲ အလုပ်လုပ်မယ်)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📚 အကြောင်းအရာ", callback_data='about'),
            InlineKeyboardButton("❓ အကူအညီ", callback_data='help'),
        ],
        [
            InlineKeyboardButton("🌐 ဝက်ဘ်ဆိုက်", url='https://example.com'),  # လိုချင်တဲ့ link ပြောင်းပါ
            InlineKeyboardButton("📞 ဆက်သွယ်ရန်", callback_data='contact'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 မင်္ဂလာပါ!\n\n",
        reply_markup=reply_markup
    )

# Group ထဲ အဖွဲ့ဝင်အသစ် ဝင်လာရင် ကြိုဆိုမယ်
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_chat_member = update.chat_member.new_chat_member

    # အသစ်ဝင်လာတာ သေချာအောင် စစ်ဆေးခြင်း
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
            text="👋 မင်္ဂလာပါ!\n"
        )
    elif query.data == 'help':
        await query.edit_message_text(
            text="❓ အကူအညီလိုအပ်ရင်:\n"
                 "- /start နှိပ်ပါ\n"
                 "- Admin ကို တိုက်ရိုက် ဆက်သွယ်ပါ:\n"
                 "_ 👉 @AHLFLK2025\n"
        )
    elif query.data == 'contact':
        await query.edit_message_text(
            text="📞 ဆက်သွယ်ရန်:\n"
                 "👉 @AHLFLK2025\n"
                 "သို့မဟုတ် email: example@gmail.com"
        )
    elif query.data == 'rules':
        await query.edit_message_text(
            text="📜 <b>အဖွဲ့ စည်းမျဉ်း</b>\n\n"
                 "1. ယဉ်ကျေးစွာ ဆက်ဆံပါ\n"
                 "2. Spam၊ Ads မလုပ်ပါနဲ့\n"
                 "3. အဖွဲ့နဲ့ မဆိုင်တဲ့ အကြောင်းအရာများ မမျှဝေပါနဲ့\n\n"
                 "စည်းမျဉ်း ချိုးဖောက်ရင် ဖယ်ရှားပါမယ်။",
            parse_mode='HTML'
        )

# အခြား text message တွေကို echo ပြန်ပို့မယ်
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        await update.message.reply_text(f"သင်ပို့တာ → {update.message.text}")

# ========================
# Main Function
# ========================

def main():
    logger.info("Building application...")
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers ထည့်ခြင်း
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(ChatMemberHandler(greet_new_member, chat_member_types=ChatMemberHandler.CHAT_MEMBER))

    logger.info("Setting up webhook: %s", WEBHOOK_URL)

    # Webhook စတင်ခြင်း
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET_TOKEN,
    )

if __name__ == "__main__":
    main()