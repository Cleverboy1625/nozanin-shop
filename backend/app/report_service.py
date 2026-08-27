from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import func
import httpx
from . import models
from .config import settings, get_product_chat_ids
from pathlib import Path


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


def _brand_banner_path():
    path = Path(__file__).resolve().parents[2] / "frontend" / "product-images" / "mahliyo-banner.jpg"
    return path if path.is_file() else None


def send_brand_banner(chat_id) -> bool:
    if not settings.BOT_TOKEN:
        return False
    caption = (
        "🌸 <b>Mahliyo</b> 🌸\n\n"
        "Ayollar kiyimi va nafis parfyumeriya do'koni.\n"
        "Yangi uslub, yangi kayfiyat.\n\n"
        "🛍 Sevimli mahsulotingizni tanlang va buyurtma bering."
    )
    payload = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    banner_path = _brand_banner_path()
    try:
        if banner_path:
            with banner_path.open("rb") as image:
                response = httpx.post(
                    f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendPhoto",
                    data=payload,
                    files={"photo": (banner_path.name, image, "image/jpeg")},
                    timeout=20,
                )
        elif settings.BRAND_BANNER_URL:
            payload["photo"] = settings.BRAND_BANNER_URL
            response = httpx.post(
                f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendPhoto",
                json=payload,
                timeout=20,
            )
        else:
            return send_telegram_message(chat_id, caption.replace("<b>", "").replace("</b>", ""))
        return response.status_code == 200
    except httpx.HTTPError:
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
    stock_text = ", ".join(f"{variant.label}: {variant.stock_qty} dona" for variant in product.variants)
    stock_display = stock_text or "Ko'rsatilmagan"
    caption = (
        f"🛍 Yangi mahsulot\n\n"
        f"{product.name}\n"
        f"{product.description or ''}\n\n"
        f"💰 Narx: {money(min(prices))} - {money(max(prices))}\n"
        f"🎨 Ranglar: {colors_text}\n"
        f"📏 O'lchamlar: {variants_text}\n\n"
        f"📦 Zaxira: {stock_display}\n\n"
        f"Buyurtma berish uchun do'konni oching."
    )
    sent = 0
    base_url = settings.WEBAPP_URL.rstrip("/")
    image_url = f"{base_url}{product.image_url}" if product.image_url and product.image_url.startswith("/") else product.image_url
    for chat_id in chat_ids:
        try:
            local_image = None
            if product.image_url and product.image_url.startswith("/"):
                local_image = Path(__file__).resolve().parents[2] / "frontend" / product.image_url.lstrip("/")
            if local_image and local_image.is_file():
                with local_image.open("rb") as image:
                    response = httpx.post(
                        f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendPhoto",
                        data={"chat_id": chat_id, "caption": caption},
                        files={"photo": (local_image.name, image, "image/jpeg")},
                        timeout=20,
                    )
            elif image_url:
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


LOW_STOCK_THRESHOLD = 3


def notify_low_stock_admins(db: Session, low_stock_items):
    """Zaxira kamaygan variantlar ro'yxatini adminlarga Telegram orqali yuboradi."""
    if not low_stock_items:
        return
    lines = ["⚠️ Ombor zaxirasi kamaymoqda:\n"]
    seen = set()
    for item in low_stock_items:
        key = (item["product_name"], item["variant_label"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"• {item['product_name']} ({item['variant_label']}) — {item['stock_qty']} dona qoldi")
    text = "\n".join(lines)
    notify_admins(db, text)


def send_daily_report_to_admins(db: Session):
    report_day = datetime.now(ZoneInfo(settings.TIMEZONE)).date()
    report = build_daily_report(db, report_day)
    notify_admins(db, report["report_text"])
    return report
