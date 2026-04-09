# Implementation Plan: SitePulse

## Overview

Implement SitePulse as a FastAPI + APScheduler backend with SQLite/SQLAlchemy persistence, an httpx-based check runner, smtplib/httpx alerting, and a Streamlit frontend. The existing `sitepulse_app.py` mockup is the basis for the real frontend. Tasks are ordered so each step builds on the previous and nothing is left unintegrated.

## Tasks

- [ ] 1. Project setup — dependencies, folder structure, environment config
  - Add all runtime dependencies to `pyproject.toml`: `fastapi`, `uvicorn[standard]`, `apscheduler`, `sqlalchemy`, `pydantic[email]`, `httpx`, `streamlit`, `plotly`, `pandas`, `python-dotenv`
  - Add dev/test dependencies: `pytest`, `pytest-asyncio`, `httpx` (test client), `hypothesis`
  - Create the package layout:
    ```
    app/
      __init__.py
      main.py
      models.py
      schemas.py
      database.py
      routers/
        __init__.py
        monitors.py
        checks.py
        heatmap.py
        analytics.py
      worker/
        __init__.py
        scheduler.py
        runner.py
      services/
        __init__.py
        alerts.py
        email_alert.py
        webhook_alert.py
    tests/
      __init__.py
      conftest.py
    .env.example
    ```
  - Create `.env.example` with `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `DATABASE_URL` (default `sqlite:///./sitepulse.db`)
  - _Requirements: 7.4_

- [ ] 2. Database layer — SQLAlchemy engine, session, and ORM models
  - [ ] 2.1 Implement `app/database.py` with engine creation from `DATABASE_URL` env var, `SessionLocal` factory, `get_db` dependency, and `init_db()` that calls `Base.metadata.create_all`
    - _Requirements: 1.1, 3.1_
  - [ ] 2.2 Implement `app/models.py` with `Monitor` and `Check` ORM classes matching the design schema exactly, including cascade delete on `Check.monitor_id`
    - Include all fields: `id` (UUID str), `name`, `url`, `interval_minutes`, `expected_status_code`, `json_assert_key`, `json_assert_value`, `alert_email`, `webhook_url`, `failure_threshold` (default 3), `consecutive_failures`, `alert_suppressed`, `created_at` on Monitor; `id`, `monitor_id` (FK cascade), `timestamp`, `success`, `http_status_code`, `response_time_ms`, `failure_reason` on Check
    - _Requirements: 1.2, 1.5, 1.6, 2.6, 6.1, 6.5_

- [ ] 3. Pydantic schemas (`app/schemas.py`)
  - Implement `MonitorCreate`, `MonitorUpdate`, `MonitorRead`, `CheckRead`, `HeatmapCell`, `HeatmapResponse`, `UptimeStats` exactly as specified in the design
  - `MonitorCreate.url` uses `HttpUrl` for automatic HTTP/HTTPS validation (satisfies Req 1.3/1.4)
  - `MonitorCreate.interval_minutes` uses `Field(ge=1, le=1440)` (satisfies Req 1.7/1.8)
  - `MonitorCreate.failure_threshold` uses `Field(default=3, ge=1, le=10)` (satisfies Req 6.1/6.5)
  - _Requirements: 1.3, 1.4, 1.7, 1.8, 6.1, 6.5_

- [ ] 4. FastAPI app skeleton and lifespan hook (`app/main.py`)
  - Create `FastAPI` app with `@asynccontextmanager` lifespan that calls `init_db()`, starts the scheduler, seeds jobs for all existing monitors, and shuts down the scheduler on exit
  - Register all four routers with their prefixes
  - _Requirements: 3.1_

- [ ] 5. Monitor CRUD router (`app/routers/monitors.py`)
  - [ ] 5.1 Implement `GET /monitors` — return all monitors as `list[MonitorRead]`
    - _Requirements: 1.1, 10.1_
  - [ ] 5.2 Implement `POST /monitors` — validate with `MonitorCreate`, persist, assign UUID, call `scheduler.add_monitor_job`, return 201 `MonitorRead`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 1.8, 3.2_
  - [ ] 5.3 Implement `GET /monitors/{id}` — return single `MonitorRead` or 404
    - _Requirements: 1.1_
  - [ ] 5.4 Implement `PUT /monitors/{id}` — validate with `MonitorUpdate`, persist changes, call `scheduler.reschedule_monitor_job` if interval changed, return 200 `MonitorRead` or 404/422
    - _Requirements: 1.1, 3.4_
  - [ ] 5.5 Implement `DELETE /monitors/{id}` — delete monitor (cascade removes checks), call `scheduler.remove_monitor_job`, return 204 or 404
    - _Requirements: 1.1, 1.6, 3.3_

- [ ] 6. Checks and stats router (`app/routers/checks.py`)
  - [ ] 6.1 Implement `GET /monitors/{id}/checks` with optional `start` / `end` ISO datetime query params; return `list[CheckRead]` filtered to the requested window
    - _Requirements: 4.1_
  - [ ] 6.2 Implement `GET /monitors/{id}/stats` with `window_hours` query param (default 24); compute and return `UptimeStats` (uptime %, avg latency, total/successful checks); return `null` for uptime/latency when no checks exist
    - _Requirements: 4.2, 4.3, 4.4, 5.1, 5.2, 5.3, 5.4_

