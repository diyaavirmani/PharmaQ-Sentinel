import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class PharmaQSentinelError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ConfigurationError(PharmaQSentinelError):
    pass


class DatabaseConnectionError(PharmaQSentinelError):
    pass


def _error_content(message: str) -> dict[str, str]:
    return {"detail": message}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PharmaQSentinelError)
    async def handle_pharmaq_error(
        request: Request,
        exc: PharmaQSentinelError,
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", "unprovided")
        logger.warning("Application error [%s]: %s", request_id, exc.message)
        return JSONResponse(status_code=exc.status_code, content=_error_content(exc.message))

    @app.exception_handler(ValidationError)
    async def handle_configuration_error(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", "unprovided")
        logger.error("Configuration validation failed [%s]", request_id)
        message = str(exc) if get_settings().debug else "Configuration error"
        return JSONResponse(status_code=500, content=_error_content(message))

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(
        request: Request,
        _exc: SQLAlchemyError,
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", "unprovided")
        logger.error("Database operation failed [%s]", request_id)
        return JSONResponse(status_code=503, content=_error_content("Database unavailable"))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID", "unprovided")
        logger.exception("Unexpected application error [%s]", request_id)
        return JSONResponse(status_code=500, content=_error_content("Internal server error"))
