"""System-wide analytics API endpoints."""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db

router = APIRouter()


@router.get("/latency")
def get_latency_trends(db: Session = Depends(get_db)):
    """Get system-wide average latency per hour for the last 24 hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    query = text("""
        SELECT
            strftime('%Y-%m-%dT%H:00:00', timestamp) AS hour,
            AVG(response_time_ms) AS avg_latency
        FROM checks
        WHERE timestamp >= :cutoff
          AND response_time_ms IS NOT NULL
        GROUP BY hour
        ORDER BY hour ASC
    """)

    results = db.execute(query, {"cutoff": cutoff}).fetchall()

    data = [
        {
            "hour": row[0],
            "avg_latency_ms": row[1]
        }
        for row in results
    ]

    return data


@router.get("/incidents")
def get_incidents(db: Session = Depends(get_db)):
    """Get recent failed checks for the last 7 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    query = text("""
        SELECT
            c.timestamp,
            m.name AS monitor_name,
            c.failure_reason,
            CASE
                WHEN m.consecutive_failures >= m.failure_threshold THEN 'Critical'
                WHEN m.consecutive_failures >= 2 THEN 'High'
                ELSE 'Medium'
            END AS severity
        FROM checks c
        JOIN monitors m ON c.monitor_id = m.id
        WHERE c.timestamp >= :cutoff
          AND c.success = 0
        ORDER BY c.timestamp DESC
        LIMIT 100
    """)

    results = db.execute(query, {"cutoff": cutoff}).fetchall()

    incidents = [
        {
            "timestamp": row[0],
            "monitor_name": row[1],
            "failure_reason": row[2] or "unknown",
            "severity": row[3]
        }
        for row in results
    ]

    return incidents
