# Why: Application entry point. Configures FastAPI with lifespan background jobs,
# CORS, unified exception handlers, and mounts all application routers.

from contextlib import asynccontextmanager
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
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.routers.auth import router as auth_router
from app.routers.services import router as services_router
from app.routers.stylists import router as stylists_router
from app.routers.schedule import router as schedule_router
from app.routers.slots import router as slots_router
from app.routers.bookings import router as bookings_router
from app.routers.holds import router as holds_router
from app.routers.recommend import router as recommend_router
from app.routers.notifications import router as notifications_router
from app.routers.waitlist import router as waitlist_router
from app.routers.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook starting and stopping APScheduler background maintenance jobs."""
    # Only start scheduler if not in testing / when explicitly enabled
    if settings.APP_ENV != "test":
        start_scheduler()
    yield
    if settings.APP_ENV != "test":
        stop_scheduler()


app = FastAPI(
    title="Stylify API",
    description="Intelligent Salon Scheduling and Appointment Management Platform",
    version="0.8.0",
    lifespan=lifespan,
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
app.include_router(slots_router)
app.include_router(bookings_router)
app.include_router(holds_router)
app.include_router(recommend_router)
app.include_router(notifications_router)
app.include_router(waitlist_router)
app.include_router(admin_router)


@app.get("/health", tags=["ops"])
async def health_check():
    """Liveness probe returning server status and version."""
    return {
        "status": "healthy",
        "env": settings.APP_ENV,
        "version": app.version,
    }
