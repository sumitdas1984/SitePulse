"""Integration tests for SitePulse."""

import pytest
from app.models import Monitor, Check


def test_create_monitor(client):
    """Test creating a monitor via API."""
    response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": 5,
            "failure_threshold": 3,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test API"
    assert data["url"] == "https://api.example.com/"
    assert "id" in data


def test_list_monitors(client):
    """Test listing monitors."""
    client.post(
        "/monitors",
        json={
            "name": "Test API 1",
            "url": "https://api1.example.com",
            "interval_minutes": 5,
        },
    )
    client.post(
        "/monitors",
        json={
            "name": "Test API 2",
            "url": "https://api2.example.com",
            "interval_minutes": 10,
        },
    )

    response = client.get("/monitors")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_monitor(client):
    """Test getting a single monitor."""
    create_response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": 5,
        },
    )
    monitor_id = create_response.json()["id"]

    response = client.get(f"/monitors/{monitor_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == monitor_id
    assert data["name"] == "Test API"


def test_update_monitor(client):
    """Test updating a monitor."""
    create_response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": 5,
        },
    )
    monitor_id = create_response.json()["id"]

    response = client.put(
        f"/monitors/{monitor_id}",
        json={"name": "Updated API", "interval_minutes": 15},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated API"
    assert data["interval_minutes"] == 15


def test_delete_monitor(client):
    """Test deleting a monitor."""
    create_response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": 5,
        },
    )
    monitor_id = create_response.json()["id"]

    response = client.delete(f"/monitors/{monitor_id}")
    assert response.status_code == 204

    get_response = client.get(f"/monitors/{monitor_id}")
    assert get_response.status_code == 404


def test_monitor_id_uniqueness(client, test_db):
    """Property 2: Monitor IDs are unique across all created monitors."""
    ids = []
    for i in range(5):
        response = client.post(
            "/monitors",
            json={
                "name": f"Test API {i}",
                "url": f"https://api{i}.example.com",
                "interval_minutes": 5,
            },
        )
        ids.append(response.json()["id"])

    assert len(ids) == len(set(ids))


def test_cascade_delete(client, test_db):
    """Property 3: Cascade delete removes all associated checks."""
    create_response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": 5,
        },
    )
    monitor_id = create_response.json()["id"]

    db = next(test_db())
    monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
    for i in range(3):
        check = Check(monitor_id=monitor_id, success=True)
        db.add(check)
    db.commit()

    check_count = db.query(Check).filter(Check.monitor_id == monitor_id).count()
    assert check_count == 3

    client.delete(f"/monitors/{monitor_id}")

    check_count_after = db.query(Check).filter(Check.monitor_id == monitor_id).count()
    assert check_count_after == 0


def test_stats_endpoint(client):
    """Test stats endpoint."""
    create_response = client.post(
        "/monitors",
        json={
            "name": "Test API",
            "url": "https://api.example.com",
            "interval_minutes": 5,
        },
    )
    monitor_id = create_response.json()["id"]

    response = client.get(f"/monitors/{monitor_id}/stats?window_hours=24")
    assert response.status_code == 200
    data = response.json()
    assert data["monitor_id"] == monitor_id
    assert "total_checks" in data
    assert "uptime_pct" in data
