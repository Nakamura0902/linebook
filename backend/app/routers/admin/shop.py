from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.admin import AdminUser
from ...models.shop import ShopCategory, ShopProduct
from ...core.auth import get_current_admin, require_store_access
from ...core.exceptions import NotFoundError
from ...schemas.shop import ShopCategoryCreate, ShopProductCreate, ShopProductUpdate

router = APIRouter(prefix="/admin", tags=["admin-shop"])


# ─── カテゴリ ───

@router.get("/stores/{store_id}/shop/categories")
async def list_categories(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    cats = db.query(ShopCategory).filter(
        ShopCategory.store_id == store_id,
    ).order_by(ShopCategory.sort_order, ShopCategory.created_at).all()
    return [{"id": c.id, "name": c.name, "emoji": c.emoji, "sort_order": c.sort_order} for c in cats]


@router.post("/stores/{store_id}/shop/categories", status_code=201)
async def create_category(
    store_id: str,
    req: ShopCategoryCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    cat = ShopCategory(store_id=store_id, **req.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "emoji": cat.emoji}


@router.delete("/stores/{store_id}/shop/categories/{cat_id}", status_code=204)
async def delete_category(
    store_id: str,
    cat_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    cat = db.query(ShopCategory).filter(
        ShopCategory.id == cat_id, ShopCategory.store_id == store_id
    ).first()
    if not cat:
        raise NotFoundError("ShopCategory", cat_id)
    db.delete(cat)
    db.commit()


# ─── 商品 ───

@router.get("/stores/{store_id}/shop/products")
async def list_products(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    products = db.query(ShopProduct).filter(
        ShopProduct.store_id == store_id,
    ).order_by(ShopProduct.sort_order, ShopProduct.created_at).all()
    return [_product_dict(p) for p in products]


@router.post("/stores/{store_id}/shop/products", status_code=201)
async def create_product(
    store_id: str,
    req: ShopProductCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    p = ShopProduct(store_id=store_id, **req.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _product_dict(p)


@router.put("/stores/{store_id}/shop/products/{product_id}")
async def update_product(
    store_id: str,
    product_id: str,
    req: ShopProductUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    p = db.query(ShopProduct).filter(
        ShopProduct.id == product_id, ShopProduct.store_id == store_id
    ).first()
    if not p:
        raise NotFoundError("ShopProduct", product_id)
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return _product_dict(p)


@router.delete("/stores/{store_id}/shop/products/{product_id}", status_code=204)
async def delete_product(
    store_id: str,
    product_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    p = db.query(ShopProduct).filter(
        ShopProduct.id == product_id, ShopProduct.store_id == store_id
    ).first()
    if not p:
        raise NotFoundError("ShopProduct", product_id)
    db.delete(p)
    db.commit()


def _product_dict(p: ShopProduct) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "description": p.description,
        "staff_comment": p.staff_comment,
        "price": p.price,
        "image_url": p.image_url,
        "external_url": p.external_url,
        "ec_platform": p.ec_platform,
        "is_active": p.is_active,
        "sort_order": p.sort_order,
        "click_count": p.click_count,
    }
