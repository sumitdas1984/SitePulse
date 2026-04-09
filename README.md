# SitePulse 📡

**Professional Site Reliability Monitoring**

SitePulse is a self-hosted site reliability monitor with FastAPI backend, APScheduler for automated checks, and a beautiful Streamlit dashboard.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🔍 **HTTP/HTTPS Monitoring** - Monitor any web endpoint with configurable intervals (1-1440 minutes)
- 📊 **90-Day Heatmap** - Visualize availability with hourly granularity
- 📈 **Real-time Analytics** - System-wide latency trends and incident tracking
- 🚨 **Smart Alerting** - Email (SMTP) and webhook notifications with configurable failure thresholds
- ⚡ **JSON Assertions** - Validate API response content, not just status codes
- 🎯 **Failure Tracking** - Consecutive failure counting with alert suppression

## Prerequisites

- Python 3.13+
- SQLite (bundled with Python)
- SMTP server (optional, for email alerts)

## Quick Start

```bash
# 1. Install dependencies
pip install -e .

# 2. Set up environment (optional for basic usage)
cp .env.example .env

# 3. Start the backend
uvicorn app.main:app --reload &

# 4. Start the frontend
streamlit run sitepulse_app.py
```

Open your browser to `http://localhost:8501` and start monitoring!

## Installation

### 1. Clone and Install

```bash
git clone <repository-url>
cd sitepulse
pip install -e .[dev]  # Include [dev] for testing dependencies
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Database
DATABASE_URL=sqlite:///./sitepulse.db

# SMTP (optional - for email alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=sitepulse@yourcompany.com

# API (for frontend)
API_BASE_URL=http://localhost:8000
```

**Note**: For Gmail, you'll need to use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

## Running the Application

### 1. Start the FastAPI Backend

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

### 2. Start the Streamlit Frontend

In a separate terminal:

```bash
streamlit run sitepulse_app.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Usage

### Creating a Monitor

1. Navigate to the **Management** page in the Streamlit dashboard
2. Fill in the monitor details:
   - **Service Name**: Display name for the monitor
   - **Target URL**: HTTP/HTTPS endpoint to monitor
   - **Check Interval**: How often to check (1-1440 minutes)
   - **Alert Email** (optional): Email address for failure notifications
   - **Webhook URL** (optional): Webhook endpoint for failure notifications
   - **Failure Threshold**: Number of consecutive failures before alerting (1-10)
3. Click **Initialize Monitor**

### Advanced Monitoring

**Expected Status Code**: Set a specific HTTP status code (e.g., `200`, `201`, `204`)
- If not set, any 2xx status code is considered successful

**JSON Assertions**: Validate API response content
- Set `json_assert_key` to the JSON key path
- Set `json_assert_value` to the expected value

Example: For `{"status": "healthy"}`, set key=`status` and value=`healthy`

### Viewing Metrics

- **Dashboard**: Overview of all monitors with 90-day heatmaps
- **Analytics**: System-wide latency trends and incident log
- **Management**: Configure and delete monitors

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Streamlit     │  HTTP   │   FastAPI       │
│   Frontend      │────────▶│   Backend       │
└─────────────────┘         └─────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌───────────┐    ┌───────────┐    ┌───────────┐
            │ SQLAlchemy│    │APScheduler│    │  httpx    │
            │  (SQLite) │    │  (Checks) │    │ (Alerts)  │
            └───────────┘    └───────────┘    └───────────┘
```

### Components

- **FastAPI Backend** (`app/main.py`) - REST API for monitor management
- **APScheduler** (`app/worker/scheduler.py`) - Background job scheduler
- **Check Runner** (`app/worker/runner.py`) - Executes health checks
- **Alert Service** (`app/services/`) - Email and webhook notifications
- **Streamlit Frontend** (`sitepulse_app.py`) - Dashboard UI

## API Endpoints

### Monitors
- `GET /monitors` - List all monitors
- `POST /monitors` - Create a monitor
- `GET /monitors/{id}` - Get monitor details
- `PUT /monitors/{id}` - Update a monitor
- `DELETE /monitors/{id}` - Delete a monitor

### Checks & Stats
- `GET /monitors/{id}/checks` - Get check history (with optional `start`/`end` filters)
- `GET /monitors/{id}/stats` - Get uptime and latency stats (with `window_hours` parameter)

### Heatmap
- `GET /monitors/{id}/heatmap` - Get 90-day hourly heatmap (2160 cells)

### Analytics
- `GET /analytics/latency` - System-wide latency trends (last 24h)
- `GET /analytics/incidents` - Recent incidents (last 7 days)

## API Usage Examples

### Create a Monitor

```bash
curl -X POST http://localhost:8000/monitors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My API",
    "url": "https://api.example.com/health",
    "interval_minutes": 5,
    "expected_status_code": 200,
    "alert_email": "ops@company.com",
    "failure_threshold": 3
  }'
```

### Get Monitor Stats

```bash
curl http://localhost:8000/monitors/{monitor_id}/stats?window_hours=24
```

### View Heatmap Data

```bash
curl http://localhost:8000/monitors/{monitor_id}/heatmap
```

### List All Incidents

```bash
curl http://localhost:8000/analytics/incidents
```

## Testing

Run the full test suite:

```bash
pytest tests/ -v
```

Run specific test types:

