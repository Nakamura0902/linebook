from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from ...database import get_db
from ...models.admin import AdminUser
from ...models.store import StoreSettings, BusinessHours, Holiday, ReservationBlock
from ...models.notification import CancellationPolicy, NotificationTemplate
from ...core.auth import get_current_admin, require_store_access
from ...core.exceptions import NotFoundError
from ...schemas.store import (
    StoreSettingsUpdateRequest, BusinessHoursUpdateRequest,
    HolidayCreateRequest, BlockCreateRequest,
    CancellationPolicyCreateRequest, NotificationTemplateUpdateRequest,
)

router = APIRouter(prefix="/admin/stores/{store_id}", tags=["admin-settings"])


# ──────────── 店舗設定 ────────────

@router.get("/settings")
async def get_settings(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = require_store_access(store_id, admin, db)
    s = store.settings
    if not s:
        return {}
    return {
        "booking_mode": s.booking_mode,
        "slot_duration_minutes": s.slot_duration_minutes,
        "advance_booking_days": s.advance_booking_days,
        "min_booking_hours": s.min_booking_hours,
        "reminder_enabled": s.reminder_enabled,
        "reminder_send_time": str(s.reminder_send_time) if s.reminder_send_time else None,
        "notify_admin_on_new": s.notify_admin_on_new,
        "notify_admin_on_cancel": s.notify_admin_on_cancel,
        "notify_admin_on_change": s.notify_admin_on_change,
        "industry_config": s.industry_config,
    }


@router.put("/settings")
async def update_settings(
    store_id: str,
    req: StoreSettingsUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = require_store_access(store_id, admin, db)
    s = store.settings
    if not s:
        s = StoreSettings(store_id=store_id)
        db.add(s)

    for key, value in req.model_dump(exclude_none=True).items():
        setattr(s, key, value)

    db.commit()
    return {"success": True}


# ──────────── 営業時間 ────────────

@router.get("/business-hours")
async def get_business_hours(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    hours = db.query(BusinessHours).filter(BusinessHours.store_id == store_id).order_by(BusinessHours.day_of_week).all()
    return [
        {
            "day_of_week": h.day_of_week,
            "is_open": h.is_open,
            "open_time": str(h.open_time) if h.open_time else None,
            "close_time": str(h.close_time) if h.close_time else None,
        }
        for h in hours
    ]


@router.put("/business-hours")
async def update_business_hours(
    store_id: str,
    req: BusinessHoursUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)

    for item in req.hours:
        bh = db.query(BusinessHours).filter(
            BusinessHours.store_id == store_id,
            BusinessHours.day_of_week == item.day_of_week,
        ).first()
        if bh:
            bh.is_open = item.is_open
            bh.open_time = item.open_time
            bh.close_time = item.close_time
        else:
            bh = BusinessHours(
                store_id=store_id,
                day_of_week=item.day_of_week,
                is_open=item.is_open,
                open_time=item.open_time,
                close_time=item.close_time,
            )
            db.add(bh)

    db.commit()
    return {"success": True}


# ──────────── 休業日 ────────────

@router.get("/holidays")
async def list_holidays(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    holidays = db.query(Holiday).filter(Holiday.store_id == store_id).order_by(Holiday.date).all()
    return [{"id": h.id, "date": h.date, "reason": h.reason} for h in holidays]


@router.post("/holidays")
async def create_holiday(
    store_id: str,
    req: HolidayCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    holiday = Holiday(store_id=store_id, date=req.date, reason=req.reason)
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return {"id": holiday.id, "date": holiday.date}


@router.delete("/holidays/{holiday_id}")
async def delete_holiday(
    store_id: str,
    holiday_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    h = db.query(Holiday).filter(Holiday.id == holiday_id, Holiday.store_id == store_id).first()
    if not h:
        raise NotFoundError("Holiday", holiday_id)
    db.delete(h)
    db.commit()
    return {"success": True}


# ──────────── 予約ブロック ────────────

@router.get("/blocks")
async def list_blocks(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    blocks = db.query(ReservationBlock).filter(ReservationBlock.store_id == store_id).all()
    return [
        {
            "id": b.id,
            "staff_id": b.staff_id,
            "start_datetime": b.start_datetime,
            "end_datetime": b.end_datetime,
            "reason": b.reason,
        }
        for b in blocks
    ]


@router.post("/blocks")
async def create_block(
    store_id: str,
    req: BlockCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    block = ReservationBlock(
        store_id=store_id,
        staff_id=req.staff_id,
        start_datetime=datetime.fromisoformat(req.start_datetime),
        end_datetime=datetime.fromisoformat(req.end_datetime),
        reason=req.reason,
        created_by=admin.id,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return {"id": block.id, "success": True}


@router.delete("/blocks/{block_id}")
async def delete_block(
    store_id: str,
    block_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    b = db.query(ReservationBlock).filter(ReservationBlock.id == block_id, ReservationBlock.store_id == store_id).first()
    if not b:
        raise NotFoundError("Block", block_id)
    db.delete(b)
    db.commit()
    return {"success": True}


# ──────────── キャンセルポリシー ────────────

@router.get("/cancellation-policies")
async def list_policies(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    policies = db.query(CancellationPolicy).filter(CancellationPolicy.store_id == store_id).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "is_default": p.is_default,
            "cancel_deadline_hours": p.cancel_deadline_hours,
            "same_day_cancel_allowed": p.same_day_cancel_allowed,
            "require_cancel_reason": p.require_cancel_reason,
            "description": p.description,
        }
        for p in policies
    ]


@router.post("/cancellation-policies")
async def create_policy(
    store_id: str,
    req: CancellationPolicyCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)

    if req.is_default:
        # 既存のデフォルトを解除
        db.query(CancellationPolicy).filter(
            CancellationPolicy.store_id == store_id,
            CancellationPolicy.is_default == True,
        ).update({"is_default": False})

    policy = CancellationPolicy(store_id=store_id, **req.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return {"id": policy.id, "name": policy.name}


# ──────────── 通知テンプレート ────────────

@router.get("/notification-templates")
async def list_templates(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    templates = db.query(NotificationTemplate).filter(NotificationTemplate.store_id == store_id).all()
    return [
        {
            "id": t.id,
            "type": t.type,
            "channel": t.channel,
            "body": t.body,
            "is_active": t.is_active,
        }
        for t in templates
    ]


@router.put("/notification-templates")
async def update_template(
    store_id: str,
    req: NotificationTemplateUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    tmpl = db.query(NotificationTemplate).filter(
        NotificationTemplate.store_id == store_id,
        NotificationTemplate.type == req.type,
        NotificationTemplate.channel == "line",
    ).first()

    if tmpl:
        tmpl.body = req.body
        tmpl.is_active = req.is_active
    else:
        tmpl = NotificationTemplate(
            store_id=store_id,
            type=req.type,
            channel="line",
            body=req.body,
            is_active=req.is_active,
        )
        db.add(tmpl)

    db.commit()
    return {"success": True}
