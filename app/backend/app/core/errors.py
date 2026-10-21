"""Единый формат ошибок API: {"error": {"code", "message", "details"}}."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ERROR_CODES = {
    "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "UNSUPPORTED_MEDIA_TYPE": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "PAYLOAD_TOO_LARGE": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}


class AppError(Exception):
    """Ожидаемая ошибка приложения с понятным сообщением для пользователя."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[List[Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code or ERROR_CODES.get(code, status.HTTP_400_BAD_REQUEST)
        self.details = details or []

    def to_payload(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": jsonable_encoder(self.details),
            }
        }


def register_error_handlers(app: FastAPI) -> None:
    """Подключает обработчики, чтобы наружу не утекали traceback и SQL."""

    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = " -> ".join(str(part) for part in error.get("loc", []) if part != "body")
            details.append(
                {
                    "field": location,
                    "message": error.get("msg", "Некорректное значение"),
                    "type": error.get("type", "value_error"),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=AppError(
                "VALIDATION_ERROR",
                "Проверьте заполненные поля: часть данных указана неверно.",
                details=details,
            ).to_payload(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
        }.get(exc.status_code, "INTERNAL_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "Ошибка запроса"
        return JSONResponse(
            status_code=exc.status_code,
            content=AppError(code, message, status_code=exc.status_code).to_payload(),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        # В лог пишем факт ошибки, наружу отдаём только обезличенное сообщение.
        import logging

        logger = logging.getLogger("app.unhandled")
        logger.exception("Необработанная ошибка при обработке %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=AppError(
                "INTERNAL_ERROR",
                "Внутренняя ошибка сервера. Попробуйте повторить действие позже.",
            ).to_payload(),
        )
