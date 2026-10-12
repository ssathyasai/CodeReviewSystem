import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
REPORTS_DIR = DATA_DIR / "reports"
WORKSPACES_DIR = DATA_DIR / "workspaces"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)


def get_env_str(key: str, default: str = "") -> str:
    val = os.getenv(key, default)
    if not val:
        return default
    return val.strip().strip('"').strip("'").replace("\r", "").replace("\n", "").strip()


class Settings(BaseModel):
    APP_NAME: str = "AI Code Review & Quality Assurance System"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Server
    HOST: str = get_env_str("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]
    
    # Database
    MONGODB_URI: str = get_env_str("MONGODB_URI", "mongodb://localhost:27017")
    MONGODB_DB_NAME: str = get_env_str("MONGODB_DB_NAME", "codereview_db")
    
    # AI Providers
    AI_PROVIDER: str = get_env_str("AI_PROVIDER", "local")  # "openai", "gemini", "ollama", "groq", "local"
    OPENAI_API_KEY: str = get_env_str("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = get_env_str("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = get_env_str("GROQ_API_KEY", "")
    GROQ_MODEL: str = get_env_str("GROQ_MODEL", "llama-3.3-70b-versatile")
    OLLAMA_URL: str = get_env_str("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = get_env_str("OLLAMA_MODEL", "qwen2.5-coder:latest")
    OPENAI_MODEL: str = get_env_str("OPENAI_MODEL", "gpt-4o-mini")
    
    # GitHub Integration
    GITHUB_TOKEN: str = get_env_str("GITHUB_TOKEN", "")
    
    # Scan Limits & Security
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    MAX_EXTRACTED_SIZE_MB: int = int(os.getenv("MAX_EXTRACTED_SIZE_MB", "200"))
    MAX_ARCHIVE_FILES: int = int(os.getenv("MAX_ARCHIVE_FILES", "5000"))
    MAX_SCAN_TIME_SECONDS: int = int(os.getenv("MAX_SCAN_TIME_SECONDS", "300"))
    
    # DAST Safety
    DAST_TIMEOUT_SECONDS: int = int(os.getenv("DAST_TIMEOUT_SECONDS", "60"))
    DAST_ALLOW_LOCAL_TARGETS: bool = os.getenv("DAST_ALLOW_LOCAL_TARGETS", "true").lower() == "true"
    ZAP_API_URL: str = os.getenv("ZAP_API_URL", "http://localhost:8080")
    ZAP_API_KEY: str = os.getenv("ZAP_API_KEY", "")

    # Storage paths
    DATA_DIR: Path = DATA_DIR
    UPLOADS_DIR: Path = UPLOADS_DIR
    REPORTS_DIR: Path = REPORTS_DIR
    WORKSPACES_DIR: Path = WORKSPACES_DIR


settings = Settings()
