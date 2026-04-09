"""Checks and statistics API endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Monitor, Check
from app.schemas import CheckRead, UptimeStats

router = APIRouter()


@router.get("/{monitor_id}/checks", response_model=list[CheckRead])
def get_checks(
    monitor_id: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get check history for a monitor with optional time window."""
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    query = db.query(Check).filter(Check.monitor_id == monitor_id)

    if start:
        query = query.filter(Check.timestamp >= start)
    if end:
        query = query.filter(Check.timestamp <= end)

    checks = query.order_by(Check.timestamp.desc()).all()
    return checks


@router.get("/{monitor_id}/stats", response_model=UptimeStats)
def get_stats(
    monitor_id: str,
    window_hours: int = Query(default=24, ge=1),
    db: Session = Depends(get_db)
):
    """Get uptime and latency statistics for a monitor."""
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

    checks = db.query(Check).filter(
        Check.monitor_id == monitor_id,
        Check.timestamp >= cutoff
    ).all()

    total_checks = len(checks)
    successful_checks = sum(1 for c in checks if c.success)

    uptime_pct = None
    avg_latency_ms = None

    if total_checks > 0:
        uptime_pct = (successful_checks / total_checks) * 100

        latencies = [c.response_time_ms for c in checks if c.response_time_ms is not None]
        if latencies:
            avg_latency_ms = sum(latencies) / len(latencies)

    return UptimeStats(
        monitor_id=monitor_id,
        window_hours=window_hours,
        uptime_pct=uptime_pct,
        avg_latency_ms=avg_latency_ms,
        total_checks=total_checks,
        successful_checks=successful_checks,
    )
