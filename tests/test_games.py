import pytest


def test_games_returns_paginated(client):
    r = client.get("/api/games")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "meta" in body
    assert "total" in body["meta"]


def test_games_default_limit(client):
    r = client.get("/api/games")
    assert len(r.json()["data"]) <= 20


def test_games_custom_limit(client):
    r = client.get("/api/games?limit=5")
    assert len(r.json()["data"]) <= 5


def test_games_title_filter(client):
    r = client.get("/api/games?title=Grand+Theft+Auto")
    assert r.status_code == 200
    for g in r.json()["data"]:
        assert "grand theft auto" in g["canonical_title"].lower()


def test_games_platform_filter(client):
    r = client.get("/api/games?platform=PS4&limit=5")
    assert r.status_code == 200
    for g in r.json()["data"]:
        assert g["platform"] == "PS4"


def test_games_sort_by_meta_score(client):
    r = client.get("/api/games?sort_by=meta_score&limit=5")
    scores = [g["meta_score"] for g in r.json()["data"] if g["meta_score"]]
    assert scores == sorted(scores, reverse=True)


def test_games_empty_search(client):
    r = client.get("/api/games?title=xyznonexistentgame123")
    assert r.status_code == 200
    assert r.json()["data"] == []


def test_game_by_id(client):
    # grab a real game from the seeded database
    r = client.get("/api/games?title=Grand+Theft+Auto&limit=1")
    data = r.json()["data"]
    assert len(data) > 0, "No GTA games found -- is the database seeded?"
    game_id = data[0]["id"]
    r2 = client.get(f"/api/games/{game_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == game_id


def test_game_invalid_id_404(client):
    r = client.get("/api/games/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_admin_create_requires_auth(client):
    # unauthenticated POST should be rejected -- 401 or 403 both acceptable
    r = client.post("/api/games", json={
        "canonical_title": "Test Game",
        "normalized_title": "test game",
        "platform": "PC"
    })
    assert r.status_code in (401, 403)