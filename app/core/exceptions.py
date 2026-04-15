from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(
        self,
        detail: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "application_error",
        extra: dict | None = None,
    ) -> None:
        self.detail = detail
        self.status_code = status_code
        self.code = code
        self.extra = extra or {}
        super().__init__(detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found.") -> None:
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND, code="not_found")


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource conflict.") -> None:
        super().__init__(detail, status_code=status.HTTP_409_CONFLICT, code="conflict")


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Unauthorized.") -> None:
        super().__init__(detail, status_code=status.HTTP_401_UNAUTHORIZED, code="unauthorized")


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Forbidden.") -> None:
        super().__init__(detail, status_code=status.HTTP_403_FORBIDDEN, code="forbidden")


class RateLimitException(AppException):
    def __init__(self, detail: str = "Too many requests.") -> None:
        super().__init__(
            detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="rate_limited",
        )


def _to_json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (Decimal, UUID)):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(item) for item in value]
    return str(value)


def _format_validation_errors(exc: RequestValidationError) -> list[dict]:
    formatted_errors: list[dict] = []
    for error in exc.errors():
        location = list(error.get("loc", ()))
        field_path = ".".join(str(item) for item in location if item != "body")
        formatted_errors.append(
            {
                "field": field_path or None,
                "location": _to_json_safe(location),
                "message": error.get("msg", "Validation error."),
                "type": error.get("type", "validation_error"),
                "context": _to_json_safe(error.get("ctx", {})),
            }
        )
    return formatted_errors


def _exception_payload(request: Request, *, detail: str, code: str, extra: dict | None = None) -> dict:
    return _to_json_safe(
        {
        "detail": detail,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
        "extra": extra or {},
        }
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_exception_payload(request, detail=exc.detail, code=exc.code, extra=exc.extra),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        validation_errors = _format_validation_errors(exc)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_exception_payload(
                request,
                detail="Validation error.",
                code="validation_error",
                extra={"errors": validation_errors},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_exception_payload(
                request,
                detail="Internal server error.",
                code="internal_server_error",
            ),
        )
