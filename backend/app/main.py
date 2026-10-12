import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from bson import ObjectId
from fastapi.encoders import ENCODERS_BY_TYPE

# Ensure MongoDB ObjectId is properly serializable by FastAPI
ENCODERS_BY_TYPE[ObjectId] = str

from backend.app.config import settings
from backend.app.db.mongo import db
from backend.app.api.api_v1 import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("codereview.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AI Code Review & Quality Assurance System...")
    db.connect()
    logger.info(f"Database operational. Mode: {'MongoDB' if not db.use_fallback else 'Local Document Store'}")
    yield
    logger.info("Shutting down AI Code Review & Quality Assurance System...")


app = FastAPI(
    title="AI Code Review & Quality Assurance System API",
    description="Multi-language SAST, DAST, Secret Detection, LLM Governance, and AI Code Review Pipeline.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error processing {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "ERROR",
            "message": "An internal server error occurred.",
            "detail": str(exc) if settings.DEBUG else "Please check server logs."
        }
    )

# Include API Router
app.include_router(api_router, prefix="/api")

# Serve frontend static assets if built (for unified production deployment on Render)
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if frontend_dist.is_dir() and (frontend_dist / "index.html").is_file():
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa_frontend(full_path: str):
        if full_path.startswith("api/") or full_path == "api" or full_path in ["docs", "redoc", "openapi.json"]:
            raise HTTPException(status_code=404, detail="Not Found")
        
        target_file = frontend_dist / full_path
        if full_path and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "ONLINE",
            "docs": "/docs",
            "dashboard_ui": "http://localhost:5173"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
