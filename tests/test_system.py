import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_api_health_returns_ok():
    """API health check confirms the service is running and reachable."""
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_frontend_dashboard_served_at_root():
    """Frontend HTML dashboard is served from the root URL via StaticFiles mount."""
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_games_endpoint_returns_paginated_results():
    """Games endpoint returns paginated envelope with data and meta fields."""
    r = client.get("/api/games?limit=5&sort_by=total_sales")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["limit"] == 5
    assert len(body["data"]) > 0


def test_verdict_machine_reachable_via_graphql():
    """GraphQL endpoint responds to introspection — confirms schema is mounted."""
    r = client.post("/api/graphql", json={"query": "{ __typename }"})
    assert r.status_code == 200


def test_analytics_leaderboard_returns_ranked_games():
    """Leaderboard endpoint returns leaders array with sales data present."""
    r = client.get("/api/analytics/leaderboard?metric=total_sales&limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "leaders" in body
    assert len(body["leaders"]) > 0
    assert body["metric"] == "total_sales"