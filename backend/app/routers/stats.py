from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import schemas
from ..database import get_db
from ..deps import require_admin
from ..report_service import build_daily_report, send_daily_report_to_admins

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/today", response_model=schemas.StatsOut)
def stats_today(db: Session = Depends(get_db), admin=Depends(require_admin)):
    return build_daily_report(db, date.today())


@router.post("/send-report")
def send_report_now(db: Session = Depends(get_db), admin=Depends(require_admin)):
    report = send_daily_report_to_admins(db)
    return {"ok": True, "report": report}
