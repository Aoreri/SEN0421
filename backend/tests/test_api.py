"""API integration tests against the migrated, disposable test database."""
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import pytest

from app.auth import JWT_ALGORITHM, JWT_SECRET
from app.db import SessionLocal
from app.models import DefectTransition, User
from tests.conftest import as_user

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("fresh_seed")]


def test_seed_and_metrics(client):
    assert len(client.get("/api/test-cases").json()) == 6
    assert client.get("/api/metrics").json() == {
        "total_tests": 6, "execution_rate": 66.7, "pass_rate": 75.0, "open_defects": 3,
    }


def test_defect_lifecycle_and_history(client):
    d = client.post("/api/defects", json={"title": "Yeni hata", "test_case": "TC-001"},
                    headers=as_user("tester")).json()
    assert d["id"] == 4 and d["status"] == "Open" and d["allowed"] == []

    url = f"/api/defects/{d['id']}/transition"
    admin = as_user("admin")
    assert client.post(url, json={"to": "Closed"}, headers=admin).status_code == 409
    for to in ("In Progress", "Resolved", "Closed", "Open"):
        assert client.post(url, json={"to": to}, headers=admin).json()["status"] == to

    hist = client.get(f"/api/defects/{d['id']}/history").json()
    assert [(h["from"], h["to"]) for h in hist] == [
        (None, "Open"), ("Open", "In Progress"), ("In Progress", "Resolved"),
        ("Resolved", "Closed"), ("Closed", "Open"),
    ]


def test_validation(client):
    tester = as_user("tester")
    assert client.post("/api/defects", json={"title": "  "}, headers=tester).status_code == 422
    assert client.post("/api/defects", json={"title": "x", "test_case": "TC-999"},
                       headers=tester).status_code == 422
    assert client.post("/api/defects/999/transition", json={"to": "Open"},
                       headers=tester).status_code == 404


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_rejected_requests_leave_data_unchanged(client):
    before = client.get("/api/defects/1/history").json()
    count = len(client.get("/api/defects").json())
    tester = as_user("tester")
    assert client.post("/api/defects/1/transition", json={"to": "Closed"},
                       headers=tester).status_code == 409
    assert client.post("/api/defects/1/transition", json={"to": "In Progress"},
                       headers=tester).status_code == 403
    assert client.post("/api/defects", json={"title": " "}, headers=tester).status_code == 422
    assert client.get("/api/defects/1/history").json() == before
    assert len(client.get("/api/defects").json()) == count


@pytest.mark.parametrize("username,role", [
    ("admin", "Admin"), ("testlead", "Test Lead"), ("tester", "Tester"), ("developer", "Developer"),
])
def test_login_and_me(client, username, role):
    body = client.post("/api/auth/login", json={"username": username, "password": "demo1234"}).json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == username and body["user"]["role"] == role
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json() == body["user"]


@pytest.mark.parametrize("username,password", [("tester", "yanlis"), ("yok", "demo1234")])
def test_login_rejects_bad_credentials(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 401 and "access_token" not in res.json()


def test_login_does_not_truncate_long_passwords(client):
    password = "a" * 72
    with SessionLocal() as db:
        db.add(User(username="uzun", role="Tester",
                    password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()))
        db.commit()
    for attempt, status in [(password, 200), (password + "x", 401)]:
        res = client.post("/api/auth/login", json={"username": "uzun", "password": attempt})
        assert res.status_code == status


def forged(secret=JWT_SECRET, expires_in=60, sub="1") -> dict:
    claims = {"sub": sub, "exp": datetime.now(UTC) + timedelta(seconds=expires_in)}
    return {"Authorization": f"Bearer {jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)}"}


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer garbage"},
    forged(secret="x" * 32),
    forged(expires_in=-60),
    forged(sub="999"),
    forged(sub="abc"),
])
def test_bad_tokens_are_rejected(client, headers):
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_mutations_require_login_and_role(client):
    before = len(client.get("/api/defects").json())
    assert client.post("/api/defects", json={"title": "x"}).status_code == 401
    assert client.post("/api/defects/1/transition", json={"to": "In Progress"}).status_code == 401
    assert client.post("/api/defects", json={"title": "x"},
                       headers=as_user("developer")).status_code == 403
    assert len(client.get("/api/defects").json()) == before
    for username in ("admin", "testlead", "tester"):
        assert client.post("/api/defects", json={"title": "x"},
                           headers=as_user(username)).status_code == 201


