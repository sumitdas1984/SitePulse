"""Check runner for executing health checks."""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Optional
import httpx
from sqlalchemy.orm import Session
from app.models import Monitor, Check
from app.database import SessionLocal


_check_locks: dict[str, asyncio.Lock] = {}


async def run_check(monitor_id: str) -> None:
    """Execute a health check for the given monitor (with duplicate prevention)."""
    lock = _check_locks.setdefault(monitor_id, asyncio.Lock())

    if lock.locked():
        return

    async with lock:
        await _execute_check(monitor_id)


async def _execute_check(monitor_id: str) -> None:
    """Execute the actual health check logic."""
    db = SessionLocal()
    try:
        monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
        if not monitor:
            return

        success = False
        http_status_code: Optional[int] = None
        response_time_ms: Optional[int] = None
        failure_reason: Optional[str] = None

        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(str(monitor.url))
                response_time_ms = int((time.time() - start_time) * 1000)
                http_status_code = response.status_code

                if monitor.expected_status_code is not None:
                    if response.status_code == monitor.expected_status_code:
                        success = True
                    else:
                        failure_reason = "status_mismatch"
                else:
                    if 200 <= response.status_code < 300:
                        success = True
                    else:
                        failure_reason = "status_mismatch"

                if success and monitor.json_assert_key:
                    try:
                        body = response.json()
                        if body.get(monitor.json_assert_key) == monitor.json_assert_value:
                            success = True
                        else:
                            success = False
                            failure_reason = "json_assertion_failed"
                    except (json.JSONDecodeError, ValueError):
                        success = False
                        failure_reason = "json_parse_error"

        except httpx.TimeoutException:
            failure_reason = "timeout"
        except (httpx.ConnectError, httpx.NetworkError):
            failure_reason = "connection_error"
        except Exception:
            failure_reason = "connection_error"

        check = Check(
            monitor_id=monitor_id,
            timestamp=datetime.now(timezone.utc),
            success=success,
            http_status_code=http_status_code,
            response_time_ms=response_time_ms,
            failure_reason=failure_reason,
        )
        db.add(check)

        if success:
            monitor.consecutive_failures = 0
            monitor.alert_suppressed = False
        else:
            monitor.consecutive_failures += 1
            if (
                monitor.consecutive_failures >= monitor.failure_threshold
                and not monitor.alert_suppressed
            ):
                from app.services.alerts import dispatch_alert
                await dispatch_alert(monitor, check)
                monitor.alert_suppressed = True

        db.commit()

    finally:
        db.close()
