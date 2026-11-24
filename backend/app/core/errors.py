# Why: Consistent application-wide error handling.
# Guarantees all errors follow the unified shape: {"detail": "...", "code": "..."}.

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppException(Exception):
    """Base application exception with HTTP status code and custom error code."""
    def __init__(self, status_code: int, detail: str, code: str):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found", code: str = "NOT_FOUND"):
        super().__init__(status_code=404, detail=detail, code=code)


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflict", code: str = "CONFLICT"):
        super().__init__(status_code=409, detail=detail, code=code)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Could not validate credentials", code: str = "UNAUTHORIZED"):
        super().__init__(status_code=401, detail=detail, code=code)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Permission denied", code: str = "FORBIDDEN"):
        super().__init__(status_code=403, detail=detail, code=code)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad request", code: str = "BAD_REQUEST"):
        super().__init__(status_code=400, detail=detail, code=code)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles all custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Formats Pydantic 422 schema validation errors into our standard shape."""
    first_error = exc.errors()[0]
    loc = " -> ".join(str(l) for l in first_error.get("loc", []))
    msg = first_error.get("msg", "Invalid input")
    return JSONResponse(
        status_code=422,
        content={"detail": f"{loc}: {msg}", "code": "VALIDATION_ERROR"},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Formats default FastAPI/Starlette HTTPExceptions."""
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 409:
        code = "CONFLICT"

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail), "code": code},
    )

