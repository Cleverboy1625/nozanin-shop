from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import Base, engine, SessionLocal
from . import models
from .config import settings, get_admin_ids_from_env
from .report_service import send_daily_report_to_admins
from .routers import products, orders, stats, admins, favorites, promos, analytics, cart, notifications, loyalty, search, content
from bot.bot import bot, dp
from aiogram.types import Update
from seed_products import seed as seed_products

logger = logging.getLogger(__name__)
app = FastAPI(title="Mahliyo Shop API")

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
app.include_router(favorites.router)
app.include_router(promos.router)
app.include_router(analytics.router)
app.include_router(cart.router)
app.include_router(notifications.router)
app.include_router(loyalty.router)
app.include_router(search.router)
app.include_router(content.router)

scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)
_INITIALIZED = False


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


def seed_content():
    db = SessionLocal()
    try:
        defaults = [("Kiyimlar", "kiyim", "👗"), ("Parfyum", "parfyum", "🌸")]
        for name, slug, icon in defaults:
            if not db.query(models.Category).filter(models.Category.slug == slug).first():
                db.add(models.Category(name=name, slug=slug, icon=icon))
        if not db.query(models.HeroBanner).filter(models.HeroBanner.active == 1).first():
            db.add(models.HeroBanner(title="Yangi uslub, yangi kayfiyat", subtitle="Sevimli kiyim va iforlarni bir joydan tanlang."))
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
    global _INITIALIZED
    if _INITIALIZED:
        return

    Base.metadata.create_all(bind=engine)
    migrate_legacy_schema()
    seed_products()
    seed_admins()
    seed_content()
    if not scheduler.running:
        scheduler.add_job(
            scheduled_daily_report,
            CronTrigger(hour=settings.DAILY_REPORT_HOUR, minute=settings.DAILY_REPORT_MINUTE),
            id="daily_report",
            replace_existing=True,
        )
        scheduler.start()
    _INITIALIZED = True


def migrate_legacy_schema():
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(admins)")}
        if "role" not in columns:
            connection.exec_driver_sql("ALTER TABLE admins ADD COLUMN role VARCHAR NOT NULL DEFAULT 'admin'")


async def configure_telegram_webhook():
    if not settings.BOT_TOKEN:
        logger.warning("BOT_TOKEN sozlanmagan, Telegram webhook o'rnatilmadi")
        return
    if not settings.USE_WEBHOOK:
        logger.info("USE_WEBHOOK=false: Telegram webhook o'rnatilmadi; polling rejimi kutilmoqda")
        return
    webhook_url = f"{settings.WEBAPP_URL}/telegram/webhook"
    try:
        await bot.set_webhook(
            webhook_url,
            secret_token=settings.WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
        logger.info("Telegram webhook o'rnatildi: %s", webhook_url)
    except Exception:
        logger.exception("Telegram webhook o'rnatilmadi: %s", webhook_url)


@app.on_event("startup")
async def on_startup():
    initialize_app()
    await configure_telegram_webhook()


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
