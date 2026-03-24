from __future__ import annotations
import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from ...database import get_db
from ...models.admin import AdminUser
from ...models.customer import Customer
from ...models.reservation import Reservation
from ...core.auth import get_current_admin, require_store_access
from ...core.exceptions import NotFoundError
from ...schemas.customer import CustomerUpdateRequest, BlacklistRequest, CustomerResponse

router = APIRouter(prefix="/admin/stores/{store_id}/customers", tags=["admin-customers"])


@router.get("")
async def list_customers(
    store_id: str,
    search: Optional[str] = Query(None),
    is_blacklisted: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)

    query = db.query(Customer).filter(Customer.store_id == store_id)

    if search:
        like = f"%{search}%"
        query = query.filter(
            Customer.name.ilike(like) |
            Customer.phone.ilike(like) |
            Customer.email.ilike(like)
        )
    if is_blacklisted is not None:
        query = query.filter(Customer.is_blacklisted == is_blacklisted)

    total = query.count()
    customers = query.order_by(Customer.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [CustomerResponse.model_validate(c) for c in customers],
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": (page * limit) < total,
    }


@router.get("/export")
async def export_csv(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    customers = db.query(Customer).filter(Customer.store_id == store_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "氏名", "ふりがな", "電話番号", "メール", "性別",
        "初回フラグ", "ブラックリスト", "来店回数", "最終来店日",
        "キャンセル回数", "無断キャンセル回数", "登録日",
    ])
    for c in customers:
        writer.writerow([
            c.id, c.name, c.name_kana, c.phone, c.email, c.gender,
            c.is_first_visit, c.is_blacklisted, c.visit_count,
            c.last_visit_at.isoformat() if c.last_visit_at else "",
            c.cancel_count, c.no_show_count,
            c.created_at.isoformat(),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@router.get("/{customer_id}")
async def get_customer(
    store_id: str,
    customer_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.store_id == store_id
    ).first()
    if not customer:
        raise NotFoundError("Customer", customer_id)

    reservations = db.query(Reservation).filter(
        Reservation.customer_id == customer_id,
    ).order_by(Reservation.start_datetime.desc()).limit(20).all()

    return {
        "customer": CustomerResponse.model_validate(customer),
        "recent_reservations": [
            {
                "id": r.id,
                "start_datetime": r.start_datetime,
                "status": r.status,
                "menu_name": r.menu.name if r.menu else None,
                "staff_name": r.staff.name if r.staff else None,
                "confirmation_code": r.confirmation_code,
            }
            for r in reservations
        ],
    }


@router.put("/{customer_id}")
async def update_customer(
    store_id: str,
    customer_id: str,
    req: CustomerUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.store_id == store_id
    ).first()
    if not customer:
        raise NotFoundError("Customer", customer_id)

    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.patch("/{customer_id}/blacklist")
async def update_blacklist(
    store_id: str,
    customer_id: str,
    req: BlacklistRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    customer = db.query(Customer).filter(
        Customer.id == customer_id, Customer.store_id == store_id
    ).first()
    if not customer:
        raise NotFoundError("Customer", customer_id)

    customer.is_blacklisted = req.is_blacklisted
    customer.blacklist_reason = req.reason if req.is_blacklisted else None
    db.commit()

    return {"id": customer.id, "is_blacklisted": customer.is_blacklisted}
