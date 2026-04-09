# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SitePulse is a self-hosted site reliability monitoring system with three runtime components:
1. **FastAPI backend** (single process) - REST API + embedded APScheduler for health checks
2. **Streamlit frontend** (separate process) - Dashboard UI that polls the API
3. **SQLite database** - Persistent storage via SQLAlchemy ORM

**Critical architectural constraint**: The scheduler runs INSIDE the FastAPI process (same event loop), not as a separate worker. This is managed via the FastAPI lifespan hook.

## Development Commands

```bash
# Install (with dev dependencies)
pip install -e .[dev]

# Run backend (API + scheduler in one process)
uvicorn app.main:app --reload

# Run frontend (separate terminal)
streamlit run sitepulse_app.py

# Run all tests
pytest tests/ -v

# Run specific test types
pytest tests/test_properties.py -v      # Property-based tests
pytest tests/test_integration.py -v     # Integration tests

# Run single test
pytest tests/test_integration.py::test_create_monitor -v
```

## Architecture: Single-Process Design

The backend uses a **single-process architecture** where APScheduler's `AsyncIOScheduler` runs in the same event loop as FastAPI:

```
FastAPI app startup (app/main.py lifespan)
  ├─ init_db()                    # Create tables
  ├─ scheduler.start()            # Start APScheduler
  ├─ Seed existing monitors       # Schedule jobs for all DB monitors
  └─ yield (app runs)
  └─ scheduler.shutdown()         # Clean shutdown
```

When monitors are created/updated/deleted via API endpoints, the scheduler must be updated synchronously:
- **Create monitor** → `add_monitor_job(monitor)`
- **Update monitor interval** → `reschedule_monitor_job(monitor)`
- **Delete monitor** → `remove_monitor_job(monitor_id)`

**Why this matters**: The scheduler and API share the same process. If you add a new monitor endpoint, you MUST update the scheduler in the same transaction/request handler.

## Check Execution Flow

Health checks are triggered by APScheduler and run via `app/worker/runner.py`:

```python
# Scheduler triggers this every interval_minutes
async def run_check(monitor_id: str) -> None:
    # Per-monitor lock prevents duplicate concurrent checks
    lock = _check_locks.setdefault(monitor_id, asyncio.Lock())
    if lock.locked():
        return  # Skip if already running
    
    async with lock:
        # 1. Load monitor from DB
        # 2. httpx.get(url) with 30s timeout
        # 3. Evaluate success (status code + optional JSON assertion)
        # 4. Persist Check record
        # 5. Update monitor.consecutive_failures
        # 6. Trigger alerts if threshold reached
```

**Critical pattern**: Each monitor has its own `asyncio.Lock` (stored in module-level dict) to prevent duplicate concurrent checks if a job runs long or scheduler interval is too short.

## Database Session Management

- **FastAPI requests**: Use `Depends(get_db)` dependency injection (session per request)
- **Background checks**: Create `SessionLocal()` directly, use try/finally to close
- **Cascade delete**: Monitor deletion automatically removes all associated Check records (FK constraint with `ondelete="CASCADE"`)

## Router Structure

Each router maps to a specific resource/concern:

| Router | Prefix | Purpose |
|--------|--------|---------|
| `monitors.py` | `/monitors` | CRUD + scheduler synchronization |
| `checks.py` | `/monitors/{id}/checks` | Check history + stats (uptime/latency) |
| `heatmap.py` | `/monitors/{id}/heatmap` | 90-day hourly heatmap (always 2160 cells) |
| `analytics.py` | `/analytics` | System-wide metrics (all monitors) |

**Pattern**: Routers that modify monitors (create/update/delete) MUST also update the scheduler. Routers that read data do NOT touch the scheduler.

## Heatmap Implementation

The heatmap endpoint always returns exactly **2160 cells** (90 days × 24 hours):
- Runs SQL aggregation query (GROUP BY hour)
- Fills gaps with `no_data` status
- Trims/pads to exactly 2160 cells
- Oldest-first ordering

**Classification logic** (`classify_hour`):
- `total == 0` → `no_data`
- `successes == total` → `up`
- `successes == 0` → `down`
- Otherwise → `degraded`

This is a pure function tested via property-based tests (see `tests/test_properties.py`).

## Alert System

Alerts fire when `consecutive_failures >= failure_threshold`:

```python
if consecutive_failures >= threshold and not alert_suppressed:
    await dispatch_alert(monitor, check)
    monitor.alert_suppressed = True  # Suppress until success
```

**State machine**:
- Failures increment counter
- At threshold, fire alert ONCE and suppress
- On success, reset counter and unsuppress
- Alerts are best-effort (SMTP/webhook failures are logged, not raised)

## Frontend Architecture

The Streamlit app (`sitepulse_app.py`) is stateless and polls the API:
- Uses `httpx` client with `API_BASE_URL` from env
- Auto-refresh via `time.sleep(1) + st.rerun()` countdown timer (60s max)
- Never touches the database directly (all data via API)

**Pattern**: When adding a new API endpoint, add corresponding client call in the appropriate `show_*()` function.

## Testing Strategy

- **Property-based tests** (`test_properties.py`): Pure business logic (classify_hour, uptime formula, validation ranges)
- **Integration tests** (`test_integration.py`): Full CRUD lifecycle, cascade delete, API contracts
- **Test DB**: Uses in-memory SQLite via `conftest.py` fixture

**When adding features**:
- Pure functions → property-based test with `@given` from hypothesis
- API endpoints → integration test with TestClient
- Database behavior → integration test with test_db fixture

## Configuration

Environment variables (`.env`):
- `DATABASE_URL` - SQLite or PostgreSQL connection string
- `SMTP_*` - Email alert configuration (optional)
- `API_BASE_URL` - Frontend→backend connection

**SQLite limitation**: Single-writer. For production with many monitors, use PostgreSQL.

## Common Modifications

### Adding a new monitor field
1. Add column to `Monitor` model (`app/models.py`)
2. Add field to `MonitorCreate`/`MonitorUpdate`/`MonitorRead` schemas (`app/schemas.py`)
3. Update `create_monitor` in `app/routers/monitors.py` to handle the field
4. Database migration: Delete `sitepulse.db` (dev) or use Alembic (prod)

### Adding a new check evaluation criterion
1. Modify `_execute_check` in `app/worker/runner.py`
2. Add failure reason to `failure_reason` field
3. Add property-based test in `tests/test_properties.py`

### Adding a new alert channel
1. Create `app/services/<channel>_alert.py` with `send_<channel>_alert()`
2. Update `dispatch_alert()` in `app/services/alerts.py`
3. Add configuration fields to Monitor model/schema
4. Add env vars to `.env.example` if needed

## Key Files

- `app/main.py` - **Lifespan hook** (scheduler start/stop)
- `app/worker/runner.py` - **Check execution** (lock pattern, alert triggering)
- `app/worker/scheduler.py` - **Job management** (add/remove/reschedule)
- `app/routers/monitors.py` - **Scheduler synchronization** (CRUD endpoints)
- `app/routers/heatmap.py` - **2160-cell heatmap** (SQL + gap filling)
