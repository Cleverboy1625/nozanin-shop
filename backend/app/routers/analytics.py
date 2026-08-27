from sqlalchemy import func
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

EVENT_VIEW = "view"
EVENT_CART = "add_to_cart"


@router.post("/event")
def track_event(payload: schemas.AnalyticsEventIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if payload.event_type not in {EVENT_VIEW, EVENT_CART}:
        raise HTTPException(400, "Noto'g'ri event turi")
    if payload.product_id and not db.query(models.Product).get(payload.product_id):
        raise HTTPException(404, "Mahsulot topilmadi")
    db.add(models.AnalyticsEvent(
        telegram_user_id=user["id"],
        event_type=payload.event_type,
        product_id=payload.product_id,
    ))
    db.commit()
    return {"ok": True}


@router.get("/insights", response_model=schemas.AnalyticsInsightOut)
def insights(db: Session = Depends(get_db), admin=Depends(require_admin)):
    # Ko'p ko'rilgan mahsulotlar
    viewed = (
        db.query(
            models.AnalyticsEvent.product_id,
            models.Product.name,
            func.count(models.AnalyticsEvent.id).label("cnt"),
        )
        .join(models.Product, models.Product.id == models.AnalyticsEvent.product_id)
        .filter(models.AnalyticsEvent.event_type == EVENT_VIEW)
        .group_by(models.AnalyticsEvent.product_id, models.Product.name)
        .order_by(func.count(models.AnalyticsEvent.id).desc())
        .limit(10)
        .all()
    )
    most_viewed = [{"product_id": v[0], "name": v[1], "count": v[2]} for v in viewed]

    # Ko'p savatga qo'shilgan
    carted = (
        db.query(
            models.AnalyticsEvent.product_id,
            models.Product.name,
            func.count(models.AnalyticsEvent.id).label("cnt"),
        )
        .join(models.Product, models.Product.id == models.AnalyticsEvent.product_id)
        .filter(models.AnalyticsEvent.event_type == EVENT_CART)
        .group_by(models.AnalyticsEvent.product_id, models.Product.name)
        .order_by(func.count(models.AnalyticsEvent.id).desc())
        .limit(10)
        .all()
    )
    most_added = [{"product_id": c[0], "name": c[1], "count": c[2]} for c in carted]

    # Ko'p ko'rilgan, lekin sotib olinmagan (abandoned)
    ordered_product_names = {
        oi.product_name
        for o in db.query(models.Order).filter(models.Order.status != "bekor").all()
        for oi in o.items
    }
    abandoned = [v for v in most_viewed if v["name"] not in ordered_product_names][:10]

    total_views = db.query(func.count(models.AnalyticsEvent.id)).filter(
        models.AnalyticsEvent.event_type == EVENT_VIEW
    ).scalar() or 0
    total_add_to_cart = db.query(func.count(models.AnalyticsEvent.id)).filter(
        models.AnalyticsEvent.event_type == EVENT_CART
    ).scalar() or 0
    total_orders = db.query(models.Order).filter(models.Order.status != "bekor").count()
    conversion = round((total_orders / total_add_to_cart) * 100, 1) if total_add_to_cart else 0

    return {
        "most_viewed": most_viewed,
        "most_added_to_cart": most_added,
        "most_abandoned": abandoned,
        "total_views": total_views,
        "total_add_to_cart": total_add_to_cart,
        "total_orders": total_orders,
        "conversion_rate": conversion,
    }