# (defect id, tohum durumu): 1 Open, 2 In Progress, 3 Resolved
@pytest.mark.parametrize("defect,to,allowed,denied", [
    (1, "In Progress", "developer", "tester"),
    (2, "Resolved", "developer", "testlead"),
    (3, "Closed", "tester", "developer"),
    (3, "Open", "testlead", "developer"),
])
def test_transition_roles(client, defect, to, allowed, denied):
    url = f"/api/defects/{defect}/transition"
    assert client.post(url, json={"to": to}, headers=as_user(denied)).status_code == 403
    res = client.post(url, json={"to": to}, headers=as_user(allowed))
    assert res.status_code == 200 and res.json()["status"] == to


def test_closed_defect_reopen_roles(client):
    url = "/api/defects/3/transition"
    client.post(url, json={"to": "Closed"}, headers=as_user("tester"))
    assert client.post(url, json={"to": "Open"}, headers=as_user("developer")).status_code == 403
    assert client.post(url, json={"to": "Open"}, headers=as_user("tester")).status_code == 200


def test_allowed_depends_on_role(client):
    def allowed(headers):
        return {d["id"]: d["allowed"] for d in client.get("/api/defects", headers=headers).json()}

    assert allowed({}) == {1: [], 2: [], 3: []}
    assert allowed(as_user("developer")) == {1: ["In Progress"], 2: ["Resolved"], 3: []}
    assert allowed(as_user("tester")) == {1: [], 2: [], 3: ["Closed", "Open"]}
    assert allowed(as_user("admin")) == {1: ["In Progress"], 2: ["Resolved"], 3: ["Closed", "Open"]}
    assert client.get("/api/defects", headers=forged(expires_in=-60)).status_code == 401


def test_denied_transitions_write_no_history(client):
    before = client.get("/api/defects/1/history").json()
    url = "/api/defects/1/transition"
    assert client.post(url, json={"to": "In Progress"}, headers=as_user("tester")).status_code == 403
    assert client.post(url, json={"to": "Nope"}, headers=as_user("admin")).status_code == 409
    assert client.get("/api/defects/1/history").json() == before


def test_transition_rules_come_from_the_database(client):
    with SessionLocal() as db:
        db.get_one(DefectTransition, ("Open", "In Progress")).allowed_roles = ["Tester"]
        db.commit()
    url = "/api/defects/1/transition"
    assert client.post(url, json={"to": "In Progress"}, headers=as_user("developer")).status_code == 403
    assert client.post(url, json={"to": "In Progress"}, headers=as_user("tester")).status_code == 200


def test_project_crud(client):
    lead = as_user("testlead")
    created = client.post("/api/projects", json={"name": " Yeni "}, headers=lead)
    assert created.status_code == 201
    project = created.json()
    assert project["name"] == "Yeni" and project["description"] == ""
    url = f"/api/projects/{project['id']}"
    assert client.get(url).json() == project
    updated = client.put(url, json={"name": "Yeni 2", "description": "d"}, headers=lead).json()
    assert updated == {"id": project["id"], "name": "Yeni 2", "description": "d"}
    assert updated in client.get("/api/projects").json()
    assert client.delete(url, headers=lead).status_code == 204
    assert client.get(url).status_code == 404


def test_release_crud(client):
    lead = as_user("testlead")
    release = client.post("/api/releases", json={"project_id": 1, "version": "v1"}, headers=lead)
    assert release.status_code == 201
    url = f"/api/releases/{release.json()['id']}"
    assert client.get(url).json()["version"] == "v1"
    assert client.put(url, json={"project_id": 1, "version": "v2"},
                      headers=lead).json()["version"] == "v2"
    assert len(client.get("/api/releases").json()) == 1
    assert client.delete(url, headers=lead).status_code == 204
    assert client.get(url).status_code == 404


