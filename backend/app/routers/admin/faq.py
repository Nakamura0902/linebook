from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.admin import AdminUser
from ...models.faq import FAQItem, ChatSession, ChatMessage
from ...models.store import Store
from ...core.auth import get_current_admin, require_store_access
from ...core.exceptions import NotFoundError
from ...services.line_service import send_line_message
from ...config import settings

router = APIRouter(prefix="/admin", tags=["admin-faq"])


# ─── FAQ CRUD ───

class FAQCreate(BaseModel):
    question: str
    answer: str
    keywords: Optional[str] = None
    sort_order: int = 0


class FAQUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    keywords: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


@router.get("/stores/{store_id}/faq")
async def list_faq(
    store_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    items = db.query(FAQItem).filter(
        FAQItem.store_id == store_id,
    ).order_by(FAQItem.sort_order, FAQItem.created_at).all()
    return [_faq_dict(f) for f in items]


@router.post("/stores/{store_id}/faq", status_code=201)
async def create_faq(
    store_id: str,
    req: FAQCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    item = FAQItem(store_id=store_id, **req.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _faq_dict(item)


@router.put("/stores/{store_id}/faq/{faq_id}")
async def update_faq(
    store_id: str,
    faq_id: str,
    req: FAQUpdate,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    item = db.query(FAQItem).filter(
        FAQItem.id == faq_id, FAQItem.store_id == store_id
    ).first()
    if not item:
        raise NotFoundError("FAQItem", faq_id)
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return _faq_dict(item)


@router.delete("/stores/{store_id}/faq/{faq_id}", status_code=204)
async def delete_faq(
    store_id: str,
    faq_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    item = db.query(FAQItem).filter(
        FAQItem.id == faq_id, FAQItem.store_id == store_id
    ).first()
    if not item:
        raise NotFoundError("FAQItem", faq_id)
    db.delete(item)
    db.commit()


def _faq_dict(f: FAQItem) -> dict:
    return {
        "id": f.id,
        "question": f.question,
        "answer": f.answer,
        "keywords": f.keywords,
        "is_active": f.is_active,
        "sort_order": f.sort_order,
    }


# ─── チャットセッション管理 ───

@router.get("/stores/{store_id}/chats")
async def list_chats(
    store_id: str,
    status: Optional[str] = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    q = db.query(ChatSession).filter(ChatSession.store_id == store_id)
    if status:
        q = q.filter(ChatSession.status == status)
    sessions = q.order_by(ChatSession.updated_at.desc()).limit(100).all()
    return [_session_dict(s) for s in sessions]


@router.get("/stores/{store_id}/chats/{session_id}/messages")
async def get_chat_messages(
    store_id: str,
    session_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.store_id == store_id
    ).first()
    if not session:
        raise NotFoundError("ChatSession", session_id)

    # 既読にする
    session.unread_count = 0
    db.commit()

    return {
        "session": _session_dict(session),
        "messages": [_msg_dict(m) for m in session.messages],
    }


class AdminReply(BaseModel):
    text: str


@router.post("/stores/{store_id}/chats/{session_id}/reply")
async def reply_to_chat(
    store_id: str,
    session_id: str,
    req: AdminReply,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.store_id == store_id
    ).first()
    if not session:
        raise NotFoundError("ChatSession", session_id)

    store = db.query(Store).filter(Store.id == store_id).first()
    access_token = store.line_access_token or settings.line_channel_access_token

    # LINEにプッシュメッセージ送信
    await send_line_message(access_token, session.line_user_id, [
        {"type": "text", "text": req.text}
    ])

    # メッセージ記録
    db.add(ChatMessage(session_id=session.id, role="admin", content=req.text))
    db.commit()
    return {"ok": True}


@router.put("/stores/{store_id}/chats/{session_id}/close")
async def close_chat(
    store_id: str,
    session_id: str,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    require_store_access(store_id, admin, db)
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id, ChatSession.store_id == store_id
    ).first()
    if not session:
        raise NotFoundError("ChatSession", session_id)
    session.status = "closed"
    db.commit()
    return {"ok": True}


def _session_dict(s: ChatSession) -> dict:
    return {
        "id": s.id,
        "line_user_id": s.line_user_id,
        "display_name": s.display_name,
        "status": s.status,
        "unread_count": s.unread_count,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _msg_dict(m: ChatMessage) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