- [ ] 7. Heatmap router (`app/routers/heatmap.py`)
  - [ ] 7.1 Implement `classify_hour(successes: int, total: int) -> str` pure function with the four-branch logic from the design
    - _Requirements: 9.2_
  - [ ] 7.2 Implement `GET /monitors/{id}/heatmap` — run the aggregation SQL query, fill all 2160 hourly slots (oldest-first, `no_data` for missing hours), return `HeatmapResponse`
    - _Requirements: 9.1, 9.2_
  - [ ]* 7.3 Write property test for `classify_hour` — Property 14
    - **Property 14: Heatmap classification is exhaustive and correct**
    - **Validates: Requirements 9.2**
  - [ ]* 7.4 Write property test for heatmap endpoint cell count — Property 15
    - **Property 15: Heatmap response always contains exactly 2160 cells**
    - **Validates: Requirements 9.1**

- [ ] 8. Analytics router (`app/routers/analytics.py`)
  - [ ] 8.1 Implement `GET /analytics/latency` — return system-wide average latency per hour for the last 24 hours across all monitors
    - _Requirements: 4.2_
  - [ ] 8.2 Implement `GET /analytics/incidents` — return recent failed checks grouped as incidents for the last 7 days, with columns: timestamp, monitor name, failure reason, severity
    - _Requirements: 4.1_

- [ ] 9. Scheduler service (`app/worker/scheduler.py`)
  - Implement `AsyncIOScheduler` singleton with `add_monitor_job`, `remove_monitor_job`, and `reschedule_monitor_job` functions
  - Each job calls `run_check(monitor_id)` on the `'interval'` trigger with `minutes=interval_minutes`
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 10. Check runner (`app/worker/runner.py`)
  - [ ] 10.1 Implement per-monitor `asyncio.Lock` dict and `run_check(monitor_id)` entry point that acquires the lock non-blocking (skip if already locked)
    - _Requirements: 3.5_
  - [ ] 10.2 Implement `_execute_check(monitor_id)` with the full flow: load monitor, HTTP GET via `httpx.AsyncClient(timeout=30.0)`, evaluate success criteria (status code match, JSON assertion), persist `Check` record, update `consecutive_failures` / `alert_suppressed`, dispatch alert if threshold reached
    - Record `failure_reason` as `"timeout"`, `"connection_error"`, `"status_mismatch"`, `"json_assertion_failed"`, or `"json_parse_error"` as appropriate
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 6.2, 6.3, 6.4_
  - [ ]* 10.3 Write property test for check success evaluation — Property 5
    - **Property 5: Check success evaluation is determined solely by response vs. expectation**
    - **Validates: Requirements 2.2**
  - [ ]* 10.4 Write property test for JSON assertion evaluation — Property 6
    - **Property 6: JSON assertion evaluation**
    - **Validates: Requirements 2.3**
  - [ ]* 10.5 Write property test for completed check record fields — Property 7
    - **Property 7: Completed check records contain all required fields**
    - **Validates: Requirements 2.6**

- [ ] 11. Alert service (`app/services/alerts.py`, `email_alert.py`, `webhook_alert.py`)
  - [ ] 11.1 Implement `send_email_alert(monitor, last_check)` in `email_alert.py` using `smtplib` with SMTP config from env vars; use the email body template from the design; catch and log all SMTP exceptions without re-raising
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  - [ ] 11.2 Implement `send_webhook_alert(monitor, last_check)` in `webhook_alert.py` using `httpx.AsyncClient(timeout=10.0)`; send the JSON payload from the design; catch non-2xx responses and timeouts, log them, do not raise
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [ ] 11.3 Implement `dispatch_alert(monitor, last_check)` in `alerts.py` that calls both conditionally based on monitor config
    - _Requirements: 7.1, 8.1_
  - [ ]* 11.4 Write property test for alert payload completeness — Property 13
    - **Property 13: Alert notification payload contains all required fields**
    - **Validates: Requirements 7.2, 8.2**

- [ ] 12. Checkpoint — wire backend together and verify
  - Ensure `app/main.py` lifespan correctly starts/stops the scheduler and seeds jobs
  - Ensure all routers are registered and reachable
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Property-based tests for core business logic (`tests/test_properties.py`)
  - [ ] 13.1 Write property test for URL validation — Property 1
    - **Property 1: URL validation rejects non-HTTP/HTTPS strings**
    - **Validates: Requirements 1.3, 1.4**
  - [ ] 13.2 Write property test for interval range validation — Property 4
    - **Property 4: Interval range validation**
    - **Validates: Requirements 1.7, 1.8**
  - [ ] 13.3 Write property test for uptime percentage formula — Property 8
    - **Property 8: Uptime percentage formula correctness**
    - **Validates: Requirements 5.1, 5.4**
  - [ ] 13.4 Write property test for average latency formula — Property 9
    - **Property 9: Average latency formula correctness**
    - **Validates: Requirements 4.2, 4.3, 4.4**
  - [ ] 13.5 Write property test for failure threshold range validation — Property 10
    - **Property 10: Failure threshold range validation**
    - **Validates: Requirements 6.1**
  - [ ] 13.6 Write property test for alert suppression state machine — Property 11
    - **Property 11: Alert fires exactly at threshold and is then suppressed**
    - **Validates: Requirements 6.2, 6.3**
  - [ ] 13.7 Write property test for consecutive failure reset on success — Property 12
    - **Property 12: Successful check resets consecutive failure count**
    - **Validates: Requirements 6.4**
  - [ ] 13.8 Write property test for check time-window filter — Property 16
    - **Property 16: Check time-window filter excludes out-of-range records**
    - **Validates: Requirements 4.1**

