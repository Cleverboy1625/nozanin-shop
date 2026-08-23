from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import require_admin, get_current_user
from ..report_service import money, send_telegram_message, notify_admins

router = APIRouter(prefix="/api/orders", tags=["orders"])

STATUS_LABELS = {
    "yangi": "Yangi",
    "tayyor": "Tayyorlanmoqda",
    "yolda": "Yo'lda",
    "yetkazildi": "Yetkazildi",
    "bekor": "Bekor qilindi",
}


@router.post("", response_model=schemas.OrderOut)
def create_order(payload: schemas.OrderIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not payload.items:
        raise HTTPException(400, "Savat bo'sh")

    order_items = []
    total = 0
    for it in payload.items:
        variant = db.query(models.Variant).get(it.variant_id)
        if not variant:
            raise HTTPException(400, f"Variant topilmadi: {it.variant_id}")
        if it.qty <= 0:
            raise HTTPException(400, "Miqdor noto'g'ri")
        if variant.stock_qty < it.qty:
            raise HTTPException(400, f"'{variant.product.name}' ({variant.label}) uchun yetarli zaxira yo'q")
        variant.stock_qty -= it.qty
        total += variant.price * it.qty
        order_items.append(models.OrderItem(
            variant_id=variant.id, product_name=variant.product.name,
            variant_label=variant.label, color=variant.color,
            price=variant.price, qty=it.qty,
        ))

    order = models.Order(
        telegram_user_id=user["id"],
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        customer_address=payload.customer_address,
        delivery_date=payload.delivery_date,
        note=payload.note,
        total=total,
        status="yangi",
        items=order_items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    items_text = "\n".join(f"• {i.product_name} ({i.variant_label}) × {i.qty} — {money(i.price*i.qty)}" for i in order.items)
    admin_text = (
        f"🛍 Yangi buyurtma!\n\n"
        f"№ {order.id[:8]}\n"
        f"Mijoz: {order.customer_name}\n"
        f"Telefon: {order.customer_phone}\n"
        f"Manzil: {order.customer_address}\n"
        f"Yetkazish sanasi: {order.delivery_date}\n\n"
        f"{items_text}\n\n"
        f"Jami: {money(order.total)}"
    )
    notify_admins(db, admin_text)
    send_telegram_message(user["id"], f"✅ Buyurtmangiz qabul qilindi!\nBuyurtma raqami: {order.id[:8]}\nYetkazish sanasi: {order.delivery_date}\nSumma: {money(order.total)}")

    return order


@router.get("", response_model=List[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()


@router.get("/my", response_model=List[schemas.OrderOut])
def my_orders(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return (
        db.query(models.Order)
        .filter(models.Order.telegram_user_id == user["id"])
        .order_by(models.Order.created_at.desc())
        .all()
    )


@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
def update_status(order_id: str, payload: schemas.StatusUpdate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    order = db.query(models.Order).get(order_id)
    if not order:
        raise HTTPException(404, "Buyurtma topilmadi")
    if payload.status not in STATUS_LABELS:
        raise HTTPException(400, "Noto'g'ri holat")
    order.status = payload.status
    db.commit()
    db.refresh(order)

    send_telegram_message(
        order.telegram_user_id,
        f"ℹ️ Buyurtmangiz holati o'zgardi: {order.id[:8]}\nYangi holat: {STATUS_LABELS[order.status]}"
    )
    return order
