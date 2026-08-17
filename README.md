# Hybrid Code Intelligence & Governance Agent 🛡️

An enterprise-grade, multi-engine AI code review and security audit platform built with **FastAPI**, **MongoDB**, **PyMongo**, and **React (Vite + Tailwind CSS)**.

---

## ✨ Features & Architecture

- **🔴 MongoDB Cloud Persistence**: Replaced SQLite with MongoDB Atlas / PyMongo for storing projects and scan history.
- **🔴 Production Single-Service**: FastAPI serves both REST/WebSocket APIs and the built React SPA frontend.
- **🔴 Secure GitHub Webhooks**: HMAC SHA-256 signature verification (`X-Hub-Signature-256`) enforced for push webhooks.
- **🟠 Multi-Engine Security Auditing**:
  - **SAST Engine**: AST-based static analyzer for OWASP Top 10 vulnerabilities (SQLi, Hardcoded Secrets, Command Execution).
  - **DAST Engine**: Isolated process execution and runtime profiling (RAM leaks, CPU spikes, timeout detection).
  - **LLM Governance AI**: Policy compliance checker with Groq Llama 3.3 for structured JSON output and inline auto-fixes.
- **🟠 Historical Audit Tracking**: All scan results persisted to MongoDB `scans` collection with searchable REST endpoints.
- **🟡 React SPA Dashboard**: Dark-mode interface with live code scanner, project registry, scan timeline, and GitHub webhook setup guide.

---

## 🛠️ Environment Configuration

Create a `.env` file in the project root:

```ini
# Database Connection
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/codereview_db

# LLM Configuration
GROQ_API_KEY=gsk_your_groq_api_key_here

# Security
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret_key

# Server Configuration
PORT=8000
ENVIRONMENT=production
CORS_ORIGINS=*
```

---

## 🚀 Quick Start

### 1. Backend Setup & Run

```bash
# Install Python dependencies
pip install fastapi uvicorn pymongo python-dotenv psutil requests pyyaml

# Start FastAPI Server (serves API + React frontend)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend Development / Build

```bash
cd frontend
npm install
npm run build
```

---

## 🧪 Testing & CI/CD

Run automated pytest backend tests:

```bash
pytest tests/
```

Continuous integration is pre-configured in `.github/workflows/ci.yml`.