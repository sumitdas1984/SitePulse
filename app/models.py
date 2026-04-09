"""SQLAlchemy ORM models for SitePulse."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Monitor(Base):
    """Monitor configuration and state."""

    __tablename__ = "monitors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    json_assert_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    json_assert_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    alert_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    failure_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_suppressed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    checks: Mapped[list["Check"]] = relationship(
        "Check",
        back_populates="monitor",
        cascade="all, delete-orphan"
    )


class Check(Base):
    """Health check execution result."""

    __tablename__ = "checks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    monitor_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("monitors.id", ondelete="CASCADE"),
        nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    http_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    monitor: Mapped["Monitor"] = relationship("Monitor", back_populates="checks")
