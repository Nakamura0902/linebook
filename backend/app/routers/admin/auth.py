from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from ...database import get_db
from ...models.admin import AdminUser
from ...core.security import verify_password, create_access_token, create_refresh_token
from ...core.auth import get_current_admin
from ...models.log import AuditLog

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    admin_id: str
    name: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(
        AdminUser.email == req.email,
        AdminUser.is_active == True,
    ).first()

    if not admin or not verify_password(req.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
        )

    admin.last_login_at = datetime.now(timezone.utc)

    # 監査ログ
    audit = AuditLog(
        tenant_id=admin.tenant_id,
        actor_type="admin",
        actor_id=admin.id,
        action="admin.login",
        resource_type="admin_user",
        resource_id=admin.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    db.commit()

    access_token = create_access_token({"sub": admin.id, "tenant_id": admin.tenant_id, "role": admin.role})
    refresh_token = create_refresh_token({"sub": admin.id})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        admin_id=admin.id,
        name=admin.name or admin.email,
        role=admin.role,
    )


@router.get("/me")
async def get_me(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    store_ids = [a.store_id for a in admin.store_access] if admin.store_access else []
    return {
        "id": admin.id,
        "email": admin.email,
        "name": admin.name,
        "role": admin.role,
        "tenant_id": admin.tenant_id,
        "store_ids": store_ids,
    }
