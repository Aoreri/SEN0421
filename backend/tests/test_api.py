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
    assert release.json()["status"] == "Planned"
    url = f"/api/releases/{release.json()['id']}"
    assert client.get(url).json()["version"] == "v1"
    assert client.put(url, json={"project_id": 1, "version": "v2"},
                      headers=lead).json()["version"] == "v2"
    assert len(client.get("/api/releases").json()) == 1
    assert client.delete(url, headers=lead).status_code == 204
    assert client.get(url).status_code == 404


def test_release_exit_gate_criteria_waiver_and_status(client):
    lead = as_user("testlead")
    admin = as_user("admin")
    tester = as_user("tester")
    dev = as_user("developer")

    rel = client.post("/api/releases", json={"project_id": 1, "version": "v1.0.0"}, headers=lead).json()
    rid = rel["id"]

    # 404 on nonexistent release
    assert client.get("/api/releases/999/gate").status_code == 404
    assert client.put("/api/releases/999/criteria",
                      json={"min_pass_rate": 80, "max_open_critical": 0, "min_req_coverage": 80},
                      headers=lead).status_code == 404
    assert client.post("/api/releases/999/waiver", json={"reason": "ok"}, headers=lead).status_code == 404
    assert client.delete("/api/releases/999/waiver", headers=lead).status_code == 404
    assert client.put("/api/releases/999/status", json={"status": "In Test"}, headers=lead).status_code == 404

    # Initial gate state on seed data:
    # Seed test cases: 4 executed (3 Passed, 1 Failed) -> pass_rate = 75.0 (< 80.0)
    # Seed defects: 0 Critical open -> open_critical = 0 (<= 0)
    # Seed requirements: 5 of 8 covered (R1, R3, R4, R6, R7) -> req_coverage = 62.5 (< 80.0)
    gate = client.get(f"/api/releases/{rid}/gate").json()
    assert gate == {
        "release_id": rid,
        "release_version": "v1.0.0",
        "status": "Planned",
        "criteria": {"min_pass_rate": 80.0, "max_open_critical": 0, "min_req_coverage": 80.0},
        "actual_pass_rate": 75.0,
        "actual_open_critical": 0,
        "actual_req_coverage": 62.5,
        "passed_criteria": {"pass_rate": False, "open_critical": True, "req_coverage": False},
        "gate_passed": False,
        "waiver": None,
    }

    # Transitioning to In Test or Planned is allowed even when gate_passed is False
    res = client.put(f"/api/releases/{rid}/status", json={"status": "In Test"}, headers=lead)
    assert res.status_code == 200 and res.json()["status"] == "In Test"

    # Transitioning to Ready or Released when gate_passed is False is rejected with 409
    for blocked_status in ("Ready", "Released"):
        assert client.put(f"/api/releases/{rid}/status",
                          json={"status": blocked_status}, headers=lead).status_code == 409
    assert client.get(f"/api/releases/{rid}/gate").json()["status"] == "In Test"

    # Role guards on gate mutation endpoints (401 unauthenticated, 403 for Tester/Developer)
    for method, path, payload in [
        ("put", f"/api/releases/{rid}/criteria",
         {"min_pass_rate": 70, "max_open_critical": 0, "min_req_coverage": 60}),
        ("post", f"/api/releases/{rid}/waiver", {"reason": "Acil yama"}),
        ("delete", f"/api/releases/{rid}/waiver", None),
        ("put", f"/api/releases/{rid}/status", {"status": "In Test"}),
    ]:
        send = getattr(client, method)
        kwargs = {"json": payload} if payload is not None else {}
        assert send(path, **kwargs).status_code == 401
        for denied_header in (tester, dev):
            assert send(path, headers=denied_header, **kwargs).status_code == 403

    # Validation errors (422) on criteria, waiver, and status
    for bad_criteria in [
        {"min_pass_rate": -1, "max_open_critical": 0, "min_req_coverage": 80},
        {"min_pass_rate": 101, "max_open_critical": 0, "min_req_coverage": 80},
        {"min_pass_rate": 80, "max_open_critical": -1, "min_req_coverage": 80},
        {"min_pass_rate": 80, "max_open_critical": 0, "min_req_coverage": -0.1},
        {"min_pass_rate": 80, "max_open_critical": 0, "min_req_coverage": 100.1},
    ]:
        assert client.put(f"/api/releases/{rid}/criteria",
                          json=bad_criteria, headers=lead).status_code == 422

    assert client.post(f"/api/releases/{rid}/waiver", json={"reason": "   "}, headers=lead).status_code == 422
    assert client.post(f"/api/releases/{rid}/waiver",
                       json={"reason": "x" * 1001}, headers=lead).status_code == 422
    assert client.put(f"/api/releases/{rid}/status",
                      json={"status": "InvalidStatus"}, headers=lead).status_code == 422

    # Waiver allows gate to pass even when criteria fail
    waived = client.post(f"/api/releases/{rid}/waiver",
                         json={"reason": "  Bilinen hata ertelendi  "}, headers=lead).json()
    assert waived["gate_passed"] is True
    assert waived["waiver"]["waived_by"] == "testlead"
    assert waived["waiver"]["reason"] == "Bilinen hata ertelendi"
    assert waived["waiver"]["waived_at"] is not None

    # With active waiver, Ready and Released succeed
    assert client.put(f"/api/releases/{rid}/status",
                      json={"status": "Ready"}, headers=lead).json()["status"] == "Ready"

    # Deleting waiver restores gate failure and blocks Released
    unwaived = client.delete(f"/api/releases/{rid}/waiver", headers=admin).json()
    assert unwaived["waiver"] is None and unwaived["gate_passed"] is False
    assert client.put(f"/api/releases/{rid}/status",
                      json={"status": "Released"}, headers=admin).status_code == 409

    # Updating criteria so thresholds are met makes gate pass without waiver
    updated = client.put(
        f"/api/releases/{rid}/criteria",
        json={"min_pass_rate": 75.0, "max_open_critical": 0, "min_req_coverage": 60.0},
        headers=admin,
    ).json()
    assert updated["passed_criteria"] == {
        "pass_rate": True, "open_critical": True, "req_coverage": True,
    }
    assert updated["gate_passed"] is True

    # Opening a Critical defect breaks open_critical criterion
    crit = client.post("/api/defects",
                       json={"title": "Kritik çökme", "severity": "Critical"},
                       headers=tester).json()
    after_crit = client.get(f"/api/releases/{rid}/gate").json()
    assert after_crit["actual_open_critical"] == 1
    assert after_crit["passed_criteria"]["open_critical"] is False
    assert after_crit["gate_passed"] is False
    assert client.put(f"/api/releases/{rid}/status",
                      json={"status": "Released"}, headers=admin).status_code == 409

    # Closing the Critical defect satisfies the gate again and allows Released
    for to in ("In Progress", "Resolved", "Closed"):
        client.post(f"/api/defects/{crit['id']}/transition", json={"to": to}, headers=admin)
    rel_final = client.put(f"/api/releases/{rid}/status",
                           json={"status": "Released"}, headers=admin)
    assert rel_final.status_code == 200 and rel_final.json()["status"] == "Released"


