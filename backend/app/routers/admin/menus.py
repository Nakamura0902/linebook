from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.admin import AdminUser
from ...models.menu import Menu, MenuCategory
from ...core.auth import get_current_admin, require_store_access
from ...core.exceptions import NotFoundError
from ...schemas.menu import (
    MenuCreateRequest, MenuUpdateRequest, MenuResponse,
    MenuCategoryCreateRequest,
)

router = APIRouter(prefix="/admin/stores/{store_id}", tags=["admin-menus"])


@router.get("/menu-categories")
async def list_categories(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    cats = db.query(MenuCategory).filter(
        MenuCategory.store_id == store_id, MenuCategory.is_active == True
    ).order_by(MenuCategory.sort_order).all()
    return [{"id": c.id, "name": c.name, "sort_order": c.sort_order} for c in cats]


@router.post("/menu-categories")
async def create_category(
    store_id: str,
    req: MenuCategoryCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    cat = MenuCategory(store_id=store_id, **req.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name}


@router.get("/menus")
async def list_menus(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    menus = db.query(Menu).filter(Menu.store_id == store_id).order_by(Menu.sort_order).all()

    result = []
    for m in menus:
        r = MenuResponse.model_validate(m)
        if m.category:
            r.category_name = m.category.name
        result.append(r)
    return result


@router.post("/menus")
async def create_menu(
    store_id: str,
    req: MenuCreateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    menu = Menu(store_id=store_id, **req.model_dump())
    db.add(menu)
    db.commit()
    db.refresh(menu)
    return MenuResponse.model_validate(menu)


@router.put("/menus/{menu_id}")
async def update_menu(
    store_id: str,
    menu_id: str,
    req: MenuUpdateRequest,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    menu = db.query(Menu).filter(Menu.id == menu_id, Menu.store_id == store_id).first()
    if not menu:
        raise NotFoundError("Menu", menu_id)

    for key, value in req.model_dump(exclude_none=True).items():
        setattr(menu, key, value)

    db.commit()
    db.refresh(menu)
    return MenuResponse.model_validate(menu)


@router.delete("/menus/{menu_id}")
async def delete_menu(
    store_id: str,
    menu_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    menu = db.query(Menu).filter(Menu.id == menu_id, Menu.store_id == store_id).first()
    if not menu:
        raise NotFoundError("Menu", menu_id)

    menu.is_active = False  # 論理削除
    db.commit()
    return {"success": True}
