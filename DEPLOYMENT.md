# Production Deployment Guide: Supabase, Render & Vercel

This guide outlines the production deployment lifecycle for **Stylify: Salon Scheduling and Appointment Platform**, covering database provisioning on Supabase, API deployment on Render, and single-page application hosting on Vercel.

---

## 1. Supabase (Managed PostgreSQL Database)

### 1.1 Project Initialization & Extensions
1. Sign in to [Supabase](https://supabase.com) and click **"New Project"**.
2. Select an AWS region close to your target users (e.g., `us-east-1` or `ap-south-1`).
3. Set a strong database password and copy it securely.
4. Navigate to **SQL Editor** in the Supabase dashboard and run the following statement to ensure the exclusion constraint extension is active:
   ```sql
   CREATE EXTENSION IF NOT EXISTS btree_gist;
   ```

### 1.2 Database Connection String
1. Go to **Project Settings** &rarr; **Database** &rarr; **Connection string**.
2. Select the **URI** tab and choose **Mode: Session** (Port `5432`) or **Direct connection**.
3. Convert the URI to use the SQLAlchemy `asyncpg` driver:
   ```text
   # Standard Supabase URI format:
   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

   # AsyncPG URI required by Stylify backend:
   postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres
   ```

### 1.3 Apply Migrations & Seed Data
From your local terminal (or deployment pipeline):
```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres"

# Apply all Alembic schema migrations
alembic upgrade head

# Seed initial catalog, stylists, and working hours
python -m app.db.seed
```

---

## 2. Render (FastAPI Backend Deployment)

### 2.1 Web Service Configuration
1. Sign in to [Render](https://render.com) and click **"New +"** &rarr; **"Web Service"**.
2. Connect your GitHub repository: `https://github.com/[username]/stylify`.
3. Configure the following service settings:
   - **Name**: `stylify-api`
   - **Region**: Same region as your Supabase database (e.g., `Oregon` or `Ohio`)
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && alembic upgrade head`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/health`

### 2.2 Environment Variables (Render Dashboard)
Add the following key-value pairs in the **Environment** tab:

| Variable | Recommended Value | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres.[ref]:[pw]@...:5432/postgres` | Supabase AsyncPG connection string |
| `JWT_SECRET` | *Generated 64-char hex string* (`openssl rand -hex 32`) | Signs and validates user access tokens |
| `JWT_ALGORITHM` | `HS256` | HMAC signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Session lifetime (24 hours) |
| `CORS_ORIGINS` | `https://stylify.vercel.app` | **Strictly locked** to production Vercel frontend URL |
| `EMAIL_BACKEND` | `console` (or `smtp`) | Delivery mode (`console` logs to Render; `smtp` for Mailtrap/SES) |
| `SMTP_HOST` | `sandbox.smtp.mailtrap.io` | SMTP mail server hostname |
| `SMTP_PORT` | `2525` | SMTP port |
| `SMTP_USER` | *Mailtrap Username* | SMTP auth credential |
| `SMTP_PASSWORD` | *Mailtrap Password* | SMTP auth credential |
| `LLM_API_KEY` | *OpenAI / OpenRouter API Key* (Optional) | AI assistant parser (falls back locally if blank) |

> [!IMPORTANT]
> To eliminate cross-origin security vulnerabilities, `CORS_ORIGINS` must be explicitly set to the final Vercel frontend domain (`https://your-stylify-app.vercel.app`). Wildcards (`*`) are strictly prohibited in production.

---

## 3. Vercel (React Frontend Deployment)

### 3.1 Project Import & Build Settings
1. Sign in to [Vercel](https://vercel.com) and click **"Add New..."** &rarr; **"Project"**.
2. Select your `stylify` GitHub repository and click **Import**.
3. In the project setup form:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click edit and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 3.2 Frontend Environment Variables
In the **Environment Variables** section, add:
- `VITE_API_URL`: The live Render API domain without trailing slash:
  ```text
  VITE_API_URL=https://stylify-api.onrender.com
  ```

### 3.3 SPA Routing Configuration
The included `frontend/vercel.json` automatically rewrites all incoming routes to `/index.html`:
```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```
This ensures customer bookmarks and deep URLs (e.g., `/book`, `/admin/dashboard`, `/my-bookings`) reload seamlessly without HTTP 404 errors.

---

## 4. Post-Deployment Verification Checklist

1. **Verify Backend Health**:
   ```bash
   curl -I https://stylify-api.onrender.com/health
   # Expected: HTTP/1.1 200 OK
   ```

2. **Verify CORS Isolation**:
   ```bash
   curl -H "Origin: https://malicious-site.com" \
        -H "Access-Control-Request-Method: POST" \
        -I https://stylify-api.onrender.com/bookings
   # Expected: Absence of Access-Control-Allow-Origin header
   ```

3. **Verify Frontend Authentication**:
   - Visit `https://your-stylify-app.vercel.app/login`
   - Sign in with demo customer credentials: `alex@example.com` / `password123`
   - Verify that `/auth/me` responds with HTTP 200 and sets the user session in the header.

4. **Verify Booking Hold & Exclusion Constraint**:
   - Select a slot in the booking wizard to verify the 5-minute hold timer fires against Supabase.
