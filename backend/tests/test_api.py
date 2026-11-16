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


def test_test_suite_crud(client):
    lead = as_user("testlead")
    created = client.post("/api/test-suites",
                          json={"project_id": 1, "name": " Auth Suite ", "description": "Giriş"},
                          headers=lead)
    assert created.status_code == 201
    suite = created.json()
    assert suite == {
        "id": suite["id"], "project_id": 1, "name": "Auth Suite",
        "description": "Giriş", "test_cases": [],
    }
    url = f"/api/test-suites/{suite['id']}"
    assert client.get(url).json() == suite
    updated = client.put(url, json={"project_id": 1, "name": "Auth v2", "description": "d"},
                         headers=lead).json()
    assert updated["name"] == "Auth v2" and updated["description"] == "d"
    assert updated in client.get("/api/test-suites").json()
    assert client.delete(url, headers=lead).status_code == 204
    assert client.get(url).status_code == 404


def test_test_case_crud_and_specification_fields(client):
    lead = as_user("testlead")
    tester = as_user("tester")
    suite = client.post("/api/test-suites",
                        json={"project_id": 1, "name": "Smoke"},
                        headers=lead).json()
    body = {
        "id": " TC-007 ",
        "suite_id": suite["id"],
        "title": "  Suite oluşturma testi  ",
        "priority": "High",
        "automated": True,
        "steps": ["  1. Giriş yap  ", "2. Suite oluştur"],
        "expected_result": "  201 döner ve listede görünür  ",
        "status": "Not Run",
        "requirements": ["R2", "R1", "R2"],
    }
    created = client.post("/api/test-cases", json=body, headers=tester)
    assert created.status_code == 201
    tc = created.json()
    assert tc == {
        "id": "TC-007",
        "suite_id": suite["id"],
        "title": "Suite oluşturma testi",
        "requirement": "R1",
        "requirements": ["R1", "R2"],
        "status": "Not Run",
        "priority": "High",
        "automated": True,
        "steps": ["1. Giriş yap", "2. Suite oluştur"],
        "expected_result": "201 döner ve listede görünür",
    }
    assert client.get("/api/test-cases/TC-007").json() == tc
    assert client.get(f"/api/test-suites/{suite['id']}").json()["test_cases"] == ["TC-007"]
    assert "TC-007" in client.get("/api/requirements/R2").json()["test_cases"]

    updated = client.put("/api/test-cases/TC-007", json={
        "title": "Güncel başlık",
        "suite_id": None,
        "priority": "Critical",
        "automated": False,
        "steps": ["Tek adım"],
        "expected_result": "Başarılı",
        "status": "Passed",
        "requirements": ["R3"],
    }, headers=tester).json()
    assert updated["suite_id"] is None
    assert updated["priority"] == "Critical"
    assert updated["automated"] is False
    assert updated["status"] == "Passed"
    assert updated["requirement"] == "R3"
    assert updated["requirements"] == ["R3"]
    assert "TC-007" not in client.get("/api/requirements/R2").json()["test_cases"]

    relinked = client.put("/api/test-cases/TC-007/requirements",
                          json={"requirements": ["R5", "R2"]},
                          headers=tester).json()
    assert relinked["requirements"] == ["R2", "R5"]
    assert relinked["requirement"] == "R2"

    assert client.delete("/api/test-cases/TC-007", headers=tester).status_code == 204
    assert client.get("/api/test-cases/TC-007").status_code == 404


