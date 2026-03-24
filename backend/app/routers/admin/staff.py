from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.admin import AdminUser
from ...models.staff import Staff, StaffMenuSettings
from ...core.auth import get_current_admin, require_store_access
from ...core.exceptions import NotFoundError
from ...schemas.staff import (
    StaffCreateRequest, StaffUpdateRequest,
    StaffMenuSettingsUpdateRequest, StaffResponse,
)

router = APIRouter(prefix="/admin/stores/{store_id}", tags=["admin-staff"])


@router.get("/staff")
async def list_staff(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    staff_list = db.query(Staff).filter(
        Staff.store_id == store_id,
    ).order_by(Staff.sort_order, Staff.name).all()
    return [StaffResponse.model_validate(s) for s in staff_list]


@router.post("/staff")
async def create_staff(
    store_id: str,
    req: StaffCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    staff = Staff(store_id=store_id, **req.model_dump())
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return StaffResponse.model_validate(staff)


@router.put("/staff/{staff_id}")
async def update_staff(
    store_id: str,
    staff_id: str,
    req: StaffUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    staff = db.query(Staff).filter(Staff.id == staff_id, Staff.store_id == store_id).first()
    if not staff:
        raise NotFoundError("Staff", staff_id)

    for key, value in req.model_dump(exclude_none=True).items():
        setattr(staff, key, value)

    db.commit()
    db.refresh(staff)
    return StaffResponse.model_validate(staff)


@router.delete("/staff/{staff_id}")
async def delete_staff(
    store_id: str,
    staff_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    staff = db.query(Staff).filter(Staff.id == staff_id, Staff.store_id == store_id).first()
    if not staff:
        raise NotFoundError("Staff", staff_id)

    staff.is_active = False  # 論理削除
    db.commit()
    return {"success": True}


@router.get("/staff/{staff_id}/menus")
async def get_staff_menus(
    store_id: str,
    staff_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    settings = db.query(StaffMenuSettings).filter(
        StaffMenuSettings.staff_id == staff_id,
    ).all()
    return [
        {
            "menu_id": s.menu_id,
            "is_available": s.is_available,
            "custom_duration_minutes": s.custom_duration_minutes,
        }
        for s in settings
    ]


@router.put("/staff/{staff_id}/menus")
async def update_staff_menus(
    store_id: str,
    staff_id: str,
    req: StaffMenuSettingsUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    staff = db.query(Staff).filter(Staff.id == staff_id, Staff.store_id == store_id).first()
    if not staff:
        raise NotFoundError("Staff", staff_id)

    # 既存設定を削除して再作成（シンプルなアップサート）
    db.query(StaffMenuSettings).filter(StaffMenuSettings.staff_id == staff_id).delete()

    for item in req.settings:
        sms = StaffMenuSettings(
            staff_id=staff_id,
            menu_id=item.menu_id,
            is_available=item.is_available,
            custom_duration_minutes=item.custom_duration_minutes,
        )
        db.add(sms)

    db.commit()
    return {"success": True, "count": len(req.settings)}
