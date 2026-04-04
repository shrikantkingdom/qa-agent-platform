from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # --- Startup ---
    for folder in ["outputs/reports", "outputs/testcases", "outputs/bdd"]:
        Path(folder).mkdir(parents=True, exist_ok=True)
    logger.info(f"{settings.app_name} v{settings.app_version} ready")
    yield
    # --- Shutdown ---
    logger.info(f"{settings.app_name} shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Agentic AI QA Workflow Automation Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — restrict origins in production via environment variable
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# API routes must be registered BEFORE static files mount
app.include_router(router, prefix="/api/v1", tags=["QA Workflow"])

# Serve the single-page UI from /
ui_path = Path("ui")
if ui_path.exists():
    app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
