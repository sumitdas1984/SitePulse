# SitePulse 📡

**Professional Site Reliability Monitoring**

SitePulse is a self-hosted site reliability monitor with FastAPI backend, APScheduler for automated checks, and a beautiful Streamlit dashboard.

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

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sitepulse
   ```

2. **Install dependencies**
   ```bash
   pip install -e .[dev]
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

   Required environment variables:
   - `DATABASE_URL` - SQLite database path (default: `sqlite:///./sitepulse.db`)
   - `SMTP_HOST` - SMTP server hostname (e.g., `smtp.gmail.com`)
   - `SMTP_PORT` - SMTP port (default: `587`)
   - `SMTP_USERNAME` - SMTP authentication username
   - `SMTP_PASSWORD` - SMTP authentication password
   - `SMTP_FROM` - Email sender address
   - `API_BASE_URL` - Backend API URL (default: `http://localhost:8000`)

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

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Run property-based tests:

```bash
pytest tests/test_properties.py -v
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

## License

MIT

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

Built with ❤️ using FastAPI, APScheduler, SQLAlchemy, and Streamlit