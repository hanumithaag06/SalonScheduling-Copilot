# Why: Production-grade containerization for the Stylify FastAPI backend.
# Built on lightweight Python 3.12-slim with asyncpg/Postgres dependencies, non-root user, and uvicorn server.

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by asyncpg/psycopg C compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user for security best practices
RUN groupadd -r stylify && useradd -r -g stylify -d /app stylify

# Install Python dependencies first for optimal Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and migrations
COPY --chown=stylify:stylify . .

# Switch to unprivileged runtime user
USER stylify

# Expose internal ASGI service port
EXPOSE 8000

# Health check to ensure service readiness
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn ASGI server bound to 0.0.0.0
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
