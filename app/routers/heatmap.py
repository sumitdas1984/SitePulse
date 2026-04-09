"""Heatmap API endpoints."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Monitor, Check
from app.schemas import HeatmapResponse, HeatmapCell

router = APIRouter()


def classify_hour(successes: int, total: int) -> str:
    """Classify an hourly bucket based on success rate."""
    if total == 0:
        return "no_data"
    if successes == total:
        return "up"
    if successes == 0:
        return "down"
    return "degraded"


@router.get("/{monitor_id}/heatmap", response_model=HeatmapResponse)
def get_heatmap(monitor_id: str, db: Session = Depends(get_db)):
    """Get 90-day hourly heatmap for a monitor."""
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    query = text("""
        SELECT
            strftime('%Y-%m-%dT%H:00:00', timestamp) AS hour,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) AS successes,
            COUNT(*) AS total,
            AVG(response_time_ms) AS avg_latency
        FROM checks
        WHERE monitor_id = :monitor_id
          AND timestamp >= :cutoff
        GROUP BY hour
        ORDER BY hour ASC
    """)

    results = db.execute(query, {"monitor_id": monitor_id, "cutoff": cutoff}).fetchall()

    hour_map = {}
    for row in results:
        hour_str = row[0]
        successes = row[1]
        total = row[2]
        avg_latency = row[3]

        hour_dt = datetime.fromisoformat(hour_str).replace(tzinfo=timezone.utc)
        status = classify_hour(successes, total)
        uptime_pct = (successes / total * 100) if total > 0 else None

        hour_map[hour_dt] = HeatmapCell(
            hour=hour_dt,
            status=status,
            uptime_pct=uptime_pct,
            avg_latency_ms=avg_latency,
        )

    cells = []
    current_hour = cutoff.replace(minute=0, second=0, microsecond=0)
    end_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    while current_hour <= end_hour:
        if current_hour in hour_map:
            cells.append(hour_map[current_hour])
        else:
            cells.append(
                HeatmapCell(
                    hour=current_hour,
                    status="no_data",
                    uptime_pct=None,
                    avg_latency_ms=None,
                )
            )
        current_hour += timedelta(hours=1)

    if len(cells) > 2160:
        cells = cells[-2160:]

    while len(cells) < 2160:
        first_hour = cells[0].hour if cells else end_hour
        new_hour = first_hour - timedelta(hours=1)
        cells.insert(
            0,
            HeatmapCell(
                hour=new_hour,
                status="no_data",
                uptime_pct=None,
                avg_latency_ms=None,
            )
        )

    return HeatmapResponse(monitor_id=monitor_id, cells=cells[:2160])
