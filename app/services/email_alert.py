"""Email alert service using SMTP."""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models import Monitor, Check


async def send_email_alert(monitor: Monitor, last_check: Check) -> None:
    """Send an email alert for a failed monitor."""
    if not monitor.alert_email:
        return

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", "sitepulse@yourcompany.com")

    if not smtp_host or not smtp_username or not smtp_password:
        print(f"ERROR: SMTP not configured for monitor {monitor.id}")
        return

    subject = f"[SitePulse Alert] {monitor.name} is DOWN"
    body = f"""Monitor:   {monitor.name}
URL:       {monitor.url}
Failures:  {monitor.consecutive_failures} consecutive
Last fail: {last_check.timestamp} UTC

SitePulse — Professional Site Reliability Monitor"""

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = monitor.alert_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"ERROR monitor_id={monitor.id} smtp_error={e}")