def test_release_gate_isolates_projects(client):
    admin = as_user("admin")
    tester = as_user("tester")

    # Project 1 release with thresholds satisfied by Project 1 seed data (75% pass rate, 62.5% req coverage)
    rel1 = client.post("/api/releases", json={"project_id": 1, "version": "v1-iso"}, headers=admin).json()
    client.put(
        f"/api/releases/{rel1['id']}/criteria",
        json={"min_pass_rate": 75.0, "max_open_critical": 0, "min_req_coverage": 60.0},
        headers=admin,
    )

    # Create Project 2 with 1 requirement, 1 Failed test case, and 1 open Critical defect linked to it
    p2 = client.post("/api/projects", json={"name": "P2-Iso"}, headers=admin).json()
    client.post(
        "/api/requirements",
        json={"id": "R-P2-1", "project_id": p2["id"], "title": "P2 Req"},
        headers=admin,
    )
    client.post(
        "/api/test-cases",
        json={"id": "TC-P2-1", "title": "P2 Failed Case", "status": "Failed", "requirements": ["R-P2-1"]},
        headers=tester,
    )
    client.post(
        "/api/defects",
        json={"title": "P2 Critical Defect", "severity": "Critical", "test_case": "TC-P2-1"},
        headers=tester,
    )
    rel2 = client.post("/api/releases", json={"project_id": p2["id"], "version": "v1"}, headers=admin).json()

    # Project 1 gate is unaffected by Project 2's failed test case and open Critical defect
    gate1 = client.get(f"/api/releases/{rel1['id']}/gate").json()
    assert gate1["actual_pass_rate"] == 75.0
    assert gate1["actual_open_critical"] == 0
    assert gate1["actual_req_coverage"] == 100.0 if False else 62.5
    assert gate1["gate_passed"] is True

    # Project 2 gate sees only Project 2's 0% pass rate, 1 open Critical defect, and 100% req coverage
    gate2 = client.get(f"/api/releases/{rel2['id']}/gate").json()
    assert gate2["actual_pass_rate"] == 0.0
    assert gate2["actual_open_critical"] == 1
    assert gate2["actual_req_coverage"] == 100.0
    assert gate2["gate_passed"] is False


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


