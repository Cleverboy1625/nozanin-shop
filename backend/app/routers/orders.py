from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin, require_staff, get_current_user
from ..config import is_configured_admin
from ..report_service import money, send_telegram_message, notify_admins, notify_low_stock_admins, LOW_STOCK_THRESHOLD
from .promos import calculate_discount

router = APIRouter(prefix="/api/orders", tags=["orders"])

STATUS_LABELS = {
    "yangi": "Yangi",
    "tayyor": "Tayyorlanmoqda",
    "yolda": "Yo'lda",
    "yetkazildi": "Yetkazildi",
    "bekor": "Bekor qilindi",
}


def _is_staff(db: Session, telegram_user_id: int) -> bool:
    return is_configured_admin(telegram_user_id) or db.query(models.Admin).filter(
        models.Admin.telegram_user_id == telegram_user_id
    ).first() is not None


def _order_dict(order):
    return {
        "id": order.id,
        "telegram_user_id": order.telegram_user_id,
        "customer_name": order.customer_name,
        "customer_phone": order.customer_phone,
        "customer_address": order.customer_address,
        "delivery_date": order.delivery_date,
        "note": order.note,
        "total": order.total,
        "status": order.status,
        "created_at": order.created_at,
        "items": order.items,
        "status_events": order.status_events,
        "promo_code": order.promotion.code if order.promotion else None,
        "discount_amount": order.promotion.discount_amount if order.promotion else 0,
    }


@router.post("", response_model=schemas.OrderOut)
def create_order(payload: schemas.OrderIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(400, "Savat bo'sh")

    order_items = []
    total = 0
    low_stock_items = []
    for it in payload.items:
        variant = db.query(models.Variant).options(joinedload(models.Variant.product)).get(it.variant_id)
        if not variant:
            raise HTTPException(400, f"Variant topilmadi: {it.variant_id}")
        if it.qty <= 0:
            raise HTTPException(400, "Miqdor noto'g'ri")
        if variant.stock_qty < it.qty:
            raise HTTPException(400, f"'{variant.product.name}' ({variant.label}) uchun yetarli zaxira yo'q")
        was_above = variant.stock_qty > LOW_STOCK_THRESHOLD
        variant.stock_qty -= it.qty
        if was_above and variant.stock_qty <= LOW_STOCK_THRESHOLD:
            low_stock_items.append({
                "product_name": variant.product.name,
                "variant_label": variant.label,
                "stock_qty": variant.stock_qty,
            })
        total += variant.price * it.qty
        order_items.append(models.OrderItem(
            variant_id=variant.id, product_name=variant.product.name,
            variant_label=variant.label, color=variant.color,
            price=variant.price, qty=it.qty,
        ))

    # Promo kod qo'llash
    promo = None
    discount_amount = 0
    promo_code_text = None
    if payload.promo_code:
        promo = db.query(models.PromoCode).filter(models.PromoCode.code == payload.promo_code.strip()).first()
        if not promo or not promo.active:
            raise HTTPException(400, "Promo kod topilmadi yoki faol emas")
        if promo.usage_limit is not None and promo.used_count >= promo.usage_limit:
            raise HTTPException(400, "Promo kod limiti tugagan")
        if promo.expires_at and promo.expires_at < datetime.utcnow():
            raise HTTPException(400, "Promo kod muddati tugagan")
        if total < promo.min_order_total:
            raise HTTPException(400, f"Minimal buyurtma summasi {promo.min_order_total:,} so'm")
        discount_amount = calculate_discount(promo, total)
        promo.used_count += 1
        promo_code_text = promo.code

    final_total = max(0, total - discount_amount)

    order = models.Order(
        telegram_user_id=user["id"],
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_address=payload.customer_address,
        delivery_date=payload.delivery_date,
        note=payload.note,
        total=final_total,
        status="yangi",
        items=order_items,
    )
    db.add(order)
    db.flush()

    db.add(models.OrderStatusEvent(order_id=order.id, status="yangi", note="Buyurtma qabul qilindi"))

    if promo_code_text:
        db.add(models.OrderPromotion(
            order_id=order.id, code=promo_code_text, discount_amount=discount_amount,
        ))

    db.commit()
    db.refresh(order)

    items_text = "\n".join(f"• {i.product_name} ({i.variant_label}) × {i.qty} — {money(i.price*i.qty)}" for i in order.items)
    discount_text = f"\nChegirma: -{money(discount_amount)}" if discount_amount else ""
    admin_text = (
        f"🛍 Yangi buyurtma!\n\n"
        f"№ {order.id[:8]}\n"
        f"Mijoz: {order.customer_name}\n"
        f"Telefon: {order.customer_phone}\n"
        f"Manzil: {order.customer_address}\n"
        f"Yetkazish sanasi: {order.delivery_date}\n\n"
        f"{items_text}\n"
        f"Asosiy summa: {money(total)}\n"
        f"Chegirma: -{money(discount_amount)}\n\n"
        f"Jami: {money(order.total)}"
    )
    notify_admins(db, admin_text)
    notify_low_stock_admins(db, low_stock_items)
    send_telegram_message(
        user["id"],
        f"✅ Buyurtmangiz qabul qilindi!\n"
        f"Buyurtma raqami: {order.id[:8]}\n"
        f"Yetkazish sanasi: {order.delivery_date}\n"
        f"Summa: {money(order.total)}"
        + (f"\nChegirma: -{money(discount_amount)}" if discount_amount else "")
    )

    return _order_dict(order)


@router.get("", response_model=List[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db), admin=Depends(require_staff)):
    orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.items), joinedload(models.Order.status_events), joinedload(models.Order.promotion))
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return [_order_dict(o) for o in orders]


