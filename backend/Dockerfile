# Why: Containerizes the backend for consistent local dev and Render deployment.

FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system deps needed by asyncpg (PostgreSQL C client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker caches this layer if requirements don't change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port uvicorn will listen on
EXPOSE 8000

# Start the ASGI server. --host 0.0.0.0 makes it accessible from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

