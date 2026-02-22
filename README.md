<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/LightGBM-02569B?style=for-the-badge&logo=microsoft&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq_LLM-FF6600?style=for-the-badge&logo=ai&logoColor=white" />
  <img src="https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" />
  <img src="https://img.shields.io/badge/TailwindCSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
</p>

<h1 align="center">🏥 HealthFlow AI</h1>

<p align="center">
  <strong>AI-Driven Hospital Operations Intelligence Platform</strong><br/>
  Predict admissions 7 days ahead with ML-powered forecasting, live external signals, and an AI agent that explains every trend.
</p>

<p align="center">
  <a href="https://hospital-forecast.vercel.app/">🌐 Live Demo</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-api-reference">API Reference</a>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Live Demo](#-live-demo)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [API Reference](#-api-reference)
- [AI Agent Layer](#-ai-agent-layer)
- [Automation & CI/CD](#-automation--cicd)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Deployment](#-deployment)
- [Design Principles](#-design-principles)

---

## 🔭 Overview

**HealthFlow AI** is a full-stack, production-grade hospital admissions forecasting platform that combines:

1. **LightGBM ensemble models** trained on historical admission data with cross-validated horizon-specific models (Days 1–7).
2. **Live external signals** — weather, AQI, outbreak indices, and mobility data fetched daily from [Open-Meteo](https://open-meteo.com/) (free, no API key).
3. **A Groq-powered AI Agent** that explains forecast trends, identifies drivers, and provides actionable staffing recommendations using real database data.
4. **A modern Next.js frontend** with glassmorphism dark-themed UI, interactive charts, and real-time AI insights.

All forecasts are **precomputed daily** — the API never runs inference inside request handlers. The entire data pipeline is automated via GitHub Actions.

---

## 🌐 Live Demo

| Service | URL |
|---------|-----|
| **Frontend** | [https://hospital-forecast.vercel.app](https://hospital-forecast.vercel.app) |
| **Backend API** | [https://hospitalforecasting.vercel.app](https://hospitalforecasting.vercel.app) |
| **API Docs (Swagger)** | [https://hospitalforecasting.vercel.app/docs](https://hospitalforecasting.vercel.app/docs) |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitHub Actions (Cron)                        │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │ Fetch Signals │  │ Daily Forecast   │  │ Weekly Retrain       │  │
│  │ 2:00 AM UTC  │→ │ 2:30 AM UTC      │  │ Sunday 3:00 AM UTC   │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬───────────┘  │
└─────────┼──────────────────┼────────────────────────┼──────────────┘
          │                  │                        │
          ▼                  ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Neon PostgreSQL (Source of Truth)                 │
│  ┌──────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │hospitals │ │admission_    │ │forecasts │ │external_signals  │   │
│  │          │ │history       │ │(UPSERT)  │ │(UPSERT)          │   │
│  └──────────┘ └──────────────┘ └──────────┘ └──────────────────┘   │
│  ┌──────────────┐  ┌──────────┐                                    │
│  │forecast_runs │  │users     │                                    │
│  └──────────────┘  └──────────┘                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  FastAPI on Vercel (Serverless)                      │
│  ┌───────────┐  ┌──────────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ /forecast │  │ /auth/*      │  │ /agent/*  │  │ /system/*    │  │
│  │ /predict  │  │ JWT-secured  │  │ Groq LLM  │  │ /hospitals   │  │
│  └───────────┘  └──────────────┘  └───────────┘  └──────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Next.js 14 Frontend on Vercel                     │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │Dashboard │  │ Hospitals │  │ AI Agent │  │ System Status    │   │
│  │(Charts)  │  │ (Table)   │  │ (Chat)   │  │ (Health Cards)   │   │
│  └──────────┘  └───────────┘  └──────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **GitHub Actions** fetch external signals daily at 2:00 AM UTC from Open-Meteo (weather, AQI).
2. **Daily Forecast Job** runs at 2:30 AM — loads model, fetches latest data from DB, generates 7-day predictions for all hospitals, and UPSERTs them.
3. **Weekly Retrain** runs every Sunday — pulls all admission history from DB, retrains per-horizon LightGBM models.
4. **FastAPI** serves precomputed forecasts from the DB. Zero inference at request time.
5. **AI Agent** uses Groq to reason over real DB data (forecasts, admissions, signals) and explain trends.
6. **Frontend** renders charts, tables, and AI insights with a modern glassmorphism UI.

---

## 🛠 Tech Stack

### Backend

| Technology | Purpose |
|------------|---------|
| **[FastAPI](https://fastapi.tiangolo.com/)** | Async Python API framework |
| **[SQLAlchemy 2.0](https://www.sqlalchemy.org/)** | ORM with declarative models |
| **[Neon PostgreSQL](https://neon.tech/)** | Serverless Postgres (single source of truth) |
| **[Alembic](https://alembic.sqlalchemy.org/)** | Database migrations |
| **[LightGBM](https://lightgbm.readthedocs.io/)** | Gradient boosting for admission forecasting |
| **[scikit-learn](https://scikit-learn.org/)** | Feature engineering & cross-validation |
| **[Groq API](https://groq.com/)** | LLM inference (Llama 3.3 70B) for AI agent |
| **[python-jose](https://python-jose.readthedocs.io/)** | JWT authentication |
| **[bcrypt](https://pypi.org/project/bcrypt/)** | Password hashing |
| **[httpx](https://www.python-httpx.org/)** | Async HTTP client for Groq API |
| **[Open-Meteo](https://open-meteo.com/)** | Free weather & AQI data (no API key) |

### Frontend

| Technology | Purpose |
|------------|---------|
| **[Next.js 14](https://nextjs.org/)** (App Router) | React framework with SSR/SSG |
| **[TypeScript](https://www.typescriptlang.org/)** | Type-safe JavaScript |
| **[TailwindCSS 3.4](https://tailwindcss.com/)** | Utility-first CSS framework |
| **[Recharts](https://recharts.org/)** | Composable chart library |
| **[Framer Motion](https://www.framer.com/motion/)** | Animation library |
| **[Axios](https://axios-http.com/)** | HTTP client with JWT interceptors |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **[Vercel](https://vercel.com/)** | Serverless deployment (both frontend & backend) |
| **[GitHub Actions](https://github.com/features/actions)** | CI/CD — daily forecasts, weekly retrain, signal fetching |
| **[Neon](https://neon.tech/)** | Serverless PostgreSQL with branching |

---

## 📁 Project Structure

```
Hospital_forecasting/
│
├── api/
│   └── index.py                  # Vercel serverless entry point (re-exports FastAPI app)
│
├── app/
│   ├── main.py                   # FastAPI application (read-only endpoints)
│   ├── dependencies.py           # Auth dependency injection (get_current_user, require_admin)
│   ├── agent/
│   │   ├── router.py             # POST /agent/query endpoint
│   │   ├── service.py            # Groq API integration, DB context fetching, prompt engineering
│   │   └── schemas.py            # AgentQueryRequest / AgentQueryResponse
│   ├── auth/
│   │   ├── router.py             # /auth/register, /auth/login, /auth/me
│   │   ├── service.py            # User creation, authentication logic
│   │   ├── security.py           # JWT token creation & verification
│   │   ├── schemas.py            # Auth Pydantic models
│   │   └── models.py             # Auth-specific model helpers
│   ├── core/
│   │   ├── config.py             # Pydantic settings (SECRET_KEY, JWT config)
│   │   └── database.py           # Core DB helpers
│   └── services/
│       └── external_data_service.py  # Open-Meteo API integration
│
├── database/
│   ├── base.py                   # SQLAlchemy DeclarativeBase
│   ├── models.py                 # All DB models (Hospital, Forecast, User, etc.)
│   ├── session.py                # Engine, SessionLocal, get_db (NullPool for serverless)
│   └── crud.py                   # CRUD operations with UPSERT (ON CONFLICT DO UPDATE)
│
├── forecast_system/
│   ├── config.py                 # ML configuration
│   ├── db_loader.py              # DB → DataFrame loader
│   ├── features.py               # Feature engineering pipeline
│   ├── inference.py              # Model inference logic
│   ├── ingestion.py              # Data ingestion utilities
│   ├── model_bundle.py           # ModelBundle class (load/save)
│   ├── training.py               # Training pipeline
│   └── utils.py                  # Logger and utilities
│
├── models/
│   └── forecast_system/
│       ├── lightgbm_final.pkl           # Ensemble model bundle
│       ├── lightgbm_final_horizons/     # Per-horizon models (horizon_1.pkl – horizon_7.pkl)
│       ├── evaluation_metrics.json      # Training evaluation results
│       ├── feature_importance.csv       # Feature importance rankings
│       └── diagnostics/                 # Residual plots, horizon degradation charts
│
├── scripts/
│   ├── daily_forecast_job.py     # Daily precompute forecasts (GitHub Actions)
│   ├── weekly_retrain.py         # Weekly model retraining (GitHub Actions)
│   ├── fetch_external_signals.py # Daily external data fetch (GitHub Actions)
│   └── seed_db_from_csv.py       # One-time DB seed from CSV (dev only)
│
├── alembic/                      # Database migrations
│   └── versions/                 # Migration scripts
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx            # Root layout (Navbar + Footer shell)
│   │   ├── globals.css           # Design system (glassmorphism, gradients, badges)
│   │   ├── page.tsx              # Landing page (hero, features, architecture, tech)
│   │   ├── dashboard/page.tsx    # Forecast dashboard (charts, table, signals, AI insights)
│   │   ├── hospitals/page.tsx    # Hospital directory table
│   │   ├── agent/page.tsx        # AI Agent chat interface
│   │   ├── system/page.tsx       # System health & status cards
│   │   ├── login/page.tsx        # Sign in page
│   │   ├── register/page.tsx     # Registration page
│   │   ├── about/page.tsx        # About page
│   │   └── contact/page.tsx      # Contact form
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Navbar.tsx        # Sticky glassmorphism navbar (mobile responsive)
│   │   │   ├── Footer.tsx        # Three-column footer
│   │   │   └── Container.tsx     # Max-width content wrapper
│   │   ├── ui/
│   │   │   ├── Logo.tsx          # SVG logo (medical cross + wave + pixel squares)
│   │   │   └── GlobalLoader.tsx  # Dual-ring loading animation
│   │   ├── agent/
│   │   │   └── InsightCard.tsx   # AI insight display with risk level & inference time
│   │   ├── HospitalSelector.tsx  # Multi-select hospital dropdown
│   │   └── ProtectedRoute.tsx    # JWT auth guard
│   ├── lib/
│   │   ├── api.ts                # Axios instance with JWT interceptors & error handling
│   │   └── auth.ts               # Token & user localStorage helpers
│   ├── tailwind.config.ts        # Extended theme (navy, cyan, teal, custom animations)
│   ├── package.json              # Frontend dependencies
│   └── vercel.json               # Frontend Vercel config
│
├── .github/workflows/
│   ├── fetch-external-signals.yml  # Daily at 2:00 AM UTC
│   ├── daily-forecast.yml          # Daily at 2:30 AM UTC
│   ├── weekly-retrain.yml          # Sunday at 3:00 AM UTC
│   └── retrain.yml                 # Monthly retrain (legacy)
│
├── requirements.txt              # Slim deps for Vercel serverless (~50 MB)
├── requirements-ml.txt           # Full ML deps for scripts & local dev
├── vercel.json                   # Backend Vercel config
├── alembic.ini                   # Alembic configuration
└── setup.py                      # Package setup
```

---

## 🗄 Database Schema

All data lives in **Neon PostgreSQL**. No CSV files in the production path.

```
┌──────────────────┐       ┌───────────────────────┐
│     users         │       │     hospitals          │
├──────────────────┤       ├───────────────────────┤
│ id (UUID, PK)    │       │ id (UUID, PK)         │
│ email (unique)   │       │ hospital_id (unique)   │
│ name             │       │ name                   │
│ hashed_password  │       │ region                 │
│ role             │       │ capacity               │
│ is_active        │       │ population             │
│ created_at       │       │ population_density     │
│ updated_at       │       │ elderly_ratio          │
└────────┬─────────┘       │ icu_capacity           │
         │                 │ created_at             │
         │                 └───────┬───────────────┘
         │                         │
         ▼                         │ 1:N
┌──────────────────┐               ├──────────────────────┐
│  forecast_runs   │               │                      │
├──────────────────┤               ▼                      ▼
│ id (UUID, PK)    │    ┌───────────────────┐  ┌──────────────────────┐
│ user_id (FK)     │    │ admission_history │  │  external_signals    │
│ hospital_count   │    ├───────────────────┤  ├──────────────────────┤
│ horizon_count    │    │ id (UUID, PK)     │  │ id (UUID, PK)        │
│ total_forecasts  │    │ hospital_id (FK)  │  │ hospital_id (FK)     │
│ inference_time   │    │ date              │  │ date                 │
│ model_version    │    │ admissions        │  │ temperature          │
│ signal_date_used │    │ created_at        │  │ aqi                  │
│ created_at       │    └───────────────────┘  │ outbreak_index       │
└────────┬─────────┘                           │ mobility_index       │
         │                                     │ created_at           │
         │ 1:N                                 └──────────────────────┘
         ▼
┌──────────────────────────┐
│       forecasts          │
├──────────────────────────┤
│ id (UUID, PK)            │
│ forecast_run_id (FK)     │
│ hospital_id (FK)         │
│ horizon (1–7)            │
│ prediction (Float)       │
│ forecast_date            │
│ created_at               │
├──────────────────────────┤
│ UNIQUE(hospital_id,      │
│   forecast_date, horizon)│
└──────────────────────────┘
```

**Key constraints:**
- All inserts use **UPSERT** (`ON CONFLICT DO UPDATE`) — fully idempotent.
- `forecasts` has a unique constraint on `(hospital_id, forecast_date, horizon)` to prevent duplicates.
- `external_signals` has a unique constraint on `(hospital_id, date)`.
- UUID primary keys throughout.

---

## 📡 API Reference

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API info & endpoint listing |
| `GET` | `/health` | Health check (DB connection, model status) |
| `GET` | `/docs` | Swagger UI documentation |

### Forecast Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/hospitals` | No | List all hospitals |
| `GET` | `/forecast/latest?hospitals=HOSP_1,HOSP_2` | No | Latest precomputed 7-day forecasts |
| `GET` | `/forecast/history?hospitals=HOSP_1&days=30` | No | Historical admission data |
| `GET` | `/system/status` | No | Model version, last run, signal date, hospital count |
| `POST` | `/predict` | JWT | Precomputed forecasts (backward-compatible) |
| `GET` | `/forecasts` | No | Paginated forecast browser with filters |

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create new user account |
| `POST` | `/auth/login` | Login and receive JWT token |
| `GET` | `/auth/me` | Get current user info (JWT required) |

### AI Agent Endpoint

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/agent/query` | JWT | Query AI agent for forecast explanations |

**Request:**
```json
{
  "question": "What should HOSP_1 prepare for next week?"
}
```

**Response:**
```json
{
  "hospital": "HOSP_1",
  "analysis": "## Trend Summary\nPredicted admissions show a rising trend...",
  "inference_time_seconds": 2.341
}
```

### Admin Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/model-info` | Admin | Model metadata & feature list |
| `POST` | `/tasks/fetch-external-signals` | Admin | Trigger external signal fetch |

---

## 🤖 AI Agent Layer

The agent is a **tool-grounded LLM reasoning system** built on the Groq API:

```
User Question
      │
      ▼
┌─────────────────────┐
│ Extract Hospital Code│ ← regex: HOSP_\d+
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Fetch DB Context     │
│  • Hospital metadata │
│  • 7-day forecast    │
│  • 14 recent admits  │
│  • External signals  │
│  • Capacity info     │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Build Structured     │
│ Prompt               │
│  • Pre-computed stats│
│  • AQI severity      │
│  • Capacity util %   │
│  • Trend/Driver/Rec  │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Groq API Call        │
│  • llama-3.3-70b     │
│  • temp=0.2          │
│  • max_tokens=700    │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ Structured Response  │
│  • Trend Summary     │
│  • Key Drivers       │
│  • Recommendations   │
└─────────────────────┘
```

**Safety guarantees:**
- No model training inside the endpoint
- No filesystem writes
- DB session per-request (no global state mutation)
- Graceful failure if Groq API is unavailable
- Inference time logged for every request

---

## ⚙ Automation & CI/CD

Three automated GitHub Actions workflows keep the system alive:

| Workflow | Schedule | Script | Description |
|----------|----------|--------|-------------|
| **Fetch External Signals** | Daily 2:00 AM UTC | `scripts/fetch_external_signals.py` | Fetches weather, AQI from Open-Meteo; computes outbreak & mobility indices; UPSERTs to DB |
| **Daily Forecast** | Daily 2:30 AM UTC | `scripts/daily_forecast_job.py` | Loads model, generates 7-day predictions for all hospitals, UPSERTs forecasts to DB |
| **Weekly Retrain** | Sunday 3:00 AM UTC | `scripts/weekly_retrain.py` | Pulls full admission history, retrains per-horizon LightGBM models |

All workflows:
- Use `DATABASE_URL` from GitHub Secrets
- Install from `requirements-ml.txt` (full ML stack)
- Exit with code 1 on failure
- Cache pip packages for faster runs

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** (or a [Neon](https://neon.tech/) account)

### 1. Clone the repository

```bash
git clone https://github.com/Suparnnayak/agents_ai.git
cd agents_ai
```

### 2. Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install full dependencies (includes ML libraries)
pip install -r requirements-ml.txt
pip install -e .

# Create .env file
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, GROQ_API_KEY
```

### 3. Database Setup

```bash
# Run Alembic migrations
alembic upgrade head

# (Optional) Seed the database from CSV
python -m scripts.seed_db_from_csv
```

### 4. Run Backend

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 5. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000" > .env.local

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

### 6. (Optional) Run Forecast Pipeline Locally

```bash
# Fetch external signals
python -m scripts.fetch_external_signals

# Generate forecasts
python -m scripts.daily_forecast_job

# Retrain model
python -m scripts.weekly_retrain
```

---

## 🔐 Environment Variables

### Backend (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | — | JWT signing secret |
| `GROQ_API_KEY` | ✅ | — | Groq API key for AI agent |
| `GROQ_MODEL` | ❌ | `llama-3.3-70b-versatile` | Groq model identifier |
| `ALLOWED_ORIGINS` | ❌ | `http://localhost:3000,...` | Comma-separated CORS origins |
| `MODEL_PATH` | ❌ | `models/forecast_system/lightgbm_final.pkl` | Path to model bundle |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ❌ | `30` | JWT token expiry |

### Frontend (.env.local)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | — | Backend API URL |

### GitHub Actions Secrets

| Secret | Description |
|--------|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string |

---

## 🚢 Deployment

### Backend (Vercel Serverless)

The backend deploys as a Python serverless function on Vercel:

- Entry point: `api/index.py` (re-exports the FastAPI `app`)
- Runtime: `@vercel/python` with native ASGI support
- Config: `vercel.json` at project root
- Dependencies: `requirements.txt` (~50 MB, well under 500 MB Lambda limit)
- ML libraries are **excluded** from Vercel — forecasts are precomputed in DB

```json
// vercel.json
{
  "version": 2,
  "builds": [{
    "src": "api/index.py",
    "use": "@vercel/python",
    "config": { "maxLambdaSize": "50mb" }
  }],
  "routes": [{ "src": "/(.*)", "dest": "api/index.py" }]
}
```

### Frontend (Vercel)

The frontend deploys as a standard Next.js application:

- Framework: Auto-detected as Next.js
- Config: `frontend/vercel.json`
- Set `NEXT_PUBLIC_API_URL` to your backend URL in Vercel environment variables

### Key Deployment Notes

1. **Split dependencies**: `requirements.txt` for Vercel (slim), `requirements-ml.txt` for GitHub Actions (full ML stack).
2. **Lazy model loading**: ML libraries are imported lazily — if not installed, the server still works (serves precomputed data).
3. **NullPool for serverless**: Database connections use `NullPool` when `VERCEL` env var is detected, preventing connection leaks.
4. **No `create_all` on cold start**: Schema is managed exclusively by Alembic. Cold start only runs `SELECT 1` to verify connectivity.

---

## 🎨 Frontend Pages

| Page | Route | Description |
|------|-------|-------------|
| **Landing** | `/` | Hero section, feature cards, architecture diagram, tech highlights, CTA |
| **Dashboard** | `/dashboard` | Hospital selector, forecast area chart, historical bar chart, external signals panel, AI insights |
| **Hospitals** | `/hospitals` | Searchable hospital directory with capacity, region, last forecast date |
| **AI Agent** | `/agent` | Chat interface for querying the Groq-powered forecast analyst |
| **System** | `/system` | Model version, last retrain, DB health, infrastructure status cards |
| **Login** | `/login` | Email/password sign-in with JWT token storage |
| **Register** | `/register` | Account creation |
| **About** | `/about` | Platform mission & technology overview |
| **Contact** | `/contact` | Contact form with company info |

### Design System

- **Theme**: Dark navy (`#0a0f1e`) with cyan/teal accents
- **Style**: Glassmorphism panels (`backdrop-blur`, `border-white/10`)
- **Typography**: Inter (sans-serif)
- **Charts**: Recharts with custom gradient fills
- **Animations**: Framer Motion for page transitions
- **Responsive**: Fully responsive (desktop, tablet, mobile) with hamburger nav

---

## 📐 Design Principles

1. **PostgreSQL is the single source of truth** — No CSV files in production.
2. **No inference inside request handlers** — Forecasts are precomputed daily.
3. **All inserts use UPSERT** — `ON CONFLICT DO UPDATE` for idempotent writes.
4. **DB session per request** — No global state mutation.
5. **Deterministic predictions** — Same input always produces same output.
6. **Graceful degradation** — ML libraries optional at runtime; Groq failures return clean HTTP errors.
7. **Clean logging** — Structured logging throughout; scripts exit with code 1 on failure.
8. **Zero-CSV architecture** — CSV is only used by the one-time seed script.

---

## 📄 License

This project is built for educational and portfolio purposes.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/Suparnnayak">Suparn Nayak</a>
</p>