- [ ] 14. Integration tests (`tests/test_integration.py`)
  - [ ] 14.1 Write example-based test for Monitor ID uniqueness — Property 2
    - Create N monitors and assert all IDs are pairwise distinct
    - **Property 2: Monitor IDs are unique across all created monitors**
    - **Validates: Requirements 1.5**
  - [ ] 14.2 Write example-based test for cascade delete — Property 3
    - Create a monitor, insert checks, delete the monitor, assert zero checks remain
    - **Property 3: Cascade delete removes all associated checks**
    - **Validates: Requirements 1.6**
  - [ ] 14.3 Write full CRUD lifecycle integration test using FastAPI `TestClient`
    - Create → read → update (interval change) → delete; assert scheduler calls at each step
    - _Requirements: 1.1, 1.2, 3.2, 3.3, 3.4_
  - [ ] 14.4 Write check runner integration test with mocked `httpx` response
    - Mock a 200 response and a timeout; assert correct `Check` records are persisted
    - _Requirements: 2.1, 2.4, 2.5, 2.6_
  - [ ] 14.5 Write alert dispatch integration test with mocked SMTP and webhook
    - Drive consecutive failures to threshold; assert alert fires once and is suppressed on further failures; assert reset after success
    - _Requirements: 6.2, 6.3, 6.4_

- [ ] 15. Checkpoint — all backend tests pass
  - Run `pytest tests/ -x` and ensure all tests pass. Ask the user if questions arise.

- [ ] 16. Streamlit frontend — replace mockup with real API-backed implementation (`sitepulse_app.py`)
  - [ ] 16.1 Add `httpx` (or `requests`) API client helper with `API_BASE_URL` from env (default `http://localhost:8000`); replace all `st.session_state` mock data with live API calls
    - _Requirements: 10.1_
  - [ ] 16.2 Implement `show_dashboard()` backed by real data: fetch `GET /monitors`, compute global metrics (total, healthy count, avg latency, 24h incident count), render per-monitor cards with live uptime/latency from `GET /monitors/{id}/stats`, fetch heatmap from `GET /monitors/{id}/heatmap` and pass cells to `render_heatmap`
    - _Requirements: 10.1, 10.2, 10.3, 9.3, 9.4_
  - [ ] 16.3 Implement auto-refresh: sidebar countdown timer using `time.sleep(1)` + `st.rerun()` capped at 60 seconds
    - _Requirements: 10.4_
  - [ ] 16.4 Implement monitor detail view triggered by the "📊" button: show check history table, Plotly latency trend chart, and full heatmap for the selected monitor
    - _Requirements: 10.5_
  - [ ] 16.5 Implement `show_management()` backed by real API: `POST /monitors` on form submit (with all fields including optional `alert_email`, `webhook_url`, `failure_threshold`), `DELETE /monitors/{id}` on delete action, refresh table from `GET /monitors`
    - _Requirements: 1.1, 1.2, 1.3, 7.1, 8.1_
  - [ ] 16.6 Implement `show_analytics()` backed by real API: Plotly area chart from `GET /analytics/latency`, incident log table from `GET /analytics/incidents`
    - _Requirements: 4.2_
  - [ ] 16.7 Implement `render_heatmap(cells: list[HeatmapCell])` with the four-color mapping and tooltip from the design, replacing the binary mock version
    - _Requirements: 9.3, 9.4_

- [ ] 17. README and run instructions
  - Update `README.md` with: prerequisites, `pip install -e .[dev]` setup, `.env` configuration, how to run the API (`uvicorn app.main:app --reload`), how to run the frontend (`streamlit run sitepulse_app.py`), and how to run tests (`pytest tests/ -x`)
  - _Requirements: all_

- [ ] 18. Final checkpoint — full system smoke test
  - Ensure all tests pass with `pytest tests/ -x`
  - Verify API starts and all routes are registered
  - Verify scheduler seeds jobs for existing monitors on startup
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use `@settings(max_examples=100)` and are tagged with `# Feature: sitepulse, Property N`
- Properties 2 and 3 are covered by example-based integration tests (task 14.1, 14.2) rather than property-based tests, as they are DB-level behaviors
- The existing `sitepulse_app.py` mockup is replaced in-place (task 16) — no new file is created
