import pytest


def test_leaderboard_default(client):
    r = client.get("/api/analytics/leaderboard")
    assert r.status_code == 200
    body = r.json()
    assert "leaders" in body
    assert "metric" in body
    assert body["metric"] == "total_sales"


def test_leaderboard_by_meta_score(client):
    r = client.get("/api/analytics/leaderboard?metric=meta_score&limit=5")
    assert r.status_code == 200
    scores = [g["meta_score"] for g in r.json()["leaders"] if g["meta_score"]]
    assert scores == sorted(scores, reverse=True)


def test_leaderboard_respects_limit(client):
    r = client.get("/api/analytics/leaderboard?limit=3")
    assert len(r.json()["leaders"]) <= 3


def test_verdict_valid_game(client):
    r = client.get("/api/games?title=Grand+Theft+Auto&limit=1")
    data = r.json()["data"]
    assert len(data) > 0, "No GTA games found -- is the database seeded?"
    game_id = data[0]["id"]
    r2 = client.get(f"/api/analytics/verdict/{game_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert "verdict" in body
    assert "confidence" in body
    assert "scores" in body
    assert body["verdict"] in [
        "All-Time Classic", "Cult Classic", "Critic Darling", "Overhyped",
        "Hidden Gem", "Commercial Hit", "Divisive", "Great Game",
        "Solid Title", "Unrated"
    ]


def test_verdict_invalid_id(client):
    r = client.get("/api/analytics/verdict/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_controversy_structure(client):
    r = client.get("/api/analytics/controversy?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    for item in body["results"]:
        assert "divergence" in item
        assert "meta_score" in item
        assert "user_review" in item


def test_controversy_sorted_by_divergence(client):
    r = client.get("/api/analytics/controversy?limit=10")
    divs = [i["divergence"] for i in r.json()["results"]]
    assert divs == sorted(divs, reverse=True)


def test_hidden_gems_structure(client):
    r = client.get("/api/analytics/hidden-gems?limit=5")
    assert r.status_code == 200
    for item in r.json()["results"]:
        assert item["user_review"] >= 8.0


def test_decade_trends_structure(client):
    r = client.get("/api/analytics/decade-trends")
    assert r.status_code == 200
    body = r.json()
    assert "decades" in body
    assert len(body["decades"]) > 0


def test_platform_dominance_structure(client):
    r = client.get("/api/analytics/platform-dominance")
    assert r.status_code == 200
    assert "platforms" in r.json()