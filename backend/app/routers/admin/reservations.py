from __future__ import annotations
from fastapi import APIRouter, Depends, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone
from typing import Optional

from ...database import get_db
from ...models.admin import AdminUser
from ...models.reservation import Reservation
from ...models.customer import Customer
from ...core.auth import get_current_admin, require_store_access
from ...core.exceptions import NotFoundError, ForbiddenError
from ...schemas.reservation import (
    ReservationResponse, AdminReservationCreateRequest,
    ReservationUpdateRequest, ReservationCancelRequest,
)
from ...services.reservation_service import create_reservation, update_reservation, cancel_reservation
from ...services.notification_service import send_notification

router = APIRouter(prefix="/admin/stores/{store_id}/reservations", tags=["admin-reservations"])


def _check_reservation_belongs_to_store(reservation: Reservation, store_id: str):
    if reservation.store_id != store_id:
        raise ForbiddenError()


def _build_response(r: Reservation) -> ReservationResponse:
    resp = ReservationResponse.model_validate(r)
    if r.staff:
        resp.staff_name = r.staff.name
    if r.menu:
        resp.menu_name = r.menu.name
    if r.customer:
        resp.customer_name = r.customer.name
    return resp


@router.get("")
async def list_reservations(
    store_id: str,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    staff_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = require_store_access(store_id, admin, db)

    query = db.query(Reservation).options(
        joinedload(Reservation.staff),
        joinedload(Reservation.menu),
        joinedload(Reservation.customer),
    ).filter(Reservation.store_id == store_id)

    if date_from:
        query = query.filter(Reservation.start_datetime >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Reservation.start_datetime <= datetime.fromisoformat(date_to))
    if staff_id:
        query = query.filter(Reservation.staff_id == staff_id)
    if status:
        query = query.filter(Reservation.status == status)

    total = query.count()
    reservations = query.order_by(Reservation.start_datetime.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [_build_response(r) for r in reservations],
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": (page * limit) < total,
    }


@router.post("")
async def create_proxy_reservation(
    store_id: str,
    req: AdminReservationCreateRequest,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = require_store_access(store_id, admin, db)

    # 顧客取得or作成
    if req.customer_id:
        customer = db.query(Customer).filter(Customer.id == req.customer_id, Customer.store_id == store_id).first()
        if not customer:
            raise NotFoundError("Customer", req.customer_id)
    else:
        # 新規顧客作成（電話代理登録）
        customer = Customer(
            store_id=store_id,
            name=req.customer_name,
            phone=req.customer_phone,
            email=req.customer_email,
            is_first_visit=req.is_first_visit if req.is_first_visit is not None else True,
        )
        db.add(customer)
        db.flush()

    reservation = create_reservation(
        db=db,
        store=store,
        customer=customer,
        menu_id=req.menu_id,
        start_datetime=req.start_datetime,
        staff_id=req.staff_id,
        notes=req.notes,
        is_first_visit=req.is_first_visit,
        extra_data=req.extra_data,
        actor_type="admin",
        actor_id=admin.id,
        is_proxy=True,
        proxy_registered_by=admin.id,
    )

    if req.staff_notes:
        reservation.staff_notes = req.staff_notes
        db.commit()

    background_tasks.add_task(send_notification, db, reservation, "booking_confirmed", store)

    return _build_response(reservation)


@router.get("/{reservation_id}")
async def get_reservation(
    store_id: str,
    reservation_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = require_store_access(store_id, admin, db)
    r = db.query(Reservation).options(
        joinedload(Reservation.staff),
        joinedload(Reservation.menu),
        joinedload(Reservation.customer),
        joinedload(Reservation.history),
    ).filter(Reservation.id == reservation_id).first()

    if not r:
        raise NotFoundError("Reservation", reservation_id)
    _check_reservation_belongs_to_store(r, store_id)
    return _build_response(r)


@router.put("/{reservation_id}")
async def update_reservation_endpoint(
    store_id: str,
    reservation_id: str,
    req: ReservationUpdateRequest,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = require_store_access(store_id, admin, db)
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise NotFoundError("Reservation", reservation_id)
    _check_reservation_belongs_to_store(r, store_id)

    updated = update_reservation(
        db=db,
        reservation=r,
        new_start_datetime=req.start_datetime,
        new_staff_id=req.staff_id,
        new_notes=req.notes,
        actor_type="admin",
        actor_id=admin.id,
    )

    background_tasks.add_task(send_notification, db, updated, "booking_changed", store)
    return _build_response(updated)


@router.delete("/{reservation_id}")
async def cancel_reservation_endpoint(
    store_id: str,
    reservation_id: str,
    req: ReservationCancelRequest,
    background_tasks: BackgroundTasks,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    store = require_store_access(store_id, admin, db)
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise NotFoundError("Reservation", reservation_id)
    _check_reservation_belongs_to_store(r, store_id)

    cancelled = cancel_reservation(
        db=db,
        reservation=r,
        reason=req.reason,
        actor_type="admin",
        actor_id=admin.id,
    )

    background_tasks.add_task(send_notification, db, cancelled, "booking_cancelled", store)
    return _build_response(cancelled)


@router.patch("/{reservation_id}/status")
async def update_status(
    store_id: str,
    reservation_id: str,
    new_status: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """ステータスを直接変更（承認/完了/無断キャンセルマーク）"""
    ALLOWED_STATUSES = {"confirmed", "completed", "no_show", "pending"}
    if new_status not in ALLOWED_STATUSES:
        from ...core.exceptions import ValidationError
        raise ValidationError(f"Invalid status: {new_status}")

    store = require_store_access(store_id, admin, db)
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise NotFoundError("Reservation", reservation_id)
    _check_reservation_belongs_to_store(r, store_id)

    if new_status == "no_show":
        customer = r.customer
        if customer:
            customer.no_show_count = (customer.no_show_count or 0) + 1

    r.status = new_status
    db.commit()
    db.refresh(r)
    return {"id": r.id, "status": r.status}
