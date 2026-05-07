import os
import sqlite3
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes, CallbackQueryHandler
from PIL import Image

# ================== 🔴 حط التوكن هنا ==================
TOKEN = "8707716224:AAEa83H05X7JtA0D5WgKzicPtmSaPtiQYjA"

# ================== 🔴 حط يوزر القناة ==================
CHANNEL_USERNAME = "@Ah_m_e09d"

# ================== 🔴 حط رابط القناة ==================
CHANNEL_LINK = "https://t.me/Ah_m_e09d"

# ================== قاعدة البيانات ==================
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")
conn.commit()

# ================== متغيرات ==================
user_images = {}
user_state = {}
user_mode = {}
user_filename = {}
user_last_message = {}

# ================== التحقق من الاشتراك ==================
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================== start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not await is_subscribed(user_id, context):
        keyboard = [
            [InlineKeyboardButton("📢 انضم للقناة", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ تحقق", callback_data="check")]
        ]

        await update.message.reply_text(
            "🚫 لازم تشترك في القناة الأول",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    await update.message.reply_text(
        "🔥 أهلا بيك\nاضغط لبدء التحويل",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 ابدأ", callback_data="start_convert")]
        ])
    )

# ================== زر التحقق ==================
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if await is_subscribed(user_id, context):
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

        await query.edit_message_text("✅ تم التحقق! اضغط /start")
    else:
        await query.answer("❌ لسه مش مشترك", show_alert=True)

# ================== الأزرار ==================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "start_convert":
        user_state[user_id] = "upload"
        user_images[user_id] = []

        await query.edit_message_text("📥 ابعت الصور")

    elif query.data == "convert":
        if not user_images.get(user_id):
            await query.answer("❌ مفيش صور", show_alert=True)
            return

        user_state[user_id] = "size"

        await query.message.reply_text(
            "📐 اختر الحجم",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("طبيعي", callback_data="normal"),
                 InlineKeyboardButton("A4", callback_data="fit")]
            ])
        )

    elif query.data in ["normal", "fit"]:
        user_mode[user_id] = query.data
        user_state[user_id] = "ask_name"

        await query.message.reply_text(
            "📝 تغيير الاسم؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("نعم", callback_data="yes"),
                 InlineKeyboardButton("لا", callback_data="no")]
            ])
        )

    elif query.data == "yes":
        user_state[user_id] = "waiting_name"
        await query.message.reply_text("✍️ اكتب الاسم")

    elif query.data == "no":
        user_filename[user_id] = str(user_id)
        await convert(user_id, query.message.chat_id, context)

# ================== استقبال الصور ==================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_state.get(user_id) != "upload":
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    if not os.path.exists("images"):
        os.makedirs("images")

    path = f"images/{user_id}_{len(user_images.get(user_id, []))}.jpg"
    await file.download_to_drive(path)

    user_images.setdefault(user_id, []).append(path)

    if user_last_message.get(user_id):
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=user_last_message[user_id]
            )
        except:
            pass

    msg = await update.message.reply_text(
        f"📸 عدد الصور: {len(user_images[user_id])}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 تحويل الصور", callback_data="convert")]
        ])
    )

    user_last_message[user_id] = msg.message_id

# ================== استقبال الاسم ==================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_state.get(user_id) == "waiting_name":
        user_filename[user_id] = update.message.text.strip()
        await update.message.reply_text("⏳ جاري التحويل...")
        await convert(user_id, update.effective_chat.id, context)

# ================== التحويل ==================
async def convert(user_id, chat_id, context):
    images = []

    for p in user_images[user_id]:
        img = Image.open(p).convert("RGB")

        if user_mode.get(user_id) == "fit":
            img = img.resize((1240, 1754))

        images.append(img)

    filename = user_filename.get(user_id, f"{user_id}")
    pdf_path = f"{filename}.pdf"

    images[0].save(pdf_path, save_all=True, append_images=images[1:])

    await context.bot.send_document(chat_id=chat_id, document=open(pdf_path, "rb"))

    # تنظيف
    for p in user_images[user_id]:
        os.remove(p)

    user_images[user_id] = []
    os.remove(pdf_path)

    # 👇 الرسالة الجديدة بعد التحويل
    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ تم تحويل الصور إلى PDF",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحويل صور تاني", callback_data="start_convert")]
        ])
    )

# ================== تشغيل ==================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(check, pattern="check"))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print("🔥 البوت شغال 100%")

app.run_polling()
