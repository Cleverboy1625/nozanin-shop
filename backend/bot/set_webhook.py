import asyncio
import sys

from aiogram import Bot

from app.config import settings


async def main():
    if len(sys.argv) != 2:
        raise SystemExit("Foydalanish: python -m bot.set_webhook https://domain/telegram/webhook")
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan")
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        await bot.set_webhook(
            sys.argv[1],
            secret_token=settings.WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
    finally:
        await bot.session.close()
    print("Telegram webhook o'rnatildi")


if __name__ == "__main__":
    asyncio.run(main())