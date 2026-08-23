from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import func
import httpx
from . import models
from .config import settings, get_product_chat_ids


def money(n: int) -> str:
    return f"{n:,}".replace(",", " ") + " so'm"


def build_daily_report(db: Session, day: date) -> dict:
    local_timezone = ZoneInfo(settings.TIMEZONE)
    local_start = datetime.combine(day, datetime.min.time(), tzinfo=local_timezone)
    start = local_start.astimezone(timezone.utc).replace(tzinfo=None)
    end = (local_start + timedelta(days=1)).astimezone(timezone.utc).replace(tzinfo=None)

    orders = (
        db.query(models.Order)
        .filter(models.Order.created_at >= start, models.Order.created_at < end)
        .filter(models.Order.status != "bekor")
        .all()
    )
    orders_count = len(orders)
    revenue = sum(o.total for o in orders)

    tally = {}
    items_sold = 0
    for o in orders:
        for it in o.items:
            items_sold += it.qty
            tally[it.product_name] = tally.get(it.product_name, 0) + it.qty
    top = sorted(tally.items(), key=lambda x: x[1], reverse=True)[:3]

    lines = [
        f"📊 Kunlik hisobot — {day.isoformat()}",
        "",
        f"Buyurtmalar soni: {orders_count} ta",
        f"Umumiy tushum: {money(revenue)}",
        f"Sotilgan mahsulotlar: {items_sold} dona",
        "",
        "Top mahsulotlar:",
    ]
    if top:
        for i, (name, qty) in enumerate(top, 1):
            lines.append(f"{i}. {name} — {qty} dona")
    else:
        lines.append("Bugun sotuv bo'lmadi")

    report_text = "\n".join(lines)
    return {
        "date": day.isoformat(),
        "orders_count": orders_count,
        "revenue": revenue,
        "items_sold": items_sold,
        "top_products": [{"name": n, "qty": q} for n, q in top],
        "report_text": report_text,
    }


def send_telegram_message(chat_id, text: str) -> bool:
    if not settings.BOT_TOKEN:
        return False
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    try:
        r = httpx.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def send_product_post(product) -> int:
    """Publish a newly added product to all configured channel/group chats."""
    chat_ids = get_product_chat_ids()
    if not chat_ids or not settings.BOT_TOKEN:
        return 0

    prices = [variant.price for variant in product.variants]
    variants = sorted({variant.label for variant in product.variants})
    colors = sorted({"Oq" if variant.color == "#ffffff" else "Ko'k" if variant.color == "#2563eb" else variant.color for variant in product.variants if variant.color})
    colors_text = ", ".join(colors) or "Ko'rsatilmagan"
    variants_text = ", ".join(variants) or "Ko'rsatilmagan"
    caption = (
        f"🛍 Yangi mahsulot\n\n"
        f"{product.name}\n"
        f"{product.description or ''}\n\n"
        f"💰 Narx: {money(min(prices))} - {money(max(prices))}\n"
        f"🎨 Ranglar: {colors_text}\n"
        f"📏 O'lchamlar: {variants_text}\n\n"
        f"Buyurtma berish uchun do'konni oching."
    )
    sent = 0
    base_url = settings.WEBAPP_URL.rstrip("/")
    image_url = f"{base_url}{product.image_url}" if product.image_url and product.image_url.startswith("/") else product.image_url
    for chat_id in chat_ids:
        try:
            if image_url:
                response = httpx.post(
                    f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendPhoto",
                    json={"chat_id": chat_id, "photo": image_url, "caption": caption},
                    timeout=15,
                )
            else:
                response = httpx.post(
                    f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
                    json={"chat_id": chat_id, "text": caption},
                    timeout=15,
                )
            if response.status_code == 200:
                sent += 1
        except httpx.HTTPError:
            continue
    return sent


def notify_admins(db: Session, text: str):
    admins = db.query(models.Admin).all()
    for a in admins:
        send_telegram_message(a.telegram_user_id, text)


def send_daily_report_to_admins(db: Session):
    report_day = datetime.now(ZoneInfo(settings.TIMEZONE)).date()
    report = build_daily_report(db, report_day)
    notify_admins(db, report["report_text"])
    return report
