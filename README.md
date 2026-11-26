# Stylify: Intelligent Salon Scheduling and Appointment Platform

[![CI Pipeline](https://github.com/stylify/stylify/actions/workflows/ci.yml/badge.svg)](https://github.com/stylify/stylify/actions)
![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)
![React](https://img.shields.io/badge/React-19.3-61dafb.svg)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4.0-38b2ac.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)
![Tests](https://img.shields.io/badge/tests-99%20passed-success.svg)

> **Product Release**: `v1.0.0-production` &bull; **System Architecture**: *Intelligent Salon Scheduling and Appointment Management Platform with Concurrency Guards, Explainable Recommendations, and AI Conversational Copilot*

---

## 1. Project Overview

**Stylify** is a production-grade salon scheduling platform built to eliminate double-booking race conditions, minimize calendar fragmentation, and simplify appointment booking through explainable artificial intelligence.

Unlike traditional booking software that relies on fragile optimistic client-side checks or black-box chatbots, Stylify pairs a **pure functional slot engine** with **PostgreSQL exclusion constraints (`btree_gist`)**, **5-minute pre-booking holds**, an **explainable rule-based recommender**, an **automated waitlist cascade**, and a **strictly guarded conversational assistant**.

---

## 2. Key Features

- **Double-Booking Proof Concurrency Guard**:
  - PostgreSQL exclusion lock (`EXCLUDE USING gist (stylist_id WITH =, tstzrange(start_ts, end_ts) WITH &&)`) guarantees zero concurrent collisions even during peak microsecond traffic spikes.
- **Pure Functional 15-Minute Slot Engine**:
  - Pure Python function (`slot_engine.py`) calculating exact free gaps from stylist schedules, confirmed appointments, active holds, lead times, and buffers with zero DB/HTTP dependencies.
- **Explainable Recommender Engine**:
  - Scored ranking formula incorporating client loyalty (+3), preferred daypart (+2), stylist specialization (+1), and adjacent booking gap optimization (+1) with auto-generated plain-language reasons.
- **5-Minute Pre-Booking Holds**:
  - Temporarily locks candidate slots for 300 seconds during client checkout. Automatically released on expiry and cleaned via background APScheduler jobs.
- **Automated Waitlist Cascade**:
  - Clients queue for fully booked dates; on appointment cancellation, the earliest matching subscriber receives an exclusive 15-minute claim offer before cascading to the next customer.
- **Guarded AI Booking Assistant**:
  - Natural language parsing with hybrid fallback (`rapidfuzz` token-set ratio + `dateparser`). The assistant extracts intent but **never creates bookings directly** without explicit client confirmation.
- **Full Administrator Suite**:
  - Recharts dashboard (daily booking curves, revenue per service, stylist utilization %, weekly appointment heatmap), FullCalendar multi-stylist resource column view, and proxy booking actions.

---

## 3. System Architecture

```mermaid
flowchart TD
    subgraph Client_Tier["Client Tier (Vercel)"]
        UI["React 19 + Tailwind v4 SPA"]
        WIZARD["5-Step Booking Wizard"]
        CHAT["Conversational AI Drawer"]
        ADMIN_UI["FullCalendar & Recharts Dashboard"]
    end

    subgraph API_Tier["API Application Tier (Render)"]
        GATEWAY["FastAPI Monolith Gateway (/api)"]
        AUTH_MW["JWT & Role Authorization Guard"]
        
        subgraph Pure_Engines["Pure Functional Computational Engines"]
            SLOT_ENG["slot_engine.py (15-min Slot Gaps)"]
            REC_ENG["recommender.py (Multi-Factor Scoring)"]
            INTENT_ENG["intent_parser.py (NLP / RapidFuzz)"]
            WAIT_ENG["waitlist_engine.py (FIFO Cascade)"]
        end
        
        SCHED["APScheduler (Hold Cleanup & Reminders)"]
    end

    subgraph Data_Tier["Data Tier (Supabase / PostgreSQL 16)"]
        EXCLUDE_LOCK["btree_gist Exclusion Constraint"]
        DB_TABLES[("PostgreSQL 16 Tables")]
    end

    UI -->|HTTPS / REST| GATEWAY
    CHAT -->|/assistant/suggest| GATEWAY
    ADMIN_UI -->|/admin/dashboard| GATEWAY
    
    GATEWAY --> AUTH_MW
    AUTH_MW --> Pure_Engines
    GATEWAY --> SCHED
    
    Pure_Engines -->|Read-Only Data| DB_TABLES
    GATEWAY -->|Write Transactions| EXCLUDE_LOCK
    EXCLUDE_LOCK --> DB_TABLES
```

---

## 4. Database Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USER ||--o{ BOOKING : "places"
    USER ||--o{ WAITLIST : "joins"
    USER ||--o{ NOTIFICATION : "receives"
    USER ||--o{ SLOT_HOLD : "holds"
    
    STYLIST ||--o{ STYLIST_SERVICES : "offers"
    SERVICE ||--o{ STYLIST_SERVICES : "provided_by"
    
    STYLIST ||--o{ WORKING_HOURS : "operates"
    STYLIST ||--o{ TIME_OFF : "takes"
    STYLIST ||--o{ BOOKING : "scheduled_for"
    SERVICE ||--o{ BOOKING : "service_type"
    
    BOOKING ||--o{ AUDIT_LOG : "audited_by"

    USER {
        int id PK
        string name
        string email UK
        string phone
        string password_hash
        string role "customer | admin"
        datetime created_at
    }

    SERVICE {
        int id PK
        string name
        string category
        int duration_min
        numeric price
        boolean is_active
    }

    STYLIST {
        int id PK
        string name
        string specialization
        boolean is_active
    }

    STYLIST_SERVICES {
        int stylist_id FK
        int service_id FK
    }

    WORKING_HOURS {
        int id PK
        int stylist_id FK
        int weekday "0-6"
        time start_time
        time end_time
    }

    TIME_OFF {
        int id PK
        int stylist_id FK
        date start_date
        date end_date
        string reason
    }

    BOOKING {
        int id PK
        int customer_id FK
        int stylist_id FK
        int service_id FK
        timestamptz start_ts
        timestamptz end_ts
        string status "confirmed | cancelled | completed"
        timestamptz created_at
    }

    SLOT_HOLD {
        int id PK
        int user_id FK
        int stylist_id FK
        int service_id FK
        timestamptz slot_time
        timestamptz expires_at
    }

    WAITLIST {
        int id PK
        int user_id FK
        int service_id FK
        int stylist_id FK
        date target_date
        string time_pref
        string status "waiting | offered | claimed | expired"
        timestamptz offered_slot
        timestamptz offer_expires_at
    }

    NOTIFICATION {
        int id PK
        int user_id FK
        int booking_id FK
        string type
        string title
        string message
        boolean is_read
        timestamptz created_at
    }

    AUDIT_LOG {
        int id PK
        int booking_id FK
        int user_id FK
        string action
        string old_value
        string new_value
        timestamptz timestamp
    }
```

---

## 5. Local Setup Instructions

### 5.1 Prerequisites
- **Python 3.12+**
- **Node.js 20+** and **npm**
- **Docker** and **Docker Compose** (for PostgreSQL)

### 5.2 Database Setup
```bash
# Start PostgreSQL 16 container with btree_gist support
docker compose up -d

# Verify database container is running
docker ps --filter name=stylify_db
```

### 5.3 Backend Setup
```bash
cd backend

# Create and activate Python virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run database migrations and seed catalog
alembic upgrade head
python -m app.db.seed

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```
*API Swagger Documentation will be live at `http://localhost:8000/docs`.*

### 5.4 Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Copy environment variables
cp .env.example .env

# Start Vite development server
npm run dev
```
*Web application will be accessible at `http://localhost:5173`.*

---

## 6. Environment Variables Reference

### Backend (`backend/.env`)
| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://stylify:stylify_pass@localhost:5432/stylify_db` | AsyncPG PostgreSQL connection string |
| `JWT_SECRET` | `change_this_to_a_secure_random_secret_key_min_32_chars` | Secret key for JWT signing |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token expiration in minutes (24h) |
| `CORS_ORIGINS` | `http://localhost:5173` | Allowed frontend origins (comma-separated) |
| `EMAIL_BACKEND` | `console` | `console` for local dev; `smtp` for Mailtrap/SES |
| `SMTP_HOST` | `sandbox.smtp.mailtrap.io` | SMTP mail server |
| `SMTP_PORT` | `2525` | SMTP port |
| `SMTP_USER` | `null` | SMTP user |
| `SMTP_PASSWORD` | `null` | SMTP password |
| `LLM_API_KEY` | *(blank)* | OpenAI API key (optional; local parser runs if blank) |
| `LLM_MODEL` | `gpt-4o-mini` | Model for conversational extraction |

### Frontend (`frontend/.env`)
| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL (or empty to use Vite `/api` proxy) |

---

## 7. Demo Credentials (Dummy Data)

| Role | Email Address | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin@stylify.com` | `admin123` | Full Admin Portal, Dashboard, Calendar, Proxy Bookings, CSV Export |
| **Customer (Loyal)** | `alex@example.com` | `password123` | Booking Wizard, My Bookings, Waitlist, Assistant (+3 loyalty boost) |
| **Customer (Standard)** | `sarah@example.com` | `password123` | Booking Wizard, Reschedule/Cancel, Notification Bell |
| **Customer (New)** | `michael@example.com` | `password123` | Standard customer account |

---

## 8. Test Suite Verification Table

Stylify features an exhaustive automated test suite with **99 passing tests** across 15 distinct modules:

| Test Module | Tests | Focus Area | Code Coverage |
| :--- | :---: | :--- | :---: |
| `test_slot_engine.py` | 7 | Pure 15-min gap math, empty day, fully booked, time-off, holidays, lead times | **94%** |
| `test_recommender.py` | 7 | Loyalty boost scaling, preferred time matching, specialization, gap fill | **94%** |
| `test_waitlist_engine.py` | 13 | Pure FIFO priority queue, time-of-day eligibility, 15-min offer cascade | **93%** |
| `test_intent_parser.py` | 4 | 15 sample customer sentences, RapidFuzz token matching, budget extractor | **92%** |
| `test_analytics_service.py`| 5 | Pure dashboard calculations, stylist utilization %, revenue per service | **98%** |
| `test_bookings.py` | 9 | Collision guard, 2-hr cancel window, overlap rejection, concurrency collision | 85% |
| `test_holds.py` | 6 | 5-minute pre-booking hold, user isolation, expiry, APScheduler purge | 88% |
| `test_waitlist_notifications.py`| 7 | Join waitlist, cancellation trigger, offer claim, cascading to next | 82% |
| `test_assistant_router.py` | 6 | `/assistant/parse`, `/assistant/suggest`, budget filter, zero-booking guard | 100% |
| `test_admin_router.py` | 6 | Admin dashboard stats match seed, CSV export, proxy book, proxy cancel | 86% |
| `test_admin_crud.py` | 5 | Service CRUD, stylist mappings, working hours, 403 forbidden checks | 91% |
| `test_auth.py` | 7 | JWT issue/validation, duplicate registration (409), wrong password (401) | 88% |
| `test_slots_router.py` | 5 | `GET /slots` filtering by stylist, date, max_price, and hold exclusions | 85% |
| `test_recommend_router.py` | 5 | `GET /recommend` live endpoint queries and ranking responses | 84% |
| `test_seed.py` & `test_models.py` | 7 | Idempotent database seeding, relationships, and hash validation | 100% |
| **TOTAL** | **99** | **Full End-to-End System Suite** | **92% Core** |

To execute the test suite with coverage:
```bash
cd backend
pytest --cov=app --cov-report=term-missing -v
```

---

## 9. Live Deployment & Documentation Links

- **Live Frontend**: [https://stylify.vercel.app](https://stylify.vercel.app) *(or your Vercel deployment URL)*
- **Live Backend API**: [https://stylify-api.onrender.com](https://stylify-api.onrender.com) *(or your Render deployment URL)*
- **Interactive Swagger Docs**: [https://stylify-api.onrender.com/docs](https://stylify-api.onrender.com/docs)
- **Deployment Walkthrough Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Postman API Collection**: [docs/postman_collection.json](docs/postman_collection.json)
- **Project Viva Video Script**: [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md)
- **10-Slide Report Outline**: [docs/SLIDE_DECK_OUTLINE.md](docs/SLIDE_DECK_OUTLINE.md)
- **Evaluation Screenshot Checklist**: [docs/SCREENSHOT_CHECKLIST.md](docs/SCREENSHOT_CHECKLIST.md)

---

## 10. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details. Built for Stylify Salon Platform.
