from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import Base, engine, SessionLocal
from . import models
from .config import settings, get_admin_ids_from_env
from .report_service import send_daily_report_to_admins
from .routers import products, orders, stats, admins
from bot.bot import bot, dp
from aiogram.types import Update

app = FastAPI(title="Nozanin Shop API")

origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()] if settings.CORS_ORIGINS != "*" else ["*"]
if not origins:
    origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router)
app.include_router(orders.router)
app.include_router(stats.router)
app.include_router(admins.router)

scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)


def seed_admins():
    db = SessionLocal()
    try:
        for tid in get_admin_ids_from_env():
            exists = db.query(models.Admin).filter(models.Admin.telegram_user_id == tid).first()
            if not exists:
                db.add(models.Admin(telegram_user_id=tid, full_name=None))
        db.commit()
    finally:
        db.close()


def scheduled_daily_report():
    db = SessionLocal()
    try:
        send_daily_report_to_admins(db)
    finally:
        db.close()


def initialize_app():
    Base.metadata.create_all(bind=engine)
    seed_admins()
    if not scheduler.running:
        scheduler.add_job(
            scheduled_daily_report,
            CronTrigger(hour=settings.DAILY_REPORT_HOUR, minute=settings.DAILY_REPORT_MINUTE),
            id="daily_report",
            replace_existing=True,
        )
        scheduler.start()


@app.on_event("startup")
def on_startup():
    initialize_app()


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown(wait=False)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
):
    if settings.WEBHOOK_SECRET and x_telegram_bot_api_secret_token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Webhook secret noto'g'ri")
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}


frontend_candidates = (
    Path(__file__).resolve().parents[1] / "frontend",
    Path(__file__).resolve().parents[2] / "frontend",
)
frontend_dir = next((path for path in frontend_candidates if path.is_dir()), None)
if frontend_dir:
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

initialize_app()
