# AI Code Review & Quality Assurance System

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19+-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC.svg)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, multi-stage **AI Code Review, Static Application Security Testing (SAST), Dynamic Application Security Testing (DAST), Secret Detection, LLM Governance, and Automated Code Remediation System**.

---

## Key Features

- **Multi-Language SAST Engine**: In-depth AST and heuristic scanning across Python, JavaScript, TypeScript, Go, Java, PHP, Ruby, and C/C++. Detects SQL injections, Command Injections, Insecure Deserialization, Path Traversal, and OWASP Top 10 vulnerabilities.
- **DAST Security Engine**: Automated REST API endpoint spidering, CORS misconfiguration probes, missing security headers checks (CSP, HSTS, X-Frame-Options), and fuzzing.
- **High-Entropy Secret Detection**: Scans repositories for exposed AWS access keys, GitHub tokens, OpenAI/Groq API keys, Stripe secrets, private certificates, and database credentials.
- **AI-Powered Code Review & Remediation**: Intelligent analysis using LLMs (Groq Cloud LLaMA 3.3, OpenAI GPT-4o, Google Gemini, Ollama, or built-in local AST rule engines) to generate line-by-line remediations and 100% production-ready fixed code downloads.
- **LLM Safety & Prompt Governance**: Enforces AI usage policy, scans for Prompt Injections, Jailbreak patterns, sensitive data leakage, and toxic prompt inputs.
- **Executive PDF & JSON Reports**: Generates formal, downloadable compliance reports with severity distributions, OWASP categorization, and audit logs.
- **Dual Storage Architecture**: Native support for **MongoDB Atlas** with automatic fallback to a local thread-safe document store when running offline.

---

## Architecture & Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4, Lucide Icons |
| **Backend** | FastAPI, Uvicorn, Gunicorn, Pydantic v2, Python AST |
| **Database** | MongoDB Atlas (pymongo) / Local JSON Document Store fallback |
| **Security Engines** | Custom Multi-Language AST Analyzer, Bandit, High-Entropy Secret Scanner, DAST Prober |
| **AI Providers** | Groq (`llama-3.3-70b-versatile`), OpenAI (`gpt-4o-mini`), Google Gemini, Ollama, Local Fallback |
| **Reporting** | ReportLab PDF Engine, Structured JSON Exporter |

---

## Deployment to Render

This repository is pre-configured for deployment on [Render](https://render.com).

### Method A: 1-Click Render Blueprint (Recommended)

1. Fork or push this repository to your GitHub account.
2. Sign in to your [Render Dashboard](https://dashboard.render.com).
3. Click **New +** and select **Blueprint**.
4. Connect this GitHub repository.
5. Render reads [`render.yaml`](./render.yaml) and automatically provisions:
   - **`codereview-backend`** (FastAPI Web Service)
   - **`codereview-frontend`** (React Static Site with automatic routing and CDN)
6. Add your environment variables (e.g. `MONGODB_URI`, `GROQ_API_KEY`) when prompted, and click **Apply**.

---

### Method B: Manual Service Creation on Render

If you prefer to configure services manually:

#### 1. Backend Web Service
- **Type**: Web Service
- **Runtime**: Python 3
- **Root Directory**: `.` (leave empty)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/health`
- **Environment Variables**:
  - `AI_PROVIDER`: `local` (or `groq`, `openai`, `gemini`)
  - `MONGODB_URI`: *Your MongoDB connection string*
  - `MONGODB_DB_NAME`: `codereview_db`
  - `GROQ_API_KEY`: *(Optional) Your Groq API key*

#### 2. Frontend Static Site
- **Type**: Static Site
- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Publish Directory**: `dist`
- **Rewrite Rule**: Rewrite `/*` to `/index.html` (under Redirects/Rewrites)
- **Environment Variables**:
  - `VITE_API_URL`: `https://your-backend-name.onrender.com`

---

### Method C: Single-Container Unified Docker Service

You can also deploy as a single service using the included multi-stage [`Dockerfile`](./Dockerfile):
- **Type**: Web Service
- **Environment**: Docker
- **Build & Start**: Render will build the React frontend and run the FastAPI server automatically on port `8000`.

---

## Environment Variables Reference

See [`.env.example`](./.env.example) for a complete template:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Port for the backend server (Render sets this automatically) |
| `HOST` | `0.0.0.0` | Bind host address |
| `DEBUG` | `false` | Enable verbose error traces and debug logs |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `MONGODB_DB_NAME` | `codereview_db` | MongoDB database name |
| `AI_PROVIDER` | `local` | Active AI provider (`local`, `groq`, `openai`, `gemini`, `ollama`) |
| `GROQ_API_KEY` | *(empty)* | API key for Groq Cloud |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Model name for Groq inference |
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key |
| `GITHUB_TOKEN` | *(empty)* | Optional GitHub Personal Access Token for rate limits |

---

## Local Development

### 1. Clone & Set Up Backend

```bash
# Clone the repository
git clone https://github.com/ssathyasai/CodeReviewSystem.git
cd CodeReviewSystem

# Create virtual environment (optional)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn backend.app.main:app --reload --port 8000
```

The interactive API documentation is accessible at:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 2. Set Up Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### 3. Run Automated Tests

```bash
python -m pytest backend/tests -v
```

---

## License

This project is open-source and distributed under the [MIT License](LICENSE).