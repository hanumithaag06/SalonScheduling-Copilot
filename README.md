# Stylify — Intelligent Salon Scheduling Platform

> College Project PRJ-012 · Salon Scheduling Copilot

## Quick Start

### 1. Database (Docker)
```bash
docker compose up -d          # starts PostgreSQL on localhost:5432
```

### 2. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows (use source venv/bin/activate on Mac/Linux)
pip install -r requirements.txt
cp .env.example .env           # then edit secrets if needed
uvicorn app.main:app --reload  # → http://localhost:8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev                    # → http://localhost:5173
```

### 4. Health Check
```
GET http://localhost:8000/health
→ {"status": "healthy", "env": "development", "version": "0.1.0"}
```

## Stack
| Layer    | Tech |
|----------|------|
| Backend  | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, JWT |
| Database | PostgreSQL 16 |
| Frontend | React + Vite, Tailwind CSS, FullCalendar, Recharts |
| DevOps   | Docker, GitHub Actions, Render + Vercel |

## Project Structure
```
stylify/
  backend/app/        ← FastAPI application
  backend/alembic/    ← database migrations
  backend/tests/      ← pytest suite
  frontend/src/       ← React application
  docs/               ← project documentation
```

