"""Webhook alert service using httpx."""

import httpx
from app.models import Monitor, Check


async def send_webhook_alert(monitor: Monitor, last_check: Check) -> None:
    """Send a webhook alert for a failed monitor."""
    if not monitor.webhook_url:
        return

    payload = {
        "monitor_name": monitor.name,
        "url": str(monitor.url),
        "consecutive_failures": monitor.consecutive_failures,
        "last_failed_at": last_check.timestamp.isoformat(),
        "event": "threshold_reached",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(str(monitor.webhook_url), json=payload)
            if not (200 <= response.status_code < 300):
                print(
                    f"ERROR monitor_id={monitor.id} webhook_url={monitor.webhook_url} "
                    f"status={response.status_code}"
                )
    except httpx.TimeoutException:
        print(f"ERROR monitor_id={monitor.id} webhook_url={monitor.webhook_url} reason=timeout")
    except Exception as e:
        print(f"ERROR monitor_id={monitor.id} webhook_url={monitor.webhook_url} error={e}")
