from __future__ import annotations
from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(self, status_code: int, error: str, message: str, details: dict = None):
        super().__init__(
            status_code=status_code,
            detail={"error": error, "message": message, "details": details or {}},
        )


class NotFoundError(AppError):
    def __init__(self, resource: str, resource_id: str = None):
        msg = f"{resource} not found"
        if resource_id:
            msg = f"{resource} '{resource_id}' not found"
        super().__init__(status.HTTP_404_NOT_FOUND, "not_found", msg)


class ConflictError(AppError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(status.HTTP_409_CONFLICT, "conflict", message, details)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict = None):
        super().__init__(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", message, details)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(status.HTTP_403_FORBIDDEN, "forbidden", message)


class DoubleBookingError(ConflictError):
    def __init__(self, conflicting_slot: str = None):
        details = {"conflicting_slot": conflicting_slot} if conflicting_slot else {}
        super().__init__("この時間帯はすでに予約が入っています。別の時間帯を選択してください。", details)


class BlacklistedCustomerError(ForbiddenError):
    def __init__(self):
        super().__init__("この顧客は予約を受け付けできません。")


class CancellationNotAllowedError(AppError):
    def __init__(self, message: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, "cancellation_not_allowed", message)
