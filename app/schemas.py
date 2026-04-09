"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, HttpUrl, EmailStr, Field, ConfigDict


class MonitorCreate(BaseModel):
    """Schema for creating a new monitor."""

    name: str
    url: HttpUrl
    interval_minutes: int = Field(ge=1, le=1440)
    expected_status_code: Optional[int] = None
    json_assert_key: Optional[str] = None
    json_assert_value: Optional[str] = None
    alert_email: Optional[EmailStr] = None
    webhook_url: Optional[HttpUrl] = None
    failure_threshold: int = Field(default=3, ge=1, le=10)


class MonitorUpdate(BaseModel):
    """Schema for updating an existing monitor."""

    name: Optional[str] = None
    url: Optional[HttpUrl] = None
    interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    expected_status_code: Optional[int] = None
    json_assert_key: Optional[str] = None
    json_assert_value: Optional[str] = None
    alert_email: Optional[EmailStr] = None
    webhook_url: Optional[HttpUrl] = None
    failure_threshold: Optional[int] = Field(default=None, ge=1, le=10)


class MonitorRead(BaseModel):
    """Schema for reading monitor data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    url: str
    interval_minutes: int
    expected_status_code: Optional[int] = None
    json_assert_key: Optional[str] = None
    json_assert_value: Optional[str] = None
    alert_email: Optional[str] = None
    webhook_url: Optional[str] = None
    failure_threshold: int
    consecutive_failures: int
    alert_suppressed: bool
    created_at: datetime


class CheckRead(BaseModel):
    """Schema for reading check data."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    monitor_id: str
    timestamp: datetime
    success: bool
    http_status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    failure_reason: Optional[str] = None


class HeatmapCell(BaseModel):
    """Single hourly cell in the heatmap."""

    hour: datetime
    status: Literal["up", "degraded", "down", "no_data"]
    uptime_pct: Optional[float] = None
    avg_latency_ms: Optional[float] = None


class HeatmapResponse(BaseModel):
    """Complete heatmap data for a monitor."""

    monitor_id: str
    cells: list[HeatmapCell]


class UptimeStats(BaseModel):
    """Uptime and latency statistics for a monitor."""

    monitor_id: str
    window_hours: int
    uptime_pct: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    total_checks: int
    successful_checks: int
