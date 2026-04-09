"""Monitor CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Monitor
from app.schemas import MonitorCreate, MonitorRead, MonitorUpdate
from app.worker.scheduler import add_monitor_job, remove_monitor_job, reschedule_monitor_job

router = APIRouter()


@router.get("", response_model=list[MonitorRead])
def list_monitors(db: Session = Depends(get_db)):
    """Get all monitors."""
    monitors = db.query(Monitor).all()
    return monitors


@router.post("", response_model=MonitorRead, status_code=201)
def create_monitor(monitor_data: MonitorCreate, db: Session = Depends(get_db)):
    """Create a new monitor."""
    monitor = Monitor(
        name=monitor_data.name,
        url=str(monitor_data.url),
        interval_minutes=monitor_data.interval_minutes,
        expected_status_code=monitor_data.expected_status_code,
        json_assert_key=monitor_data.json_assert_key,
        json_assert_value=monitor_data.json_assert_value,
        alert_email=monitor_data.alert_email,
        webhook_url=str(monitor_data.webhook_url) if monitor_data.webhook_url else None,
        failure_threshold=monitor_data.failure_threshold,
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)

    add_monitor_job(monitor)

    return monitor


@router.get("/{monitor_id}", response_model=MonitorRead)
def get_monitor(monitor_id: str, db: Session = Depends(get_db)):
    """Get a single monitor by ID."""
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.put("/{monitor_id}", response_model=MonitorRead)
def update_monitor(
    monitor_id: str,
    monitor_data: MonitorUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing monitor."""
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    old_interval = monitor.interval_minutes
    update_dict = monitor_data.model_dump(exclude_unset=True)

    for field, value in update_dict.items():
        if field in ("url", "webhook_url") and value is not None:
            setattr(monitor, field, str(value))
        else:
            setattr(monitor, field, value)

    db.commit()
    db.refresh(monitor)

    if "interval_minutes" in update_dict and monitor.interval_minutes != old_interval:
        reschedule_monitor_job(monitor)

    return monitor


@router.delete("/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: str, db: Session = Depends(get_db)):
    """Delete a monitor and all its checks."""
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")

    remove_monitor_job(monitor_id)
    db.delete(monitor)
    db.commit()

    return None
