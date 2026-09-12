# VeriGate

> AI-powered Software Verification Management Platform for modern engineering and QA teams.

---

## Key Features

- **Verification Command Center**: Real-time operational dashboard with verification metrics, pass rates, project health telemetry, and activity trends.
- **AI Failure Detective**: Automated root-cause analysis for failed and blocked tests powered by LLM diagnostics with actionable remediation suggestions.
- **Smart Verification Reports**: Professional, audit-ready verification reports exportable to PDF and JSON, complete with evidence attachments and secret sanitization.
- **GitHub PR Verification**: Seamless CI/CD integration that triggers automated verification runs on pull requests, verifies HMAC signatures, and posts commit status checks back to GitHub.
- **Playwright Testing**: Automated browser test execution with step-by-step actions, assertion validation, and automated screenshot evidence capture.

---

## Tech Stack

- **Frontend**: React 19, Vite, React Router 7, Lucide React
- **Backend**: FastAPI, Python 3.10+, SQLAlchemy, Alembic, Pydantic v2
- **Testing & Automation**: Playwright, Pytest, Node Test Runner
- **Database**: PostgreSQL (via psycopg)

---

## Project Structure

```
VeriGate/
├── Backend/
│   ├── alembic/          # Database migrations
│   ├── app/
│   │   ├── api/          # Route handlers (auth, runs, github, reports, etc.)
│   │   ├── core/         # Configuration and security settings
│   │   ├── db/           # Database engine and base models
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Verification engine, GitHub service, AI diagnostics
│   └── tests/            # Backend test suite
└── frontend/
    ├── src/
    │   ├── api/          # Typed API client
    │   ├── components/   # Reusable UI components
    │   ├── pages/        # Dashboard, Runs, GitHub PRs, Reports, etc.
    │   └── App.jsx       # Application routing and shell
    └── tests/            # Frontend unit and integration tests
```

---

## Installation

### Prerequisites
- Node.js 18+ & npm
- Python 3.10+
- PostgreSQL database

### 1. Backend Setup

```bash
cd Backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

---

## Environment Variables

Create a `.env` file inside the `Backend/` directory:

```ini
# Database & Authentication
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/verigate
AUTH_SECRET_KEY=your-secure-random-secret-key

# URLs
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173

# Optional: AI Failure Detective (Google Gemini or OpenAI)
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key

# Optional: GitHub Integration
GITHUB_TOKEN=your-github-personal-access-token
WEBHOOK_BASE_URL=https://your-public-domain-or-ngrok.app
```

---

## Running the Application

### 1. Apply Database Migrations

```bash
cd Backend
alembic upgrade head
```

### 2. Start Backend Server

```bash
cd Backend
uvicorn app.main:app --reload --port 8000
```
Backend will run at `http://localhost:8000` (API documentation at `http://localhost:8000/docs`).

### 3. Start Frontend Development Server

```bash
cd frontend
npm run dev
```
Frontend will be available at `http://localhost:5173`.
