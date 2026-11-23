# Why: Application entry point. Creates the FastAPI app, includes all
# routers, and exposes a /health endpoint for liveness checks.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(
    title="Stylify API",
    description="Intelligent Salon Scheduling and Appointment Management Platform",
    version="0.1.0",
)

# CORS: allow the React dev server (localhost:5173) to call the API.
# In production, replace "*" with the actual frontend domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["ops"])
async def health_check():
    """
    Liveness probe. Returns 200 with env info.
    Render, Docker, and CI can hit this to confirm the server is up.
    """
    return {
        "status": "healthy",
        "env": settings.APP_ENV,
        "version": app.version,
    }

