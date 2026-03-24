from __future__ import annotations
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import httpx

from ..database import get_db
from ..models.admin import AdminUser, AdminStoreAccess
from ..models.store import Store
from .security import decode_token

bearer_scheme = HTTPBearer()


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    admin = db.query(AdminUser).filter(AdminUser.id == admin_id, AdminUser.is_active == True).first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return admin


def require_store_access(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Store:
    """管理者が指定店舗へのアクセス権を持つか確認する"""
    store = db.query(Store).filter(Store.id == store_id, Store.is_active == True).first()
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")

    # テナントが一致することを確認
    if store.tenant_id != admin.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # super_adminはすべての店舗にアクセス可
    if admin.role == "super_admin":
        return store

    # adminは割り当てられた店舗のみ
    access = db.query(AdminStoreAccess).filter(
        AdminStoreAccess.admin_user_id == admin.id,
        AdminStoreAccess.store_id == store_id,
    ).first()

    if not access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this store")

    return store


async def get_line_user_id(x_line_access_token: Optional[str] = Header(None)) -> str:
    """LIFFアクセストークンを検証してLINE userIdを返す"""
    if not x_line_access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LINE access token required")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {x_line_access_token}"},
            timeout=5.0,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid LINE access token")

    return resp.json()["userId"]
