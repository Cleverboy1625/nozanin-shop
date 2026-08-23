"""
Nozanin Telegram bot.
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


def is_admin(user_id: int) -> bool:
    db = SessionLocal()
    try:
        return db.query(models.Admin).filter(models.Admin.telegram_user_id == user_id).first() is not None
    finally:
        db.close()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    admin = is_admin(message.from_user.id)
    text = (
        "👗🌹 <b>Nozanin</b> — ayollar kiyimi va parfyumeriya do'koniga xush kelibsiz!\n\n"
        "Quyidagi tugma orqali do'konni oching."
    )
    if admin:
        text += "\n\nSiz administrator sifatida ro'yxatdan o'tgansiz — do'kon ichida \"Sotuvchi\" bo'limi avtomatik ko'rinadi."
    await message.answer(text, reply_markup=shop_keyboard(settings.WEBAPP_URL), parse_mode="HTML")


async def main():
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan")
    logger.info("Bot ishga tushdi (polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
