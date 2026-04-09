"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import init_db, SessionLocal
from app.worker.scheduler import scheduler, add_monitor_job
from app.models import Monitor
from app.routers import monitors, checks, heatmap, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    init_db()
    scheduler.start()

    db = SessionLocal()
    try:
        existing_monitors = db.query(Monitor).all()
        for monitor in existing_monitors:
            add_monitor_job(monitor)
    finally:
        db.close()

    yield

    scheduler.shutdown()


app = FastAPI(
    title="SitePulse API",
    description="Professional site reliability monitoring",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(monitors.router, prefix="/monitors", tags=["monitors"])
app.include_router(checks.router, prefix="/monitors", tags=["checks"])
app.include_router(heatmap.router, prefix="/monitors", tags=["heatmap"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "SitePulse API"}
