from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from ...database import get_db
from ...models.admin import AdminUser
from ...models.reservation import Reservation
from ...models.log import CalendarSyncLog
from ...core.auth import get_current_admin, require_store_access
from ...services.google_calendar_service import get_oauth_url, exchange_code_for_token
from ...config import settings

router = APIRouter(prefix="/admin", tags=["admin-calendar"])


@router.get("/stores/{store_id}/calendar")
async def get_calendar_events(
    store_id: str,
    date_from: str = Query(...),
    date_to: str = Query(...),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """カレンダー表示用: 指定期間の予約一覧をFullCalendar形式で返す"""
    require_store_access(store_id, admin, db)

    reservations = db.query(Reservation).filter(
        Reservation.store_id == store_id,
        Reservation.status.notin_(["cancelled"]),
        Reservation.start_datetime >= datetime.fromisoformat(date_from),
        Reservation.start_datetime <= datetime.fromisoformat(date_to),
    ).all()

    STATUS_COLORS = {
        "pending": "#f59e0b",
        "confirmed": "#3b82f6",
        "completed": "#10b981",
        "no_show": "#ef4444",
    }

    events = []
    for r in reservations:
        color = STATUS_COLORS.get(r.status, "#6b7280")
        title = f"{r.customer.name or '顧客'} / {r.menu.name if r.menu else ''}"
        if r.staff:
            title = f"{r.staff.name}: {title}"

        events.append({
            "id": r.id,
            "title": title,
            "start": r.start_datetime.isoformat(),
            "end": r.end_datetime.isoformat(),
            "color": color,
            "extendedProps": {
                "status": r.status,
                "customer_name": r.customer.name if r.customer else None,
                "staff_name": r.staff.name if r.staff else None,
                "menu_name": r.menu.name if r.menu else None,
                "confirmation_code": r.confirmation_code,
            },
        })

    return events


@router.get("/stores/{store_id}/google/auth-url")
async def get_google_auth_url(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    url = get_oauth_url(
        client_id=settings.google_client_id,
        redirect_uri=settings.google_redirect_uri,
        scopes=settings.google_scopes_list,
        state=store_id,  # コールバック時のstore_id特定に使用
    )
    return {"auth_url": url}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,  # store_id
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from ...models.store import Store
    store = db.query(Store).filter(Store.id == state).first()
    if not store or store.tenant_id != admin.tenant_id:
        from ...core.exceptions import ForbiddenError
        raise ForbiddenError()

    token_data = exchange_code_for_token(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scopes=settings.google_scopes_list,
        code=code,
    )

    if not token_data:
        return {"success": False, "error": "Token exchange failed"}

    store.google_refresh_token = token_data["refresh_token"]
    db.commit()
    return {"success": True}


@router.get("/stores/{store_id}/sync-logs")
async def get_sync_logs(
    store_id: str,
    limit: int = Query(20, le=100),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    logs = db.query(CalendarSyncLog).filter(
        CalendarSyncLog.store_id == store_id,
    ).order_by(CalendarSyncLog.started_at.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "sync_type": l.sync_type,
            "direction": l.direction,
            "status": l.status,
            "events_processed": l.events_processed,
            "error_message": l.error_message,
            "started_at": l.started_at,
            "completed_at": l.completed_at,
        }
        for l in logs
    ]
