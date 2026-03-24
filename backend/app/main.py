from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os

from .config import settings
from .database import engine, Base
from .core.logging import setup_logging, logger
from .core.exceptions import AppError

# ルーターのインポート
from .routers.webhook import router as webhook_router
from .routers.liff.availability import router as liff_availability_router
from .routers.liff.customers import router as liff_customers_router
from .routers.liff.reservations import router as liff_reservations_router
from .routers.admin.auth import router as admin_auth_router
from .routers.admin.reservations import router as admin_reservations_router
from .routers.admin.customers import router as admin_customers_router
from .routers.admin.staff import router as admin_staff_router
from .routers.admin.menus import router as admin_menus_router
from .routers.admin.settings import router as admin_settings_router
from .routers.admin.calendar import router as admin_calendar_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.debug)
    logger.info("Starting linebook API", extra={"env": settings.app_env})

    # テーブルを自動作成
    Base.metadata.create_all(bind=engine)

    # APSchedulerによるリマインドバッチ
    if settings.scheduler_enabled:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from .services.reminder_service import send_reminders

        scheduler = AsyncIOScheduler()
        scheduler.add_job(send_reminders, "cron", minute=0)  # 毎時0分
        scheduler.start()
        logger.info("Scheduler started")
        app.state.scheduler = scheduler

    yield

    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()
        logger.info("Scheduler stopped")


app = FastAPI(
    title="LINE予約SaaS API",
    description="LINE/LIFFを起点とした業種別対応の予約管理SaaS",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# エラーハンドラー
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled error", extra={"path": str(request.url), "error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "内部エラーが発生しました"},
    )


# APIルーター登録
PREFIX = "/api/v1"
app.include_router(webhook_router, prefix=PREFIX)
app.include_router(liff_availability_router, prefix=PREFIX)
app.include_router(liff_customers_router, prefix=PREFIX)
app.include_router(liff_reservations_router, prefix=PREFIX)
app.include_router(admin_auth_router, prefix=PREFIX)
app.include_router(admin_reservations_router, prefix=PREFIX)
app.include_router(admin_customers_router, prefix=PREFIX)
app.include_router(admin_staff_router, prefix=PREFIX)
app.include_router(admin_menus_router, prefix=PREFIX)
app.include_router(admin_settings_router, prefix=PREFIX)
app.include_router(admin_calendar_router, prefix=PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}


# フロントエンド静的ファイルの配信（Renderでフロントとバックを同一サービスにする場合）
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/admin", StaticFiles(directory=os.path.join(frontend_dir, "admin"), html=True), name="admin")
    app.mount("/liff", StaticFiles(directory=os.path.join(frontend_dir, "liff"), html=True), name="liff")