def test_requirement_crud(client):
    lead = as_user("testlead")
    body = {"id": "R9", "project_id": 1, "title": "Yeni gereksinim"}
    assert client.post("/api/requirements", json=body, headers=lead).status_code == 201
    update = {"project_id": 1, "title": "Değişti", "description": "d"}
    assert client.put("/api/requirements/R9", json=update, headers=lead).json() == {
        "id": "R9", "project_id": 1, "title": "Değişti", "description": "d", "test_cases": [],
    }
    assert len(client.get("/api/requirements").json()) == 9
    assert client.delete("/api/requirements/R9", headers=lead).status_code == 204
    assert client.get("/api/requirements/R9").status_code == 404


@pytest.mark.parametrize("url,body,status", [
    ("/api/projects", {"name": "SDS-06"}, 409),
    ("/api/projects", {"name": "   "}, 422),
    ("/api/projects", {"name": "x" * 101}, 422),
    ("/api/releases", {"project_id": 999, "version": "v1"}, 422),
    ("/api/requirements", {"id": "R1", "project_id": 1, "title": "x"}, 409),
    ("/api/requirements", {"id": "R9", "project_id": 999, "title": "x"}, 422),
])
def test_invalid_writes(client, url, body, status):
    assert client.post(url, json=body, headers=as_user("admin")).status_code == status


def test_duplicate_release_version_conflicts(client):
    body = {"project_id": 1, "version": "v1"}
    assert client.post("/api/releases", json=body, headers=as_user("admin")).status_code == 201
    assert client.post("/api/releases", json=body, headers=as_user("admin")).status_code == 409


@pytest.mark.parametrize("method,url,body", [
    ("post", "/api/projects", {"name": "x"}),
    ("put", "/api/projects/1", {"name": "x"}),
    ("delete", "/api/projects/1", None),
    ("post", "/api/releases", {"project_id": 1, "version": "v1"}),
    ("put", "/api/releases/1", {"project_id": 1, "version": "v1"}),
    ("delete", "/api/releases/1", None),
    ("post", "/api/requirements", {"id": "R9", "project_id": 1, "title": "x"}),
    ("put", "/api/requirements/R1", {"project_id": 1, "title": "x"}),
    ("delete", "/api/requirements/R1", None),
])
def test_catalog_writes_are_role_guarded(client, method, url, body):
    send = getattr(client, method)
    kwargs = {"json": body} if body else {}
    assert send(url, **kwargs).status_code == 401
    for username in ("tester", "developer"):
        assert send(url, headers=as_user(username), **kwargs).status_code == 403


def test_delete_with_dependents_is_rejected(client):
    admin = as_user("admin")
    assert client.delete("/api/projects/1", headers=admin).status_code == 409
    assert client.delete("/api/requirements/R1", headers=admin).status_code == 409
    assert client.get("/api/requirements/R1").json()["test_cases"] == ["TC-001", "TC-002"]


def test_project_with_only_releases_cannot_be_deleted(client):
    admin = as_user("admin")
    project = client.post("/api/projects", json={"name": "P"}, headers=admin).json()
    client.post("/api/releases", json={"project_id": project["id"], "version": "v1"}, headers=admin)
    assert client.delete(f"/api/projects/{project['id']}", headers=admin).status_code == 409


def test_seed_traceability_matches_test_case_requirement(client):
    for case in client.get("/api/test-cases").json():
        assert case["requirements"] == [case["requirement"]]
    assert len(client.get("/api/requirements").json()) == 8


def test_traceability_is_many_to_many_and_replaceable(client):
    tester = as_user("tester")
    url = "/api/requirements/R2/test-cases"
    assert client.put(url, json={"test_cases": ["TC-001", "TC-003", "TC-001"]},
                      headers=tester).json()["test_cases"] == ["TC-001", "TC-003"]
    tc1 = next(c for c in client.get("/api/test-cases").json() if c["id"] == "TC-001")
    assert tc1["requirements"] == ["R1", "R2"]
    assert client.put(url, json={"test_cases": []}, headers=tester).json()["test_cases"] == []
    assert client.delete("/api/requirements/R2", headers=as_user("admin")).status_code == 204


