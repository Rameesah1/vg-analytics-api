import pytest


def test_squads_requires_auth(client):
    r = client.get("/api/squads")
    assert r.status_code in (401, 403)


def test_create_squad(auth_client):
    r = auth_client.post("/api/squads", json={
        "name": "Test Squad",
        "description": "A test squad",
        "is_public": False
    })
    assert r.status_code == 201
    assert r.json()["name"] == "Test Squad"


def test_list_squads(auth_client):
    auth_client.post("/api/squads", json={"name": "Listed Squad", "is_public": False})
    r = auth_client.get("/api/squads")
    assert r.status_code == 200
    assert "data" in r.json()


def test_get_squad_by_id(auth_client):
    created = auth_client.post("/api/squads", json={
        "name": "Detail Squad", "is_public": False
    }).json()
    r = auth_client.get(f"/api/squads/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_update_squad(auth_client):
    created = auth_client.post("/api/squads", json={
        "name": "Old Name", "is_public": False
    }).json()
    r = auth_client.patch(f"/api/squads/{created['id']}", json={"name": "New Name"})
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


def test_delete_squad(auth_client):
    created = auth_client.post("/api/squads", json={
        "name": "Delete Me", "is_public": False
    }).json()
    r = auth_client.delete(f"/api/squads/{created['id']}")
    assert r.status_code == 200
    r2 = auth_client.get(f"/api/squads/{created['id']}")
    assert r2.status_code == 404


def test_add_item_to_squad(auth_client):
    game = auth_client.get("/api/games?title=Grand+Theft+Auto&limit=1").json()["data"]
    assert len(game) > 0, "No GTA games found -- is the database seeded?"
    game_id = game[0]["id"]
    squad = auth_client.post("/api/squads", json={
        "name": "Item Squad", "is_public": False
    }).json()
    r = auth_client.post(f"/api/squads/{squad['id']}/items", json={
        "game_release_id": game_id
    })
    assert r.status_code == 201


def test_duplicate_item_ignored(auth_client):
    game = auth_client.get("/api/games?title=Grand+Theft+Auto&limit=1").json()["data"]
    assert len(game) > 0
    game_id = game[0]["id"]
    squad = auth_client.post("/api/squads", json={
        "name": "Dup Squad", "is_public": False
    }).json()
    auth_client.post(f"/api/squads/{squad['id']}/items", json={"game_release_id": game_id})
    r = auth_client.post(f"/api/squads/{squad['id']}/items", json={"game_release_id": game_id})
    assert r.status_code in (200, 201)

def test_dna_requires_min_games(auth_client):
    squad = auth_client.post("/api/squads", json={
        "name": "Tiny Squad", "is_public": False
    }).json()
    r = auth_client.get(f"/api/squads/{squad['id']}/dna")
    assert r.status_code == 400


def test_battle_same_squad_rejected(auth_client):
    squad = auth_client.post("/api/squads", json={
        "name": "Battle Squad", "is_public": False
    }).json()
    r = auth_client.post("/api/battles", json={
        "squad_a_id": squad["id"],
        "squad_b_id": squad["id"],
        "preset": "BALANCED"
    })
    assert r.status_code == 400