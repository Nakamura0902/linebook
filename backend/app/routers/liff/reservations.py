from __future__ import annotations
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from ...database import get_db
from ...models.store import Store
from ...models.customer import Customer
from ...models.reservation import Reservation
from ...models.menu import Menu
from ...models.staff import Staff
from ...core.auth import get_line_user_id
from ...core.exceptions import NotFoundError, ForbiddenError
from ...schemas.reservation import (
    ReservationCreateRequest, ReservationUpdateRequest,
    ReservationCancelRequest, ReservationResponse,
)
from ...services.reservation_service import create_reservation, update_reservation, cancel_reservation
from ...services.notification_service import send_notification

router = APIRouter(prefix="/liff", tags=["liff-reservations"])


def _build_response(r: Reservation) -> ReservationResponse:
    resp = ReservationResponse.model_validate(r)
    if r.staff:
        resp.staff_name = r.staff.name
    if r.menu:
        resp.menu_name = r.menu.name
    if r.customer:
        resp.customer_name = r.customer.name
    return resp


@router.get("/stores/{store_id}")
async def get_store_info(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise NotFoundError("Store", store_id)
    return {
        "id": store.id,
        "name": store.name,
        "phone": store.phone,
        "address": store.address,
        "industry_type": store.industry_type,
    }


@router.get("/stores/{store_id}/menus")
async def get_menus(store_id: str, db: Session = Depends(get_db)):
    from ...models.menu import MenuCategory
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise NotFoundError("Store", store_id)

    menus = db.query(Menu).filter(
        Menu.store_id == store_id, Menu.is_active == True
    ).order_by(Menu.sort_order).all()

    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "duration_minutes": m.duration_minutes,
            "price": m.price,
            "category_id": m.category_id,
            "category_name": m.category.name if m.category else None,
            "is_first_visit_only": m.is_first_visit_only,
            "is_revisit_only": m.is_revisit_only,
        }
        for m in menus
    ]


@router.get("/stores/{store_id}/staff")
async def get_staff(store_id: str, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise NotFoundError("Store", store_id)

    staff_list = db.query(Staff).filter(
        Staff.store_id == store_id,
        Staff.is_active == True,
        Staff.is_assignable == True,
    ).order_by(Staff.sort_order).all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "role": s.role,
            "gender": s.gender,
            "bio": s.bio,
            "image_url": s.image_url,
        }
        for s in staff_list
    ]


@router.post("/reservations")
async def create_reservation_liff(
    store_id: str,
    req: ReservationCreateRequest,
    background_tasks: BackgroundTasks,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise NotFoundError("Store", store_id)

    # 顧客取得（LINE userIdで識別）
    customer = db.query(Customer).filter(
        Customer.store_id == store_id,
        Customer.line_user_id == line_user_id,
    ).first()

    if not customer:
        customer = Customer(
            store_id=store_id,
            line_user_id=line_user_id,
            name=req.customer_name,
            phone=req.customer_phone,
            email=req.customer_email,
            name_kana=req.customer_name_kana,
            is_first_visit=True,
        )
        db.add(customer)
        db.flush()
    else:
        # 既存顧客: 入力された情報で上書き更新（任意）
        if req.customer_name:
            customer.name = req.customer_name
        if req.customer_phone:
            customer.phone = req.customer_phone

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
        actor_type="customer",
        actor_id=line_user_id,
    )

    background_tasks.add_task(send_notification, db, reservation, "booking_confirmed", store)

    return _build_response(reservation)


@router.get("/customers/{customer_id}/reservations")
async def get_my_reservations(
    customer_id: str,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundError("Customer", customer_id)
    if customer.line_user_id != line_user_id:
        raise ForbiddenError()

    reservations = db.query(Reservation).options(
        joinedload(Reservation.staff),
        joinedload(Reservation.menu),
    ).filter(
        Reservation.customer_id == customer_id,
        Reservation.status.notin_(["cancelled"]),
    ).order_by(Reservation.start_datetime.desc()).limit(10).all()

    return [_build_response(r) for r in reservations]


@router.get("/reservations/{reservation_id}")
async def get_reservation_liff(
    reservation_id: str,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    r = db.query(Reservation).options(
        joinedload(Reservation.staff),
        joinedload(Reservation.menu),
        joinedload(Reservation.customer),
    ).filter(Reservation.id == reservation_id).first()

    if not r:
        raise NotFoundError("Reservation", reservation_id)
    if r.customer.line_user_id != line_user_id:
        raise ForbiddenError()

    return _build_response(r)


@router.put("/reservations/{reservation_id}")
async def update_reservation_liff(
    reservation_id: str,
    req: ReservationUpdateRequest,
    background_tasks: BackgroundTasks,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    r = db.query(Reservation).options(
        joinedload(Reservation.customer),
        joinedload(Reservation.store),
    ).filter(Reservation.id == reservation_id).first()

    if not r:
        raise NotFoundError("Reservation", reservation_id)
    if r.customer.line_user_id != line_user_id:
        raise ForbiddenError()

    updated = update_reservation(
        db=db,
        reservation=r,
        new_start_datetime=req.start_datetime,
        new_staff_id=req.staff_id,
        new_notes=req.notes,
        actor_type="customer",
        actor_id=line_user_id,
    )

    background_tasks.add_task(send_notification, db, updated, "booking_changed", r.store)
    return _build_response(updated)


@router.delete("/reservations/{reservation_id}")
async def cancel_reservation_liff(
    reservation_id: str,
    req: ReservationCancelRequest,
    background_tasks: BackgroundTasks,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    r = db.query(Reservation).options(
        joinedload(Reservation.customer),
        joinedload(Reservation.store),
    ).filter(Reservation.id == reservation_id).first()

    if not r:
        raise NotFoundError("Reservation", reservation_id)
    if r.customer.line_user_id != line_user_id:
        raise ForbiddenError()

    cancelled = cancel_reservation(
        db=db,
        reservation=r,
        reason=req.reason,
        actor_type="customer",
        actor_id=line_user_id,
    )

    background_tasks.add_task(send_notification, db, cancelled, "booking_cancelled", r.store)
    return _build_response(cancelled)