```bash
# Property-based tests
pytest tests/test_properties.py -v

# Integration tests
pytest tests/test_integration.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

## Configuration Details

### Monitor Configuration Options

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✅ | - | Display name for the monitor |
| `url` | URL | ✅ | - | HTTP/HTTPS endpoint to monitor |
| `interval_minutes` | int (1-1440) | ✅ | - | Check frequency in minutes |
| `expected_status_code` | int | ❌ | null | Specific status code to expect (e.g., 200). If null, any 2xx is OK |
| `json_assert_key` | string | ❌ | null | JSON key path to validate |
| `json_assert_value` | string | ❌ | null | Expected value for JSON assertion |
| `alert_email` | email | ❌ | null | Email address for alerts |
| `webhook_url` | URL | ❌ | null | Webhook endpoint for alerts |
| `failure_threshold` | int (1-10) | ❌ | 3 | Consecutive failures before alerting |

### Alert Behavior

- Alerts fire **once** when the failure threshold is reached
- Alerts are **suppressed** until the service recovers
- On recovery, the failure counter resets and alert suppression is cleared
- Email and webhook alerts are **best-effort** (failures are logged but don't crash the system)

### Heatmap Status Colors

| Status | Color | Meaning |
|--------|-------|---------|
| 🟢 **up** | Green | 100% successful checks in that hour |
| 🟠 **degraded** | Amber | Partial failures (some checks failed) |
| 🔴 **down** | Red | All checks failed in that hour |
| ⚪ **no_data** | Grey | No checks recorded for that hour |

## Troubleshooting

### API won't start

**Error**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Install dependencies
```bash
pip install -e .
```

### Scheduler not running checks

**Check**: Verify monitors are created and scheduler started
```bash
curl http://localhost:8000/monitors
```

**Solution**: Restart the API - the scheduler loads existing monitors on startup

### Email alerts not working

**Check**: Verify SMTP configuration in `.env`

**Common issues**:
- Gmail requires an App Password, not your regular password
- Port 587 requires STARTTLS (default in our implementation)
- Check firewall rules if using a custom SMTP server

**Test SMTP manually**:
```python
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
# If this works, SitePulse will work too
```

### Streamlit shows "API: UNREACHABLE"

**Check**: Is the FastAPI backend running?
```bash
curl http://localhost:8000/
```

**Solution**: Start the backend first
```bash
uvicorn app.main:app --reload
```

### Database locked error

**Cause**: SQLite doesn't handle high concurrency well

**Solution**: For production with many monitors, switch to PostgreSQL:
```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/sitepulse
```

## Development

### Project Structure

```
sitepulse/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── database.py          # SQLAlchemy configuration
│   ├── models.py            # ORM models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/
│   │   ├── monitors.py      # Monitor CRUD
│   │   ├── checks.py        # Check history & stats
│   │   ├── heatmap.py       # Heatmap data
│   │   └── analytics.py     # System analytics
│   ├── worker/
│   │   ├── scheduler.py     # APScheduler service
│   │   └── runner.py        # Check execution
│   └── services/
│       ├── alerts.py        # Alert dispatcher
│       ├── email_alert.py   # SMTP alerting
│       └── webhook_alert.py # Webhook alerting
├── tests/
│   ├── conftest.py
│   ├── test_properties.py   # Property-based tests
│   └── test_integration.py  # Integration tests
├── sitepulse_app.py         # Streamlit dashboard
├── pyproject.toml
└── README.md
```

### Adding a New Router

1. Create `app/routers/my_router.py`:
```python
from fastapi import APIRouter
router = APIRouter()

@router.get("/my-endpoint")
def my_endpoint():
    return {"status": "ok"}
```

2. Register in `app/main.py`:
```python
from app.routers import my_router
app.include_router(my_router.router, prefix="/my", tags=["my"])
```

### Running in Production

**Use a production ASGI server**:
```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Run as systemd service** (Linux):
```ini
# /etc/systemd/system/sitepulse-api.service
[Unit]
Description=SitePulse API
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/sitepulse
Environment="PATH=/opt/sitepulse/.venv/bin"
ExecStart=/opt/sitepulse/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

**For Streamlit**:
```ini
# /etc/systemd/system/sitepulse-ui.service
[Unit]
Description=SitePulse UI
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/sitepulse
Environment="PATH=/opt/sitepulse/.venv/bin"
ExecStart=/opt/sitepulse/.venv/bin/streamlit run sitepulse_app.py --server.port 8501

[Install]
WantedBy=multi-user.target
```

## Roadmap

- [ ] Postgres/MySQL support for high-scale deployments
- [ ] Multi-region monitoring (distributed checks)
- [ ] Slack integration (native, not just webhooks)
- [ ] PagerDuty integration
- [ ] Custom dashboards and visualization
- [ ] Synthetic monitoring (multi-step flows)
- [ ] SSL certificate expiry monitoring
- [ ] Response time SLA tracking
- [ ] Maintenance windows

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

### Development Setup

```bash
# Clone and install with dev dependencies
git clone <repository-url>
cd sitepulse
pip install -e .[dev]

# Run tests
pytest tests/ -v

# Check code formatting (if using ruff/black)
ruff check app/ tests/
```

## Acknowledgments

Built with these amazing tools:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [APScheduler](https://apscheduler.readthedocs.io/) - Job scheduling
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM and database toolkit
- [Streamlit](https://streamlit.io/) - Rapid UI development
- [httpx](https://www.python-httpx.org/) - Async HTTP client
- [Plotly](https://plotly.com/) - Interactive visualizations

---

Built with ❤️ by the SitePulse team