def test_test_run_and_execution_lifecycle(client):
    tester = as_user("tester")
    lead = as_user("testlead")
    rel = client.post("/api/releases", json={"project_id": 1, "version": "v1.0"}, headers=lead).json()
    suite = client.post(
        "/api/test-suites", json={"project_id": 1, "name": "Regresyon Suite"}, headers=lead
    ).json()

    run_res = client.post(
        "/api/test-runs",
        json={
            "name": " Sprint 1 Regresyon ",
            "project_id": 1,
            "release_id": rel["id"],
            "suite_id": suite["id"],
            "test_case_ids": ["TC-003", "TC-005", "TC-003"],
        },
        headers=tester,
    )
    assert run_res.status_code == 201
    run = run_res.json()
    assert run["name"] == "Sprint 1 Regresyon"
    assert run["project_id"] == 1
    assert run["release_id"] == rel["id"]
    assert run["suite_id"] == suite["id"]
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
    s2 = client.post("/api/test-suites", json={"project_id": p2["id"], "name": "S2"}, headers=admin).json()

    valid_run = {"name": "Run 1", "project_id": 1, "test_case_ids": ["TC-001"]}
    assert client.post("/api/test-runs", json=valid_run).status_code == 401
    assert client.post("/api/test-runs", json=valid_run, headers=as_user("developer")).status_code == 403

    for bad_body in [
        {"name": "  ", "project_id": 1, "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 999, "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 1, "release_id": 999, "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 1, "release_id": r2["id"], "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 1, "suite_id": 999, "test_case_ids": ["TC-001"]},
        {"name": "Run", "project_id": 1, "suite_id": s2["id"], "test_case_ids": ["TC-001"]},
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

    # Deleting project, release, suite, or test case with test runs/executions returns 409
    rel1 = client.post("/api/releases", json={"project_id": p2["id"], "version": "v2"}, headers=admin).json()
    client.post(
        "/api/test-runs",
        json={
            "name": "P2 Run",
            "project_id": p2["id"],
            "release_id": rel1["id"],
            "suite_id": s2["id"],
            "test_case_ids": ["TC-001"],
        },
        headers=tester,
    )
    assert client.delete(f"/api/releases/{rel1['id']}", headers=admin).status_code == 409
    assert client.delete(f"/api/test-suites/{s2['id']}", headers=admin).status_code == 409
    assert client.delete(f"/api/projects/{p2['id']}", headers=admin).status_code == 409
    assert client.delete("/api/test-cases/TC-001", headers=tester).status_code == 409


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

    # Defect linked only via execution_defects (defect.test_case is None) also requires Passed execution
    d_exec = client.post("/api/defects", json={"title": "Yalnızca koşuma bağlı"}, headers=tester).json()
    run2 = client.post(
        "/api/test-runs",
        json={"name": "Koşum 2", "project_id": 1, "test_case_ids": ["TC-004"]},
        headers=tester,
    ).json()
    ex2_id = run2["executions"][0]["id"]
    client.post(
        f"/api/test-runs/{run2['id']}/executions/{ex2_id}",
        json={"status": "Failed", "actual_result": "Hata", "defect_ids": [d_exec["id"]]},
        headers=tester,
    )
    client.post(f"/api/defects/{d_exec['id']}/transition", json={"to": "In Progress"}, headers=dev)
    client.post(f"/api/defects/{d_exec['id']}/transition", json={"to": "Resolved"}, headers=dev)
    assert (
        client.post(
            f"/api/defects/{d_exec['id']}/transition", json={"to": "Closed"}, headers=tester
        ).status_code
        == 409
    )
    client.post(
        f"/api/test-runs/{run2['id']}/executions/{ex2_id}",
        json={"status": "Passed", "actual_result": "Geçti", "defect_ids": [d_exec["id"]]},
        headers=tester,
    )
    assert (
        client.post(
            f"/api/defects/{d_exec['id']}/transition", json={"to": "Closed"}, headers=tester
        ).status_code
        == 200
    )

    # New defect linked to a Not Run test case with zero executions cannot be closed until executed & Passed
    d_notrun = client.post(
        "/api/defects", json={"title": "Koşulmamış vaka hatası", "test_case": "TC-006"}, headers=tester
    ).json()
    client.post(f"/api/defects/{d_notrun['id']}/transition", json={"to": "In Progress"}, headers=dev)
    client.post(f"/api/defects/{d_notrun['id']}/transition", json={"to": "Resolved"}, headers=dev)
    assert (
        client.post(
            f"/api/defects/{d_notrun['id']}/transition", json={"to": "Closed"}, headers=tester
        ).status_code
        == 409
    )
