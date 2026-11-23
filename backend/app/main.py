# Why: Application entry point. Configures FastAPI, registers CORS,
# registers the global error handlers, and mounts all API routers.

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
)
from app.routers.auth import router as auth_router
from app.routers.services import router as services_router
from app.routers.stylists import router as stylists_router
from app.routers.schedule import router as schedule_router

app = FastAPI(
    title="Stylify API",
    description="Intelligent Salon Scheduling and Appointment Management Platform",
    version="0.2.0",
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handlers (Standard Shape: {"detail": "...", "code": "..."}) ──
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

# ── Mount Routers ──
app.include_router(auth_router)
app.include_router(services_router)
app.include_router(stylists_router)
app.include_router(schedule_router)


@app.get("/health", tags=["ops"])
async def health_check():
    """Liveness probe returning server status and version."""
    return {
        "status": "healthy",
        "env": settings.APP_ENV,
        "version": app.version,
    }
