from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.store import Store
from ...models.customer import Customer
from ...core.auth import get_line_user_id
from ...core.exceptions import NotFoundError
from ...schemas.customer import CustomerResponse, CustomerUpdateRequest

router = APIRouter(prefix="/liff", tags=["liff-customers"])


@router.post("/customers/identify")
async def identify_customer(
    store_id: str,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    """LINE userIdから顧客を特定、なければ新規作成する"""
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise NotFoundError("Store", store_id)

    customer = db.query(Customer).filter(
        Customer.store_id == store_id,
        Customer.line_user_id == line_user_id,
    ).first()

    is_new = False
    if not customer:
        customer = Customer(
            store_id=store_id,
            line_user_id=line_user_id,
            is_first_visit=True,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        is_new = True

    return {
        "customer": CustomerResponse.model_validate(customer),
        "is_new": is_new,
    }


@router.put("/customers/{customer_id}")
async def update_customer_liff(
    customer_id: str,
    req: CustomerUpdateRequest,
    line_user_id: str = Depends(get_line_user_id),
    db: Session = Depends(get_db),
):
    """LIFFユーザーが自分の顧客情報を更新する"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise NotFoundError("Customer", customer_id)

    # 本人確認: LINE userIdが一致すること
    if customer.line_user_id != line_user_id:
        from ...core.exceptions import ForbiddenError
        raise ForbiddenError("You can only update your own profile")

    for key, value in req.model_dump(exclude_none=True).items():
        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return CustomerResponse.model_validate(customer)
