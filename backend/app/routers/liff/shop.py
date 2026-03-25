from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.shop import ShopCategory, ShopProduct, CustomerInterest, ShopBanner
from ...models.customer import Customer
from ...core.auth import get_line_user_id
from ...core.exceptions import NotFoundError
from ...schemas.shop import CustomerInterestSave

router = APIRouter(prefix="/liff", tags=["liff-shop"])


@router.get("/stores/{store_id}/shop/banners")
async def get_shop_banners(store_id: str, db: Session = Depends(get_db)):
    banners = db.query(ShopBanner).filter(
        ShopBanner.store_id == store_id,
        ShopBanner.is_active == True,
    ).order_by(ShopBanner.sort_order, ShopBanner.created_at).all()
    return [
        {
            "id": b.id,
            "title": b.title,
            "subtitle": b.subtitle,
            "badge_text": b.badge_text,
            "image_url": b.image_url,
            "link_url": b.link_url,
            "bg_color": b.bg_color,
        }
        for b in banners
    ]


@router.get("/stores/{store_id}/shop/categories")
async def get_shop_categories(store_id: str, db: Session = Depends(get_db)):
    cats = db.query(ShopCategory).filter(
        ShopCategory.store_id == store_id,
    ).order_by(ShopCategory.sort_order, ShopCategory.created_at).all()
    return [{"id": c.id, "name": c.name, "emoji": c.emoji} for c in cats]


@router.get("/stores/{store_id}/shop/products")
async def get_shop_products(
    store_id: str,
    category_id: str = "",
    db: Session = Depends(get_db),
):
    q = db.query(ShopProduct).filter(
        ShopProduct.store_id == store_id,
        ShopProduct.is_active == True,
    )
    if category_id:
        q = q.filter(ShopProduct.category_id == category_id)
    products = q.order_by(ShopProduct.sort_order, ShopProduct.created_at).all()
    return [_product_dict(p) for p in products]


@router.get("/shop/products/{product_id}")
async def get_shop_product(product_id: str, db: Session = Depends(get_db)):
    p = db.query(ShopProduct).filter(ShopProduct.id == product_id).first()
    if not p:
        raise NotFoundError("Product", product_id)
    return _product_dict(p)


@router.post("/shop/products/{product_id}/click")
async def record_click(product_id: str, db: Session = Depends(get_db)):
    p = db.query(ShopProduct).filter(ShopProduct.id == product_id).first()
    if p:
        p.click_count += 1
        db.commit()
    return {"ok": True}


@router.post("/customers/{customer_id}/interests")
async def save_interests(
    customer_id: str,
    req: CustomerInterestSave,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer or customer.line_user_id != line_user_id:
        raise NotFoundError("Customer", customer_id)

    # 既存の興味を削除して保存し直す
    db.query(CustomerInterest).filter(CustomerInterest.customer_id == customer_id).delete()
    for cat_id in req.category_ids:
        db.add(CustomerInterest(customer_id=customer_id, category_id=cat_id))
    db.commit()
    return {"ok": True}


@router.get("/customers/{customer_id}/interests")
async def get_interests(
    customer_id: str,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer or customer.line_user_id != line_user_id:
        raise NotFoundError("Customer", customer_id)
    interests = db.query(CustomerInterest).filter(
        CustomerInterest.customer_id == customer_id
    ).all()
    return [i.category_id for i in interests]


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
        "click_count": p.click_count,
    }
