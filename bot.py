import os
import logging
import asyncio
import subprocess
import tempfile
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# === SOZLAMALAR ===
BOT_TOKEN = "8959863283:AAGUuTKE3yAEAC_sra906HN3-GeIiT_9jPI"
ADMIN_ID = 5454545177

# Qidirilayotgan so'zlar (katta-kichik harfga e'tibor bermasdan)
SEARCH_WORDS = ["розметов", "розметовга", "rozmetov", "rozmetovga"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def ocr_with_tesseract(image_bytes: bytes) -> str:
    """Tesseract OCR orqali rasmdan matn olish (BEPUL)"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
            tmp_img.write(image_bytes)
            tmp_img_path = tmp_img.name

        result = subprocess.run(
            ["tesseract", tmp_img_path, "stdout", "-l", "rus+eng", "--oem", "3", "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=30
        )
        os.unlink(tmp_img_path)
        return result.stdout
    except Exception as e:
        logger.error(f"Tesseract xato: {e}")
        return ""


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhga kelgan har bir rasmni tekshiradi"""
    message = update.message
    if not message or not message.photo:
        return

    chat_title = message.chat.title or message.chat.username or str(message.chat.id)
    sender = message.from_user.full_name if message.from_user else "Noma'lum"

    logger.info(f"Rasm keldi: {chat_title} dan, yuborgan: {sender}")

    # Eng katta o'lchamdagi rasmni olish
    photo = message.photo[-1]
    photo_file = await photo.get_file()
    image_bytes = await photo_file.download_as_bytearray()

    try:
        # OCR qilish
        extracted_text = await ocr_with_tesseract(bytes(image_bytes))
        logger.info(f"OCR natijasi: {extracted_text[:200]}")

        # So'z qidirish
        text_lower = extracted_text.lower()
        found_words = [w for w in SEARCH_WORDS if w in text_lower]

        if found_words:
            alert_text = (
                f"🔔 *РОЗМЕТОВ nakладной topildi!*\n\n"
                f"📍 Guruh: {chat_title}\n"
                f"👤 Yuborgan: {sender}\n"
                f"🔑 Topilgan so'z: {', '.join(found_words)}\n\n"
                f"📄 Matn:\n`{extracted_text[:500]}`"
            )

            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=alert_text,
                parse_mode="Markdown"
            )
            await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            logger.info(f"Admin ga xabar yuborildi! So'z: {found_words}")
        else:
            logger.info("Розметов topilmadi, o'tkazib yuborildi")

    except Exception as e:
        logger.error(f"Xato: {e}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot ishga tushdi!\n"
        "Men guruhga kelgan barcha rasmlarni tekshiraman.\n"
        "Rozmetov deb yozilgan nakладной topilsa, adminga xabar beraman."
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, handle_photo))
    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
