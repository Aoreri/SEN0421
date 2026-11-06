from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture
def client():
    defects = deepcopy(main.DEFECTS)
    history = deepcopy(main.HISTORY)
    with TestClient(main.app) as test_client:
        yield test_client
    main.DEFECTS.clear()
    main.DEFECTS.update(defects)
    main.HISTORY[:] = history


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "template": True}


def test_create_defect_records_initial_history(client):
    response = client.post("/api/defects", json={"title": "CI test defect"})
    assert response.status_code == 201
    defect = response.json()
    assert defect["status"] == "Open"
    history = client.get(f"/api/defects/{defect['id']}/history").json()
    assert len(history) == 1
    assert history[0]["from"] is None
    assert history[0]["to"] == "Open"


@pytest.mark.parametrize("title", ["", "   "])
def test_blank_title_is_rejected_without_mutation(client, title):
    before = deepcopy(main.DEFECTS), deepcopy(main.HISTORY)
    assert client.post("/api/defects", json={"title": title}).status_code == 422
    assert (main.DEFECTS, main.HISTORY) == before


def test_invalid_transition_does_not_change_state_or_history(client):
    before = deepcopy(main.DEFECTS), deepcopy(main.HISTORY)
    response = client.post("/api/defects/1/transition", json={"to": "Closed"})
    assert response.status_code == 400
    assert (main.DEFECTS, main.HISTORY) == before


def test_valid_transition_preserves_existing_history(client):
    before = deepcopy(main.HISTORY)
    response = client.post("/api/defects/1/transition", json={"to": "In Progress"})
    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"
    assert main.HISTORY[:-1] == before
    assert main.HISTORY[-1]["from"] == "Open"
    assert main.HISTORY[-1]["to"] == "In Progress"


def test_unknown_defect_transition_returns_404(client):
    response = client.post("/api/defects/99999/transition", json={"to": "Open"})
    assert response.status_code == 404


def test_seed_metrics(client):
    assert client.get("/api/metrics").json() == {
        "total_tests": 6,
        "execution_rate": 66.7,
        "pass_rate": 75.0,
        "open_defects": 3,
    }