def test_traceability_rejects_bad_input(client):
    url = "/api/requirements/R1/test-cases"
    body = {"test_cases": ["TC-999"]}
    assert client.put(url, json=body, headers=as_user("tester")).status_code == 422
    assert client.put("/api/requirements/R99/test-cases", json={"test_cases": []},
                      headers=as_user("tester")).status_code == 404
    links = {"test_cases": ["TC-001"]}
    assert client.put(url, json=links).status_code == 401
    assert client.put(url, json=links, headers=as_user("developer")).status_code == 403
    assert client.get("/api/requirements/R1").json()["test_cases"] == ["TC-001", "TC-002"]


def test_test_run_and_execution_lifecycle(client):
    tester = as_user("tester")
    lead = as_user("testlead")
    rel = client.post("/api/releases", json={"project_id": 1, "version": "v1.0"}, headers=lead).json()

    run_res = client.post(
        "/api/test-runs",
        json={
            "name": " Sprint 1 Regresyon ",
            "project_id": 1,
            "release_id": rel["id"],
            "suite_id": 10,
            "test_case_ids": ["TC-003", "TC-005", "TC-003"],
        },
        headers=tester,
    )
    assert run_res.status_code == 201
    run = run_res.json()
    assert run["name"] == "Sprint 1 Regresyon"
    assert run["project_id"] == 1
    assert run["release_id"] == rel["id"]
    assert run["suite_id"] == 10
    assert run["created_by"] == "tester"
    assert [e["test_case_id"] for e in run["executions"]] == ["TC-003", "TC-005"]
    assert all(e["status"] == "Not Run" and e["defect_ids"] == [] for e in run["executions"])

    assert client.get("/api/test-runs").json() == [run]
    assert client.get(f"/api/test-runs/{run['id']}").json() == run
    assert client.get("/api/test-runs/999").status_code == 404

    ex_tc3, ex_tc5 = run["executions"]
    rec = client.post(
        f"/api/test-runs/{run['id']}/executions/{ex_tc3['id']}",
        json={"status": "Failed", "actual_result": "Hata verdi", "notes": "Log ekte", "defect_ids": [1]},
        headers=tester,
    )
    assert rec.status_code == 200
    ex_updated = rec.json()
    assert ex_updated["status"] == "Failed"
    assert ex_updated["actual_result"] == "Hata verdi"
    assert ex_updated["notes"] == "Log ekte"
    assert ex_updated["executed_by"] == "tester"
    assert ex_updated["executed_at"] is not None
    assert ex_updated["defect_ids"] == [1]

    # PUT works as well and updates TestCase.status
    rec2 = client.put(
        f"/api/test-runs/{run['id']}/executions/{ex_tc5['id']}",
        json={"status": "Passed", "actual_result": "PDF üretildi", "notes": ""},
        headers=lead,
    )
    assert rec2.status_code == 200 and rec2.json()["status"] == "Passed"
    tc5 = next(c for c in client.get("/api/test-cases").json() if c["id"] == "TC-005")
    assert tc5["status"] == "Passed"

    # Creating a defect directly from a failed execution links it and records history
    new_def = client.post(
        f"/api/test-runs/{run['id']}/executions/{ex_tc3['id']}/defects",
        json={"title": " Boş form hatası devam ediyor ", "severity": "High"},
        headers=tester,
    )
    assert new_def.status_code == 201
    d_body = new_def.json()
    assert d_body["title"] == "Boş form hatası devam ediyor"
    assert d_body["severity"] == "High"
    assert d_body["status"] == "Open"
    assert d_body["test_case"] == "TC-003"
    assert client.get(f"/api/defects/{d_body['id']}/history").json()[0]["to"] == "Open"

    refreshed = client.get(f"/api/test-runs/{run['id']}").json()
    assert refreshed["executions"][0]["defect_ids"] == [1, d_body["id"]]


