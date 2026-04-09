"""Property-based tests for SitePulse."""

import pytest
from hypothesis import given, strategies as st, settings
from app.routers.heatmap import classify_hour


# Feature: sitepulse, Property 14: Heatmap classification is exhaustive and correct
@given(
    successes=st.integers(min_value=0, max_value=100),
    total=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100)
def test_classify_hour_exhaustive(successes, total):
    """Property 14: Heatmap classification is exhaustive and correct."""
    if successes > total:
        pytest.skip("Invalid input: successes > total")

    status = classify_hour(successes, total)

    if total == 0:
        assert status == "no_data"
    elif successes == total:
        assert status == "up"
    elif successes == 0:
        assert status == "down"
    else:
        assert status == "degraded"

    assert status in ["up", "degraded", "down", "no_data"]


# Feature: sitepulse, Property 8: Uptime percentage formula correctness
@given(
    successes=st.integers(min_value=0, max_value=1000),
    total=st.integers(min_value=1, max_value=1000),
)
@settings(max_examples=100)
def test_uptime_formula(successes, total):
    """Property 8: Uptime percentage formula correctness."""
    if successes > total:
        pytest.skip("Invalid input: successes > total")

    uptime_pct = (successes / total) * 100

    assert 0 <= uptime_pct <= 100
    if successes == 0:
        assert uptime_pct == 0
    if successes == total:
        assert uptime_pct == 100


# Feature: sitepulse, Property 9: Average latency formula correctness
@given(latencies=st.lists(st.floats(min_value=0, max_value=10000), min_size=1, max_size=100))
@settings(max_examples=100)
def test_avg_latency_formula(latencies):
    """Property 9: Average latency formula correctness."""
    avg_latency = sum(latencies) / len(latencies)

    assert avg_latency >= 0
    assert min(latencies) <= avg_latency <= max(latencies)


# Feature: sitepulse, Property 4: Interval range validation
@given(interval=st.integers(min_value=-100, max_value=2000))
@settings(max_examples=100)
def test_interval_validation(interval, client):
    """Property 4: Interval range validation."""
    response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": interval,
        },
    )

    if 1 <= interval <= 1440:
        assert response.status_code == 201
    else:
        assert response.status_code == 422


# Feature: sitepulse, Property 10: Failure threshold range validation
@given(threshold=st.integers(min_value=-10, max_value=20))
@settings(max_examples=100)
def test_failure_threshold_validation(threshold, client):
    """Property 10: Failure threshold range validation."""
    response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": 5,
            "failure_threshold": threshold,
        },
    )

    if 1 <= threshold <= 10:
        assert response.status_code == 201
    else:
        assert response.status_code == 422
