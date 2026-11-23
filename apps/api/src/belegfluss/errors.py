"""Errors with stable codes, so clients can show their own (translated) messages."""

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


async def handle_app_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # registered only for AppError; keeps mypy precise
        raise exc
    body = ErrorBody(code=exc.code, message=exc.message)
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(body.model_dump(), status_code=exc.status_code, headers=headers)


def error_responses(*status_codes: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI documentation for the error responses of a route."""
    return {code: {"model": ErrorBody} for code in status_codes}
