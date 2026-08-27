"""
Mahliyo Telegram bot.
Ishga tushirish: python -m bot.bot
"""
import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.config import settings
from app.database import SessionLocal
from app import models
from bot.keyboards import shop_keyboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
last_start_messages = {}


def is_admin(user_id: int) -> bool:
    db = SessionLocal()
    try:
        return db.query(models.Admin).filter(models.Admin.telegram_user_id == user_id).first() is not None
    finally:
        db.close()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    previous_message_id = last_start_messages.get(message.chat.id)
    if previous_message_id:
        try:
            await bot.delete_message(message.chat.id, previous_message_id)
        except Exception:
            pass
    text = (
        "👗🌹 <b>Mahliyo</b> — ayollar kiyimi va parfyumeriya do'koniga xush kelibsiz!\n\n"
        "Quyidagi tugma orqali do'konni oching."
    )
    sent_message = await message.answer(text, reply_markup=shop_keyboard(settings.WEBAPP_URL), parse_mode="HTML")
    last_start_messages[message.chat.id] = sent_message.message_id


async def main():
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan")

    if settings.USE_WEBHOOK:
        if not settings.WEBAPP_URL:
            raise RuntimeError("USE_WEBHOOK=true bo'lsa WEBAPP_URL kerak")
        webhook_url = settings.WEBAPP_URL.rstrip("/") + "/telegram/webhook"
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(
            webhook_url,
            secret_token=settings.WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
        logger.info("Bot webhook rejimida ishga tushdi: %s", webhook_url)
        return

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot polling rejimida ishga tushdi; avvalgi webhook o'chirildi.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