def test_test_case_and_suite_validation_and_conflicts(client):
    admin = as_user("admin")
    tester = as_user("tester")
    p2 = client.post("/api/projects", json={"name": "P2"}, headers=admin).json()
    s1 = client.post("/api/test-suites", json={"project_id": 1, "name": "S1"}, headers=admin).json()
    s2 = client.post("/api/test-suites", json={"project_id": p2["id"], "name": "S1"},
                     headers=admin).json()

    # Duplicate suite name in same project -> 409; different project -> allowed
    assert client.post("/api/test-suites", json={"project_id": 1, "name": "S1"},
                       headers=admin).status_code == 409
    assert client.post("/api/test-suites", json={"project_id": 999, "name": "S"},
                       headers=admin).status_code == 422

    # Duplicate test case id -> 409
    assert client.post("/api/test-cases", json={
        "id": "TC-001", "title": "Dup", "requirements": ["R1"],
    }, headers=tester).status_code == 409

    # Missing requirement links -> 422 (FR-REQ-01)
    assert client.post("/api/test-cases", json={
        "id": "TC-099", "title": "No req", "requirements": [],
    }, headers=tester).status_code == 422
    assert client.put("/api/test-cases/TC-001/requirements", json={"requirements": []},
                      headers=tester).status_code == 422

    # Unknown requirement or suite -> 422
    assert client.post("/api/test-cases", json={
        "id": "TC-099", "title": "Bad req", "requirements": ["R999"],
    }, headers=tester).status_code == 422
    assert client.post("/api/test-cases", json={
        "id": "TC-099", "title": "Bad suite", "suite_id": 999, "requirements": ["R1"],
    }, headers=tester).status_code == 422

    # Suite project and requirement project mismatch -> 422
    assert client.post("/api/test-cases", json={
        "id": "TC-099", "title": "Cross project", "suite_id": s2["id"], "requirements": ["R1"],
    }, headers=tester).status_code == 422

    # Blank step or invalid priority -> 422
    assert client.post("/api/test-cases", json={
        "id": "TC-099", "title": "Bad step", "steps": ["   "], "requirements": ["R1"],
    }, headers=tester).status_code == 422
    assert client.post("/api/test-cases", json={
        "id": "TC-099", "title": "Bad prio", "priority": "Urgent", "requirements": ["R1"],
    }, headers=tester).status_code == 422

    # Put TC-001 into s1; deleting s1 or moving s1 to P2 or deleting project P2 with s2 -> 409
    assert client.put("/api/test-cases/TC-001", json={
        "title": "Kullanıcı girişi başarılı", "suite_id": s1["id"], "status": "Passed",
        "requirements": ["R1"],
    }, headers=tester).status_code == 200
    assert client.delete(f"/api/test-suites/{s1['id']}", headers=admin).status_code == 409
    assert client.put(f"/api/test-suites/{s1['id']}",
                      json={"project_id": p2["id"], "name": "S1"},
                      headers=admin).status_code == 409
    assert client.delete(f"/api/projects/{p2['id']}", headers=admin).status_code == 409

    # Linking TC-001 (in project 1's suite s1) to a requirement in project 2 -> 422
    r_p2 = client.post("/api/requirements",
                       json={"id": "R-P2", "project_id": p2["id"], "title": "P2 req"},
                       headers=admin).json()
    assert client.put(f"/api/requirements/{r_p2['id']}/test-cases",
                      json={"test_cases": ["TC-001"]},
                      headers=tester).status_code == 422

    # Deleting TC-003 (has linked defect #1) -> 409
    assert client.delete("/api/test-cases/TC-003", headers=tester).status_code == 409


@pytest.mark.parametrize("method,url,body", [
    ("post", "/api/test-suites", {"project_id": 1, "name": "S"}),
    ("put", "/api/test-suites/1", {"project_id": 1, "name": "S"}),
    ("delete", "/api/test-suites/1", None),
])
def test_test_suite_writes_require_admin_or_lead(client, method, url, body):
    send = getattr(client, method)
    kwargs = {"json": body} if body else {}
    assert send(url, **kwargs).status_code == 401
    for username in ("tester", "developer"):
        assert send(url, headers=as_user(username), **kwargs).status_code == 403


@pytest.mark.parametrize("method,url,body", [
    ("post", "/api/test-cases", {"id": "TC-99", "title": "x", "requirements": ["R1"]}),
    ("put", "/api/test-cases/TC-001", {"title": "x", "requirements": ["R1"]}),
    ("delete", "/api/test-cases/TC-001", None),
    ("put", "/api/test-cases/TC-001/requirements", {"requirements": ["R1"]}),
])
def test_test_case_writes_reject_unauthenticated_and_developer(client, method, url, body):
    send = getattr(client, method)
    kwargs = {"json": body} if body else {}
    assert send(url, **kwargs).status_code == 401
    assert send(url, headers=as_user("developer"), **kwargs).status_code == 403
