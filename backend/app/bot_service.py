"""Render uchun Telegram polling xizmati.

Render Web Service HTTP port tinglashini talab qiladi. Bu modul shu portda
health endpoint beradi va aiogram polling'ni ilovaning background task'i sifatida
ishlatadi. API xizmati va bot xizmati bitta PostgreSQL bazasini bo'lishadi.
"""
import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.config import settings
from bot.bot import bot, dp


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN Render environment variables'da berilmagan")

    # Polling va webhook bir vaqtda ishlamaydi. Oldingi webhook bo'lsa uni
    # o'chirib, yangi deploy'da bot polling orqali update qabul qilishini ta'minlaymiz.
    await bot.delete_webhook(drop_pending_updates=False)
    polling_task = asyncio.create_task(
        dp.start_polling(bot, handle_signals=False, close_bot_session=False)
    )
    try:
        yield
    finally:
        await dp.stop_polling()
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task
        await bot.session.close()


app = FastAPI(title="Nozanin Telegram Bot", lifespan=lifespan)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "bot"}
