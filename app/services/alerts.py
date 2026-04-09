"""Alert dispatch coordinator."""

from app.models import Monitor, Check
from app.services.email_alert import send_email_alert
from app.services.webhook_alert import send_webhook_alert


async def dispatch_alert(monitor: Monitor, last_check: Check) -> None:
    """Dispatch alerts via email and webhook based on monitor configuration."""
    if monitor.alert_email:
        await send_email_alert(monitor, last_check)

    if monitor.webhook_url:
        await send_webhook_alert(monitor, last_check)
