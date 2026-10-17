"""FastAPI application entrypoint for Integrated Predictive Maintenance Platform."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_v1_router
from app.config import get_settings
from app.core.database import check_database_connection, get_session_factory
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.services.auth_service import ensure_demo_users_exist

setup_logging(level="INFO")
logger = logging.getLogger("fleetmaint")
settings = get_settings()

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for database initialization and demo user provisioning."""
    logger.info("Initializing backend services...")
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await ensure_demo_users_exist(session)
    except Exception as exc:
        logger.warning(f"Demo user check skipped on startup: {exc}")

    yield
    logger.info("Shutting down backend services...")


app = FastAPI(
    title="Integrated Predictive Maintenance & Fleet Availability Platform",
    description="Decision-support platform for aircraft health, maintenance planning, and fleet availability (Synthetic Data).",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register uniform exception handlers
register_exception_handlers(app)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 endpoints
app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, Any]:
    """Check health of the backend API and verify PostgreSQL connectivity."""
    db_result = await check_database_connection()
    is_db_connected = db_result["status"] == "connected"

    overall_status = "healthy" if is_db_connected else "degraded"

    return {
        "status": overall_status,
        "backend": "ok",
        "database": db_result["status"],
        "database_detail": db_result.get("error"),
        "environment": settings.environment,
        "synthetic_data": True,
        "version": "0.1.0",
    }


# Static-file serving and SPA fallback for built frontend (Phase 11 Demo)
if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.get("/", include_in_schema=False)
async def serve_root() -> Any:
    """Serve frontend index.html if built, otherwise return API landing info."""
    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "title": "Integrated Predictive Maintenance & Fleet Availability Platform",
        "version": "0.1.0",
        "status": "operational",
        "synthetic_data": True,
        "notice": "Frontend build not detected in frontend/dist. Run 'python scripts/tasks.py demo' or 'npm run build' in frontend/ to serve the UI.",
        "api_docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa_fallback(full_path: str) -> Any:
    """Serve static files or fallback to index.html for client-side SPA routing."""
    # Do not catch API or swagger endpoints
    if full_path.startswith("api/") or full_path in ("api", "docs", "redoc", "openapi.json"):
        raise HTTPException(status_code=404, detail="API endpoint or resource not found")

    target_file = FRONTEND_DIST / full_path
    if target_file.is_file():
        return FileResponse(target_file)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    raise HTTPException(
        status_code=404,
        detail="Resource not found and frontend/dist/index.html is unavailable",
    )
