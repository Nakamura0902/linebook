from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date as date_type
from typing import Optional

from ...database import get_db
from ...models.store import Store
from ...core.exceptions import NotFoundError, ValidationError
from ...services.availability_service import get_available_slots
from ...schemas.reservation import TimeSlotResponse

router = APIRouter(prefix="/liff", tags=["liff-availability"])


@router.get("/stores/{store_id}/availability")
async def get_availability(
    store_id: str,
    date: str = Query(..., description="YYYY-MM-DD"),
    menu_id: str = Query(...),
    staff_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise NotFoundError("Store", store_id)

    try:
        target_date = date_type.fromisoformat(date)
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")

    slots = get_available_slots(
        db=db,
        store=store,
        target_date=target_date,
        menu_id=menu_id,
        staff_id=staff_id,
    )

    return {
        "date": date,
        "slots": [
            TimeSlotResponse(
                start=s.start,
                end=s.end,
                staff_id=s.staff_id,
                staff_name=s.staff_name,
            )
            for s in slots
        ],
    }