@router.get("/my", response_model=List[schemas.OrderOut])
def my_orders(db: Session = Depends(get_db), user=Depends(get_current_user)):
    orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.items), joinedload(models.Order.status_events), joinedload(models.Order.promotion))
        .filter(models.Order.telegram_user_id == user["id"])
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return [_order_dict(o) for o in orders]


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items), joinedload(models.Order.status_events), joinedload(models.Order.promotion))
        .filter(models.Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(404, "Buyurtma topilmadi")
    if order.telegram_user_id != user["id"] and not _is_staff(db, user["id"]):
        raise HTTPException(403, "Bu buyurtma sizga tegishli emas")
    return _order_dict(order)


@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
def update_status(order_id: str, payload: schemas.StatusUpdate, db: Session = Depends(get_db), admin=Depends(require_staff)):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(404, "Buyurtma topilmadi")
    if payload.status not in STATUS_LABELS:
        raise HTTPException(400, "Noto'g'ri holat")
    if payload.status == "bekor":
        raise HTTPException(400, "Bekor qilish uchun buyurtmani bekor qilish tugmasidan foydalaning")
    order.status = payload.status
    db.add(models.OrderStatusEvent(order_id=order.id, status=payload.status))
    db.commit()
    db.refresh(order)

    send_telegram_message(
        order.telegram_user_id,
        f"ℹ️ Buyurtmangiz holati o'zgardi: {order.id[:8]}\nYangi holat: {STATUS_LABELS[order.status]}"
    )
    return _order_dict(order)


@router.post("/{order_id}/cancel", response_model=schemas.OrderOut)
def cancel_order(order_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(models.Order).options(joinedload(models.Order.items)).get(order_id)
    if not order:
        raise HTTPException(404, "Buyurtma topilmadi")
    is_staff = _is_staff(db, user["id"])
    if order.telegram_user_id != user["id"] and not is_staff:
        raise HTTPException(403, "Bu buyurtmani bekor qilish huquqi yo'q")
    if order.status in {"bekor", "yetkazildi"}:
        raise HTTPException(400, "Bu buyurtmani bekor qilib bo'lmaydi")
    if datetime.utcnow() - order.created_at > timedelta(hours=6):
        raise HTTPException(400, "Buyurtmani faqat 6 soat ichida bekor qilish mumkin")
    for item in order.items:
        if item.variant_id:
            variant = db.query(models.Variant).get(item.variant_id)
            if variant:
                variant.stock_qty += item.qty
    if order.promotion:
        promo = db.query(models.PromoCode).filter(models.PromoCode.code == order.promotion.code).first()
        if promo and promo.used_count > 0:
            promo.used_count -= 1
    order.status = "bekor"
    db.add(models.OrderStatusEvent(order_id=order.id, status="bekor", note="Buyurtma bekor qilindi"))
    db.commit()
    db.refresh(order)
    send_telegram_message(order.telegram_user_id, f"Buyurtma bekor qilindi: {order.id[:8]}")
    return _order_dict(order)
