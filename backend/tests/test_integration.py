"""R3/R4 lifecycle, traceability and test-monitoring integration checks."""
import pytest
from sqlalchemy import delete, text, update
from sqlalchemy.exc import DatabaseError

from app.db import SessionLocal, engine
from app.models import Defect
from app.models import TestCase as CaseRecord
from tests.conftest import as_user

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("fresh_seed")]

# Expected policy is stated independently of the implementation's TRANSITIONS table.
LEGAL = {("Open", "In Progress"), ("In Progress", "Resolved"),
         ("Resolved", "Closed"), ("Resolved", "Open"), ("Closed", "Open")}
STATES = ("Open", "In Progress", "Resolved", "Closed")


def create_in_state(client, status):
    headers = as_user("admin")
    response = client.post("/api/defects", json={"title": "Lifecycle check"}, headers=headers)
    assert response.status_code == 201
    defect_id = response.json()["id"]
    for next_state in STATES[1:STATES.index(status) + 1]:
        moved = client.post(f"/api/defects/{defect_id}/transition",
                            json={"to": next_state}, headers=headers)
        assert moved.status_code == 200
    return defect_id


@pytest.mark.parametrize(("source", "target"), [(s, t) for s in STATES for t in STATES])
def test_all_lifecycle_transitions_and_history(client, source, target):
    defect_id = create_in_state(client, source)
    path = f"/api/defects/{defect_id}"
    before = client.get(path + "/history").json()
    before_defects = client.get("/api/defects").json()
    response = client.post(path + "/transition", json={"to": target}, headers=as_user("admin"))
    history = client.get(path + "/history").json()
    if (source, target) in LEGAL:
        assert response.status_code == 200
        assert response.json()["status"] == target
        assert history[:-1] == before
        assert history[-1]["from"] == source
        assert history[-1]["to"] == target
        assert history[-1]["at"]
    else:
        assert response.status_code == 409
        assert history == before
        assert client.get("/api/defects").json() == before_defects


def test_unknown_status_is_rejected_without_history_change(client):
    before = client.get("/api/defects/1/history").json()
    response = client.post("/api/defects/1/transition", json={"to": "Unknown"},
                           headers=as_user("admin"))
    assert response.status_code == 409
    assert client.get("/api/defects/1/history").json() == before


def test_test_cases_keep_requirement_traceability(client):
    response = client.get("/api/test-cases")
    assert response.status_code == 200
    assert [(t["id"], t["requirement"]) for t in response.json()] == [
        ("TC-001", "R1"), ("TC-002", "R1"), ("TC-003", "R3"),
        ("TC-004", "R4"), ("TC-005", "R6"), ("TC-006", "R7"),
    ]


@pytest.mark.parametrize("payload", [{}, {"title": ""}, {"title": "   "},
                                     {"title": "Bad link", "test_case": "TC-999"}])
def test_rejected_creation_has_no_database_side_effects(client, payload):
    before = client.get("/api/defects").json()
    history = client.get("/api/defects/1/history").json()
    assert client.post("/api/defects", json=payload, headers=as_user("tester")).status_code == 422
    assert client.get("/api/defects").json() == before
    assert client.get("/api/defects/1/history").json() == history


def test_new_defect_is_persisted_with_initial_history(client):
    response = client.post("/api/defects", json={
        "title": "Traceable defect", "severity": "High", "test_case": "TC-003",
    }, headers=as_user("tester"))
    assert response.status_code == 201
    defect = response.json()
    assert defect in client.get("/api/defects").json()
    assert defect["test_case"] == "TC-003"
    history = client.get(f"/api/defects/{defect['id']}/history").json()
    assert len(history) == 1
    assert (history[0]["from"], history[0]["to"]) == (None, "Open")


def test_metrics_handle_unexecuted_tests(client):
    with SessionLocal.begin() as db:
        db.execute(update(CaseRecord).values(status="Not Run"))
    assert client.get("/api/metrics").json() == {
        "total_tests": 6, "execution_rate": 0, "pass_rate": 0, "open_defects": 3,
    }


def test_metrics_handle_no_test_cases(client):
    with SessionLocal.begin() as db:
        db.execute(update(Defect).values(test_case=None))
        db.execute(delete(CaseRecord))
    assert client.get("/api/metrics").json() == {
        "total_tests": 0, "execution_rate": 0, "pass_rate": 0, "open_defects": 3,
    }


def test_closing_and_reopening_changes_open_defect_metric(client):
    headers = as_user("tester")
    initial = client.get("/api/metrics").json()["open_defects"]
    assert client.post("/api/defects/3/transition", json={"to": "Closed"},
                       headers=headers).status_code == 200
    assert client.get("/api/metrics").json()["open_defects"] == initial - 1
    assert client.post("/api/defects/3/transition", json={"to": "Open"},
                       headers=headers).status_code == 200
    assert client.get("/api/metrics").json()["open_defects"] == initial


@pytest.mark.postgres
@pytest.mark.parametrize("statement", [
    "UPDATE defect_history SET to_status = 'Closed' WHERE defect_id = 1",
    "DELETE FROM defect_history WHERE defect_id = 1",
])
def test_postgresql_history_is_append_only(client, statement):
    if engine.dialect.name != "postgresql":
        pytest.skip("The append-only trigger is PostgreSQL-specific")
    before = client.get("/api/defects/1/history").json()
    with pytest.raises(DatabaseError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(text(statement))
    assert client.get("/api/defects/1/history").json() == before