def test_test_run_validation_and_roles(client):
    tester = as_user("tester")
    admin = as_user("admin")
    p2 = client.post("/api/projects", json={"name": "P2"}, headers=admin).json()
    r2 = client.post("/api/releases", json={"project_id": p2["id"], "version": "v1"}, headers=admin).json()

    valid_run = {"name": "Run 1", "project_id": 1, "test_case_ids": ["TC-001"]}
    assert client.post("/api/test-runs", json=valid_run).status_code == 401
    assert client.post("/api/test-runs", json=valid_run, headers=as_user("developer")).status_code == 403

    for bad_body in [
        {"name": "  ", "project_id": 1, "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 999, "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 1, "release_id": 999, "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 1, "release_id": r2["id"], "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 1, "test_case_ids": []},
        {"name": "Run", "project_id": 1, "test_case_ids": ["TC-999"]},
    ]:
        assert client.post("/api/test-runs", json=bad_body, headers=tester).status_code == 422

    run = client.post("/api/test-runs", json=valid_run, headers=tester).json()
    ex_id = run["executions"][0]["id"]
    exec_url = f"/api/test-runs/{run['id']}/executions/{ex_id}"
    def_url = f"{exec_url}/defects"

    assert client.post(exec_url, json={"status": "Passed"}).status_code == 401
    assert client.post(exec_url, json={"status": "Passed"}, headers=as_user("developer")).status_code == 403
    assert client.post(def_url, json={"title": "x"}).status_code == 401
    assert client.post(def_url, json={"title": "x"}, headers=as_user("developer")).status_code == 403

    assert client.post(f"/api/test-runs/999/executions/{ex_id}",
                       json={"status": "Passed"}, headers=tester).status_code == 404
    assert client.post(f"/api/test-runs/{run['id']}/executions/999",
                       json={"status": "Passed"}, headers=tester).status_code == 404
    assert client.post(f"/api/test-runs/{run['id']}/executions/999/defects",
                       json={"title": "x"}, headers=tester).status_code == 404
    assert client.post(exec_url, json={"status": "Not Run"}, headers=tester).status_code == 422
    assert client.post(exec_url, json={"status": "Passed", "defect_ids": [999]},
                       headers=tester).status_code == 422
    assert client.post(def_url, json={"title": "   "}, headers=tester).status_code == 422

    # Deleting project or release with test runs returns 409
    rel1 = client.post("/api/releases", json={"project_id": p2["id"], "version": "v2"}, headers=admin).json()
    client.post(
        "/api/test-runs",
        json={"name": "P2 Run", "project_id": p2["id"], "release_id": rel1["id"], "test_case_ids": ["TC-001"]},
        headers=tester,
    )
    assert client.delete(f"/api/releases/{rel1['id']}", headers=admin).status_code == 409
    assert client.delete(f"/api/projects/{p2['id']}", headers=admin).status_code == 409


def test_defect_close_requires_passed_verification_execution(client):
    dev = as_user("developer")
    tester = as_user("tester")

    # Defect 1 is linked to TC-003 (seed status: "Failed")
    client.post("/api/defects/1/transition", json={"to": "In Progress"}, headers=dev)
    client.post("/api/defects/1/transition", json={"to": "Resolved"}, headers=dev)

    # Cannot close while TC-003 is Failed and has no Passed verification execution
    res = client.post("/api/defects/1/transition", json={"to": "Closed"}, headers=tester)
    assert res.status_code == 409

    # Create a test run with TC-003 and record Blocked -> still cannot close
    run = client.post(
        "/api/test-runs",
        json={"name": "Doğrulama Koşumu", "project_id": 1, "test_case_ids": ["TC-003"]},
        headers=tester,
    ).json()
    ex_id = run["executions"][0]["id"]
    client.post(
        f"/api/test-runs/{run['id']}/executions/{ex_id}",
        json={"status": "Blocked", "actual_result": "Ortam kapalı"},
        headers=tester,
    )
    assert client.post("/api/defects/1/transition", json={"to": "Closed"}, headers=tester).status_code == 409

    # Record Passed execution -> now Resolved -> Closed succeeds
    client.post(
        f"/api/test-runs/{run['id']}/executions/{ex_id}",
        json={"status": "Passed", "actual_result": "Doğrulandı"},
        headers=tester,
    )
    closed = client.post("/api/defects/1/transition", json={"to": "Closed"}, headers=tester)
    assert closed.status_code == 200 and closed.json()["status"] == "Closed"

