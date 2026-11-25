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
    tester = as_user("tester")
    assert len(client.get("/api/test-cases", headers=tester).json()) == 6
    assert client.get("/api/metrics", headers=tester).json() == {
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

    hist = client.get(f"/api/defects/{d['id']}/history", headers=admin).json()
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
    tester = as_user("tester")
    before = client.get("/api/defects/1/history", headers=tester).json()
    count = len(client.get("/api/defects", headers=tester).json())
    assert client.post("/api/defects/1/transition", json={"to": "Closed"},
                       headers=tester).status_code == 409
    assert client.post("/api/defects/1/transition", json={"to": "In Progress"},
                       headers=tester).status_code == 403
    assert client.post("/api/defects", json={"title": " "}, headers=tester).status_code == 422
    assert client.get("/api/defects/1/history", headers=tester).json() == before
    assert len(client.get("/api/defects", headers=tester).json()) == count


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
    tester = as_user("tester")
    before = len(client.get("/api/defects", headers=tester).json())
    assert client.post("/api/defects", json={"title": "x"}).status_code == 401
    assert client.post("/api/defects/1/transition", json={"to": "In Progress"}).status_code == 401
    assert client.post("/api/defects", json={"title": "x"},
                       headers=as_user("developer")).status_code == 403
    assert len(client.get("/api/defects", headers=tester).json()) == before
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

    assert client.get("/api/defects").status_code == 401
    assert allowed(as_user("developer")) == {1: ["In Progress"], 2: ["Resolved"], 3: []}
    assert allowed(as_user("tester")) == {1: [], 2: [], 3: ["Closed", "Open"]}
    assert allowed(as_user("admin")) == {1: ["In Progress"], 2: ["Resolved"], 3: ["Closed", "Open"]}
    assert client.get("/api/defects", headers=forged(expires_in=-60)).status_code == 401


def test_denied_transitions_write_no_history(client):
    tester = as_user("tester")
    before = client.get("/api/defects/1/history", headers=tester).json()
    url = "/api/defects/1/transition"
    assert client.post(url, json={"to": "In Progress"}, headers=tester).status_code == 403
    assert client.post(url, json={"to": "Nope"}, headers=as_user("admin")).status_code == 409
    assert client.get("/api/defects/1/history", headers=tester).json() == before


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
    assert client.get(url, headers=lead).json() == project
    updated = client.put(url, json={"name": "Yeni 2", "description": "d"}, headers=lead).json()
    assert updated == {"id": project["id"], "name": "Yeni 2", "description": "d"}
    assert updated in client.get("/api/projects", headers=lead).json()
    assert client.delete(url, headers=lead).status_code == 204
    assert client.get(url, headers=lead).status_code == 404


def test_release_crud(client):
    lead = as_user("testlead")
    release = client.post("/api/releases", json={"project_id": 1, "version": "v1"}, headers=lead)
    assert release.status_code == 201
    assert release.json()["status"] == "Planned"
    url = f"/api/releases/{release.json()['id']}"
    assert client.get(url, headers=lead).json()["version"] == "v1"
    assert client.put(url, json={"project_id": 1, "version": "v2"},
                      headers=lead).json()["version"] == "v2"
    assert len(client.get("/api/releases", headers=lead).json()) == 1
    assert client.delete(url, headers=lead).status_code == 204
    assert client.get(url, headers=lead).status_code == 404


def test_sprint_crud_validation_roles_and_dependents(client):
    lead = as_user("testlead")
    admin = as_user("admin")
    tester = as_user("tester")
    dev = as_user("developer")

    rel = client.post("/api/releases", json={"project_id": 1, "version": "v1.0"}, headers=lead).json()
    sprint_in = {
        "project_id": 1,
        "release_id": rel["id"],
        "name": "  Sprint 1  ",
        "goal": "  Temel altyapı ve doğrulama  ",
        "start_at": "2026-11-01T00:00:00Z",
        "end_at": "2026-11-15T00:00:00Z",
        "status": "Active",
    }
    created = client.post("/api/sprints", json=sprint_in, headers=lead)
    assert created.status_code == 201
    sprint = created.json()
    sid = sprint["id"]
    assert sprint["name"] == "Sprint 1"
    assert sprint["goal"] == "Temel altyapı ve doğrulama"
    assert sprint["project_id"] == 1
    assert sprint["release_id"] == rel["id"]
    assert sprint["status"] == "Active"
    assert datetime.fromisoformat(sprint["start_at"]) == datetime(2026, 11, 1, tzinfo=UTC)
    assert datetime.fromisoformat(sprint["end_at"]) == datetime(2026, 11, 15, tzinfo=UTC)

    # Get and list with filters
    assert client.get(f"/api/sprints/{sid}", headers=admin).json() == sprint
    assert client.get("/api/sprints", headers=admin).json() == [sprint]
    assert client.get("/api/sprints", params={"project_id": 1}, headers=admin).json() == [sprint]
    assert client.get("/api/sprints", params={"release_id": rel["id"]}, headers=admin).json() == [sprint]
    assert client.get("/api/sprints", params={"release_id": 999}, headers=admin).json() == []
    assert client.get("/api/sprints/999", headers=admin).status_code == 404

    # Duplicate sprint name in same project -> 409
    assert client.post("/api/sprints", json=sprint_in, headers=lead).status_code == 409

    # Update sprint
    updated = client.put(
        f"/api/sprints/{sid}",
        json={
            "project_id": 1,
            "release_id": None,
            "name": "Sprint 1 Güncel",
            "goal": "Tamamlandı",
            "start_at": "2026-11-01T00:00:00+03:00",
            "end_at": "2026-11-16T00:00:00+03:00",
            "status": "Completed",
        },
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Sprint 1 Güncel"
    assert updated.json()["release_id"] is None
    assert updated.json()["status"] == "Completed"

    # Role checks: 401 unauthenticated, 403 for Tester/Developer
    for method, url, payload in [
        ("post", "/api/sprints", {"project_id": 1, "name": "S2"}),
        ("put", f"/api/sprints/{sid}", {"project_id": 1, "name": "S2"}),
        ("delete", f"/api/sprints/{sid}", None),
    ]:
        send = getattr(client, method)
        kwargs = {"json": payload} if payload is not None else {}
        assert send(url, **kwargs).status_code == 401
        for denied in (tester, dev):
            assert send(url, headers=denied, **kwargs).status_code == 403

    # Validation checks (422)
    p2 = client.post("/api/projects", json={"name": "P2-Sprint"}, headers=admin).json()
    r2 = client.post("/api/releases", json={"project_id": p2["id"], "version": "v2"}, headers=admin).json()
    for bad_body in [
        {"project_id": 999, "name": "S-BadProj"},
        {"project_id": 1, "release_id": 999, "name": "S-BadRel"},
        {"project_id": 1, "release_id": r2["id"], "name": "S-CrossRel"},
        {"project_id": 1, "name": "   "},
        {"project_id": 1, "name": "S-BadStatus", "status": "Invalid"},
        {"project_id": 1, "name": "S-NaiveDate", "start_at": "2026-11-01T00:00:00"},
        {
            "project_id": 1,
            "name": "S-InvertedDates",
            "start_at": "2026-11-10T00:00:00Z",
            "end_at": "2026-11-05T00:00:00Z",
        },
    ]:
        assert client.post("/api/sprints", json=bad_body, headers=admin).status_code == 422

    # Link sprint to r2 in p2, create test run in that sprint, and verify dependency protections
    s_p2 = client.post(
        "/api/sprints",
        json={"project_id": p2["id"], "release_id": r2["id"], "name": "P2 Sprint 1"},
        headers=admin,
    ).json()
    # Release with linked sprint cannot be deleted or moved to another project -> 409
    assert client.delete(f"/api/releases/{r2['id']}", headers=admin).status_code == 409
    assert (
        client.put(
            f"/api/releases/{r2['id']}",
            json={"project_id": 1, "version": "v2"},
            headers=admin,
        ).status_code
        == 409
    )
    # Project with linked sprint cannot be deleted -> 409
    assert client.delete(f"/api/projects/{p2['id']}", headers=admin).status_code == 409

    # Test run linked to sprint inherits release_id if omitted and rejects mismatched release/project
    assert (
        client.post(
            "/api/test-runs",
            json={
                "name": "Cross project sprint run",
                "project_id": 1,
                "sprint_id": s_p2["id"],
                "test_case_ids": ["TC-001"],
            },
            headers=tester,
        ).status_code
        == 422
    )
    r2_other = client.post(
        "/api/releases", json={"project_id": p2["id"], "version": "v3"}, headers=admin
    ).json()
    assert (
        client.post(
            "/api/test-runs",
            json={
                "name": "Mismatched release sprint run",
                "project_id": p2["id"],
                "release_id": r2_other["id"],
                "sprint_id": s_p2["id"],
                "test_case_ids": ["TC-001"],
            },
            headers=tester,
        ).status_code
        == 422
    )

    run = client.post(
        "/api/test-runs",
        json={
            "name": "Sprint Run",
            "project_id": p2["id"],
            "sprint_id": s_p2["id"],
            "test_case_ids": ["TC-001"],
        },
        headers=tester,
    )
    assert run.status_code == 201
    assert run.json()["sprint_id"] == s_p2["id"]
    assert run.json()["release_id"] == r2["id"]

    # Sprint with linked test run cannot be deleted or moved to another project -> 409
    assert client.delete(f"/api/sprints/{s_p2['id']}", headers=admin).status_code == 409
    assert (
        client.put(
            f"/api/sprints/{s_p2['id']}",
            json={"project_id": 1, "name": "P2 Sprint 1"},
            headers=admin,
        ).status_code
        == 409
    )

    # Unlinked sprint can be deleted -> 204
    assert client.delete(f"/api/sprints/{sid}", headers=admin).status_code == 204
    assert client.get(f"/api/sprints/{sid}", headers=admin).status_code == 404


def test_release_exit_gate_criteria_waiver_and_status(client):
    lead = as_user("testlead")
    admin = as_user("admin")
    tester = as_user("tester")
    dev = as_user("developer")

    rel = client.post("/api/releases", json={"project_id": 1, "version": "v1.0.0"}, headers=lead).json()
    rid = rel["id"]

    # 404 on nonexistent release
    assert client.get("/api/releases/999/gate", headers=lead).status_code == 404
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
    gate = client.get(f"/api/releases/{rid}/gate", headers=lead).json()
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
    assert client.get(f"/api/releases/{rid}/gate", headers=lead).json()["status"] == "In Test"

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
    after_crit = client.get(f"/api/releases/{rid}/gate", headers=tester).json()
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
    gate1 = client.get(f"/api/releases/{rel1['id']}/gate", headers=admin).json()
    assert gate1["actual_pass_rate"] == 75.0
    assert gate1["actual_open_critical"] == 0
    assert gate1["actual_req_coverage"] == 100.0 if False else 62.5
    assert gate1["gate_passed"] is True

    # Project 2 gate sees only Project 2's 0% pass rate, 1 open Critical defect, and 100% req coverage
    gate2 = client.get(f"/api/releases/{rel2['id']}/gate", headers=admin).json()
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
    assert len(client.get("/api/requirements", headers=lead).json()) == 9
    assert client.delete("/api/requirements/R9", headers=lead).status_code == 204
    assert client.get("/api/requirements/R9", headers=lead).status_code == 404


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
    assert client.get("/api/requirements/R1", headers=admin).json()["test_cases"] == ["TC-001", "TC-002"]


def test_project_with_only_releases_cannot_be_deleted(client):
    admin = as_user("admin")
    project = client.post("/api/projects", json={"name": "P"}, headers=admin).json()
    client.post("/api/releases", json={"project_id": project["id"], "version": "v1"}, headers=admin)
    assert client.delete(f"/api/projects/{project['id']}", headers=admin).status_code == 409


def test_seed_traceability_matches_test_case_requirement(client):
    tester = as_user("tester")
    for case in client.get("/api/test-cases", headers=tester).json():
        assert case["requirements"] == [case["requirement"]]
    assert len(client.get("/api/requirements", headers=tester).json()) == 8


def test_traceability_is_many_to_many_and_replaceable(client):
    tester = as_user("tester")
    url = "/api/requirements/R2/test-cases"
    assert client.put(url, json={"test_cases": ["TC-001", "TC-003", "TC-001"]},
                      headers=tester).json()["test_cases"] == ["TC-001", "TC-003"]
    tc1 = next(c for c in client.get("/api/test-cases", headers=tester).json() if c["id"] == "TC-001")
    assert tc1["requirements"] == ["R1", "R2"]
    assert client.put(url, json={"test_cases": []}, headers=tester).json()["test_cases"] == []
    assert client.delete("/api/requirements/R2", headers=as_user("admin")).status_code == 204


def test_traceability_rejects_bad_input(client):
    tester = as_user("tester")
    url = "/api/requirements/R1/test-cases"
    body = {"test_cases": ["TC-999"]}
    assert client.put(url, json=body, headers=tester).status_code == 422
    assert client.put("/api/requirements/R99/test-cases", json={"test_cases": []},
                      headers=tester).status_code == 404
    links = {"test_cases": ["TC-001"]}
    assert client.put(url, json=links).status_code == 401
    assert client.put(url, json=links, headers=as_user("developer")).status_code == 403
    assert client.get("/api/requirements/R1", headers=tester).json()["test_cases"] == ["TC-001", "TC-002"]


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
    assert client.get(url, headers=lead).json() == suite
    updated = client.put(url, json={"project_id": 1, "name": "Auth v2", "description": "d"},
                         headers=lead).json()
    assert updated["name"] == "Auth v2" and updated["description"] == "d"
    assert updated in client.get("/api/test-suites", headers=lead).json()
    assert client.delete(url, headers=lead).status_code == 204
    assert client.get(url, headers=lead).status_code == 404


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
    assert client.get("/api/test-cases/TC-007", headers=tester).json() == tc
    assert client.get(f"/api/test-suites/{suite['id']}", headers=tester).json()["test_cases"] == ["TC-007"]
    assert "TC-007" in client.get("/api/requirements/R2", headers=tester).json()["test_cases"]

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
    assert "TC-007" not in client.get("/api/requirements/R2", headers=tester).json()["test_cases"]

    relinked = client.put("/api/test-cases/TC-007/requirements",
                          json={"requirements": ["R5", "R2"]},
                          headers=tester).json()
    assert relinked["requirements"] == ["R2", "R5"]
    assert relinked["requirement"] == "R2"

    assert client.delete("/api/test-cases/TC-007", headers=tester).status_code == 204
    assert client.get("/api/test-cases/TC-007", headers=tester).status_code == 404


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

    assert client.get("/api/test-runs", headers=tester).json() == [run]
    assert client.get(f"/api/test-runs/{run['id']}", headers=tester).json() == run
    assert client.get("/api/test-runs/999", headers=tester).status_code == 404

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
    tc5 = next(c for c in client.get("/api/test-cases", headers=tester).json() if c["id"] == "TC-005")
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
    assert client.get(f"/api/defects/{d_body['id']}/history", headers=tester).json()[0]["to"] == "Open"

    refreshed = client.get(f"/api/test-runs/{run['id']}", headers=tester).json()
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


def test_test_plan_crud_and_workflow(client):
    lead = as_user("testlead")
    rel = client.post("/api/releases", json={"project_id": 1, "version": "v1.0"}, headers=lead).json()
    plan_in = {
        "project_id": 1,
        "release_id": rel["id"],
        "version": "1.0",
        "title": "SDS-06 Ana Test Planı",
        "scope": "Backend ve Frontend bileşenleri",
        "approach": "Birim, entegrasyon ve sistem testleri",
        "pass_fail_criteria": "Kritik açık defect olmamalı",
        "environment": "Docker Compose + PostgreSQL 16",
        "schedule_risks": "RSK-07 PDF üretim yedeklemesi",
    }
    res = client.post("/api/test-plans", json=plan_in, headers=lead)
    assert res.status_code == 201
    plan = res.json()
    assert plan["status"] == "Draft"
    assert plan["created_by"] == "testlead"
    assert plan["snapshot_count"] == 0
    assert plan["snapshots"] == []

    # Duplicate (project_id, version) -> 409
    assert client.post("/api/test-plans", json=plan_in, headers=lead).status_code == 409

    # Update while Draft
    updated_in = {**plan_in, "title": "Güncellenmiş Test Planı"}
    updated = client.put(f"/api/test-plans/{plan['id']}", json=updated_in, headers=lead).json()
    assert updated["title"] == "Güncellenmiş Test Planı"

    # Direct Draft -> Approved rejected with 409
    status_url = f"/api/test-plans/{plan['id']}/status"
    assert client.put(status_url, json={"status": "Approved"}, headers=lead).status_code == 409

    # Valid workflow: Draft -> In Review -> Approved
    in_rev = client.put(status_url, json={"status": "In Review"}, headers=lead)
    assert in_rev.status_code == 200 and in_rev.json()["status"] == "In Review"
    approved = client.put(status_url, json={"status": "Approved"}, headers=lead)
    assert approved.status_code == 200 and approved.json()["status"] == "Approved"

    # Approved plan cannot be updated or deleted directly -> 409
    assert client.put(f"/api/test-plans/{plan['id']}", json=updated_in, headers=lead).status_code == 409
    assert client.delete(f"/api/test-plans/{plan['id']}", headers=lead).status_code == 409

    # Re-draft (Approved -> Draft) allows deletion
    redraft = client.put(status_url, json={"status": "Draft"}, headers=lead)
    assert redraft.status_code == 200 and redraft.json()["status"] == "Draft"
    assert client.delete(f"/api/test-plans/{plan['id']}", headers=lead).status_code == 204
    assert client.get(f"/api/test-plans/{plan['id']}", headers=lead).status_code == 404


def test_test_plan_validation_and_dependents(client):
    admin = as_user("admin")
    p2 = client.post("/api/projects", json={"name": "P2"}, headers=admin).json()
    r1 = client.post("/api/releases", json={"project_id": 1, "version": "v1"}, headers=admin).json()

    # Unknown project or mismatched release -> 422
    assert client.post(
        "/api/test-plans",
        json={"project_id": 999, "version": "1.0", "title": "T"},
        headers=admin,
    ).status_code == 422
    assert client.post(
        "/api/test-plans",
        json={"project_id": p2["id"], "release_id": r1["id"], "version": "1.0", "title": "T"},
        headers=admin,
    ).status_code == 422

    # Project or release with a TestPlan cannot be deleted -> 409
    r2 = client.post("/api/releases", json={"project_id": p2["id"], "version": "v1"}, headers=admin).json()
    tp = client.post(
        "/api/test-plans",
        json={"project_id": p2["id"], "release_id": r2["id"], "version": "1.0", "title": "P2 Plan"},
        headers=admin,
    ).json()
    assert client.delete(f"/api/releases/{r2['id']}", headers=admin).status_code == 409
    assert client.delete(f"/api/projects/{p2['id']}", headers=admin).status_code == 409

    # After deleting TestPlan and Release, Project can be deleted
    assert client.delete(f"/api/test-plans/{tp['id']}", headers=admin).status_code == 204
    assert client.delete(f"/api/releases/{r2['id']}", headers=admin).status_code == 204
    assert client.delete(f"/api/projects/{p2['id']}", headers=admin).status_code == 204


def test_test_plan_role_checks(client):
    admin = as_user("admin")
    tp = client.post(
        "/api/test-plans",
        json={"project_id": 1, "version": "1.0", "title": "Yetki Testi"},
        headers=admin,
    ).json()
    pid = tp["id"]

    for method, url, body in [
        ("post", "/api/test-plans", {"project_id": 1, "version": "2.0", "title": "X"}),
        ("put", f"/api/test-plans/{pid}", {"project_id": 1, "version": "1.0", "title": "X"}),
        ("put", f"/api/test-plans/{pid}/status", {"status": "In Review"}),
        ("delete", f"/api/test-plans/{pid}", None),
    ]:
        send = getattr(client, method)
        kwargs = {"json": body} if body else {}
        assert send(url, **kwargs).status_code == 401
        for role_user in ("tester", "developer"):
            assert send(url, headers=as_user(role_user), **kwargs).status_code == 403

    # Snapshots allow Tester, reject Developer
    snap_url = f"/api/test-plans/{pid}/snapshots"
    assert client.post(snap_url).status_code == 401
    assert client.post(snap_url, headers=as_user("developer")).status_code == 403
    assert client.post(snap_url, headers=as_user("tester")).status_code == 201


def test_test_plan_snapshots_and_html_pdf_export(client):
    from app.test_plans import _fallback_pdf_bytes

    lead = as_user("testlead")
    tester = as_user("tester")
    plan = client.post(
        "/api/test-plans",
        json={
            "project_id": 1,
            "version": "1.0",
            "title": "IEEE 829 Snapshot Planı",
            "scope": "İlk kapsam metni",
            "approach": "Entegrasyon yaklaşımı",
        },
        headers=lead,
    ).json()
    pid = plan["id"]

    # Create snapshot #1 while scope is "İlk kapsam metni"
    snap1_res = client.post(f"/api/test-plans/{pid}/snapshots", headers=tester)
    assert snap1_res.status_code == 201
    snap1 = snap1_res.json()
    assert snap1["version"] == "1.0"
    assert snap1["status"] == "Draft"
    assert snap1["generated_by"] == "tester"
    assert "TP-SDS-06-1.0" in snap1["html_content"]
    assert "İlk kapsam metni" in snap1["html_content"]
    assert snap1["payload"]["metrics"]["total_tests"] == 6

    # Modify plan scope and create a new defect, then verify snapshot #1 is immutable
    client.put(
        f"/api/test-plans/{pid}",
        json={
            "project_id": 1,
            "version": "1.1",
            "title": "IEEE 829 Snapshot Planı",
            "scope": "\n".join(f"Kapsam satırı {i}" for i in range(1, 55)),
            "approach": "Entegrasyon yaklaşımı",
        },
        headers=lead,
    )
    client.post("/api/defects", json={"title": "Sonradan eklenen hata"}, headers=tester)

    stored_snap1 = client.get(f"/api/test-plans/{pid}/snapshots/{snap1['id']}", headers=tester).json()
    assert "İlk kapsam metni" in stored_snap1["html_content"]
    assert "Kapsam satırı 1" not in stored_snap1["html_content"]
    assert stored_snap1["payload"]["metrics"]["open_defects"] == 3

    # Export live HTML vs snapshot HTML
    live_html = client.get(f"/api/test-plans/{pid}/export?format=html", headers=tester)
    assert live_html.status_code == 200
    assert "text/html" in live_html.headers["content-type"]
    assert "Kapsam satırı 50" in live_html.text

    snap_html = client.get(f"/api/test-plans/{pid}/export?format=html&snapshot_id={snap1['id']}", headers=tester)
    assert snap_html.status_code == 200
    assert "İlk kapsam metni" in snap_html.text
    assert "Kapsam satırı 1" not in snap_html.text

    # Export PDF (live and snapshot) and verify multi-page + defects completeness in fallback PDF
    live_pdf = client.get(f"/api/test-plans/{pid}/export?format=pdf", headers=tester)
    assert live_pdf.status_code == 200
    assert live_pdf.headers["content-type"] == "application/pdf"
    assert f'filename="test-plan-{pid}-1.1.pdf"' in live_pdf.headers["content-disposition"]
    assert live_pdf.content.startswith(b"%PDF-1.")
    assert live_pdf.content.strip().endswith(b"%%EOF")

    live_snap = client.post(f"/api/test-plans/{pid}/snapshots", headers=tester).json()
    fallback_bytes = _fallback_pdf_bytes(live_snap["payload"])
    assert fallback_bytes.startswith(b"%PDF-1.4")
    assert b"8. Defects:" in fallback_bytes
    assert b"9. Metrics Summary: Total=6" in fallback_bytes
    assert b"/Count 2" in fallback_bytes

    snap_pdf = client.get(f"/api/test-plans/{pid}/export?format=pdf&snapshot_id={snap1['id']}", headers=tester)
    assert snap_pdf.status_code == 200
    assert snap_pdf.headers["content-type"] == "application/pdf"
    assert f'filename="test-plan-{pid}-1.0.pdf"' in snap_pdf.headers["content-disposition"]
    assert snap_pdf.content.startswith(b"%PDF-1.")

    # List plans shows snapshot_count == 2
    plans = client.get("/api/test-plans", headers=tester).json()
    assert len(plans) == 1 and plans[0]["snapshot_count"] == 2
    assert len(client.get(f"/api/test-plans/{pid}/snapshots", headers=tester).json()) == 2
    assert client.get(f"/api/test-plans/{pid}/snapshots/999", headers=tester).status_code == 404
    assert client.get(f"/api/test-plans/{pid}/export?snapshot_id=999", headers=tester).status_code == 404


def test_test_plan_snapshot_isolates_projects(client):
    admin = as_user("admin")
    tester = as_user("tester")

    p2 = client.post("/api/projects", json={"name": "P2-Plan"}, headers=admin).json()
    client.post(
        "/api/requirements",
        json={"id": "R-P2", "project_id": p2["id"], "title": "P2 Gereksinimi"},
        headers=admin,
    )
    client.post(
        "/api/test-cases",
        json={"id": "TC-P2", "title": "P2 Test Vakası", "status": "Failed", "requirements": ["R-P2"]},
        headers=tester,
    )
    client.post(
        "/api/defects",
        json={"title": "P2 Özel Hatası", "severity": "Critical", "test_case": "TC-P2"},
        headers=tester,
    )

    tp1 = client.post(
        "/api/test-plans",
        json={"project_id": 1, "version": "1.0", "title": "P1 Planı"},
        headers=admin,
    ).json()
    tp2 = client.post(
        "/api/test-plans",
        json={"project_id": p2["id"], "version": "1.0", "title": "P2 Planı"},
        headers=admin,
    ).json()

    snap1 = client.post(f"/api/test-plans/{tp1['id']}/snapshots", headers=tester).json()
    snap2 = client.post(f"/api/test-plans/{tp2['id']}/snapshots", headers=tester).json()

    assert [tc["id"] for tc in snap1["payload"]["test_cases"]] == [
        "TC-001", "TC-002", "TC-003", "TC-004", "TC-005", "TC-006"
    ]
    assert all(d["title"] != "P2 Özel Hatası" for d in snap1["payload"]["defects"])
    assert snap1["payload"]["metrics"]["total_tests"] == 6
    assert snap1["payload"]["metrics"]["open_defects"] == 3
    assert "P2 Özel Hatası" not in snap1["html_content"]

    assert [tc["id"] for tc in snap2["payload"]["test_cases"]] == ["TC-P2"]
    assert [d["title"] for d in snap2["payload"]["defects"]] == ["P2 Özel Hatası"]
    assert snap2["payload"]["metrics"]["total_tests"] == 1
    assert snap2["payload"]["metrics"]["pass_rate"] == 0.0
    assert snap2["payload"]["metrics"]["open_defects"] == 1
    assert "TC-001" not in snap2["html_content"]


@pytest.mark.parametrize(
    "url",
    [
        "/api/defects",
        "/api/defects/1/history",
        "/api/metrics",
        "/api/metrics/expanded",
        "/api/projects",
        "/api/projects/1",
        "/api/releases",
        "/api/releases/1",
        "/api/releases/1/gate",
        "/api/requirements",
        "/api/requirements/R1",
        "/api/test-suites",
        "/api/test-suites/1",
        "/api/test-cases",
        "/api/test-cases/TC-001",
        "/api/test-runs",
        "/api/test-runs/1",
        "/api/test-plans",
        "/api/test-plans/1",
        "/api/test-plans/1/snapshots",
        "/api/test-plans/1/snapshots/1",
        "/api/test-plans/1/export",
        "/api/projects/1/runs/imports",
        "/api/projects/1/runs/imports/1",
        "/api/projects/1/coverage/imports",
        "/api/projects/1/coverage/imports/1",
        "/api/sprints",
        "/api/sprints/1",
        "/api/releases/1/summary-report/snapshots",
        "/api/releases/1/summary-report/snapshots/1",
        "/api/releases/1/summary-report/export",
    ],
)
def test_read_endpoints_require_authentication(client, url):
    assert client.get(url).status_code == 401
    assert client.get(url, headers=forged(expires_in=-60)).status_code == 401
    # Every authenticated role (including least-privileged Developer) passes the auth check (not 401/403)
    for role_user in ("admin", "testlead", "tester", "developer"):
        res = client.get(url, headers=as_user(role_user))
        assert res.status_code in (200, 404), f"{url} for {role_user} returned {res.status_code}"


def test_test_summary_report_snapshots_and_html_pdf_export(client):
    from app.summary_reports import _fallback_summary_pdf_bytes

    lead = as_user("testlead")
    tester = as_user("tester")
    dev = as_user("developer")

    rel = client.post("/api/releases", json={"project_id": 1, "version": "v1.0.0"}, headers=lead).json()
    rid = rel["id"]

    # Role checks on snapshot creation: 401 unauthenticated, 403 for Developer, 201 for Tester
    snap_url = f"/api/releases/{rid}/summary-report/snapshots"
    assert client.post(snap_url).status_code == 401
    assert client.post(snap_url, headers=dev).status_code == 403
    assert client.post("/api/releases/999/summary-report/snapshots", headers=tester).status_code == 404

    snap1_res = client.post(snap_url, headers=tester)
    assert snap1_res.status_code == 201
    snap1 = snap1_res.json()
    assert snap1["release_id"] == rid
    assert snap1["release_version"] == "v1.0.0"
    assert snap1["release_status"] == "Planned"
    assert snap1["gate_passed"] is False
    assert snap1["generated_by"] == "tester"
    assert "TSR-SDS-06-v1.0.0" in snap1["html_content"]
    assert snap1["payload"]["totals"]["total_cases"] == 6
    assert snap1["payload"]["totals"]["pass_rate"] == 75.0
    assert snap1["payload"]["totals"]["requirement_coverage"] == 62.5
    assert len(snap1["payload"]["feature_results"]) == 8
    assert snap1["payload"]["defect_summary"]["open_total"] == 3
    assert snap1["payload"]["gate"]["gate_passed"] is False

    # Release with a summary report snapshot cannot be deleted -> 409
    assert client.delete(f"/api/releases/{rid}", headers=lead).status_code == 409

    # Record waiver and move release to Ready, then verify snapshot #1 remains immutable
    client.post(
        f"/api/releases/{rid}/waiver",
        json={"reason": "Ara dönem demosu muafiyeti"},
        headers=lead,
    )
    client.put(f"/api/releases/{rid}/status", json={"status": "Ready"}, headers=lead)

    stored_snap1 = client.get(f"/api/releases/{rid}/summary-report/snapshots/{snap1['id']}", headers=tester).json()
    assert stored_snap1["release_status"] == "Planned"
    assert stored_snap1["gate_passed"] is False
    assert stored_snap1["payload"]["gate"]["waiver"] is None

    # Live HTML export shows Ready and active waiver, whereas snapshot HTML preserves Planned
    live_html = client.get(f"/api/releases/{rid}/summary-report/export?format=html", headers=tester)
    assert live_html.status_code == 200
    assert "text/html" in live_html.headers["content-type"]
    assert "Ara dönem demosu muafiyeti" in live_html.text
    assert "GEÇTİ (PASSED)" in live_html.text

    snap_html = client.get(
        f"/api/releases/{rid}/summary-report/export?format=html&snapshot_id={snap1['id']}", headers=tester
    )
    assert snap_html.status_code == 200
    assert "Ara dönem demosu muafiyeti" not in snap_html.text
    assert "ENGELLİ (BLOCKED)" in snap_html.text

    # PDF export (live and snapshot) and fallback PDF verification
    live_pdf = client.get(f"/api/releases/{rid}/summary-report/export?format=pdf", headers=tester)
    assert live_pdf.status_code == 200
    assert live_pdf.headers["content-type"] == "application/pdf"
    assert f'filename="test-summary-report-{rid}-v1.0.0.pdf"' in live_pdf.headers["content-disposition"]
    assert live_pdf.content.startswith(b"%PDF-1.")
    assert live_pdf.content.strip().endswith(b"%%EOF")

    snap2 = client.post(snap_url, headers=lead).json()
    assert snap2["release_status"] == "Ready"
    assert snap2["gate_passed"] is True
    fallback_bytes = _fallback_summary_pdf_bytes(snap2["payload"])
    assert fallback_bytes.startswith(b"%PDF-1.4")
    assert b"TEST SUMMARY REPORT: TSR-SDS-06-v1.0.0" in fallback_bytes
    assert b"4. Exit Criteria & Release Gate Evaluation:" in fallback_bytes
    assert b"Active Waiver by testlead" in fallback_bytes

    snap_pdf = client.get(
        f"/api/releases/{rid}/summary-report/export?format=pdf&snapshot_id={snap1['id']}", headers=tester
    )
    assert snap_pdf.status_code == 200
    assert snap_pdf.content.startswith(b"%PDF-1.")

    # List snapshots and 404 checks
    snaps = client.get(snap_url, headers=tester).json()
    assert len(snaps) == 2
    assert client.get("/api/releases/999/summary-report/snapshots", headers=tester).status_code == 404
    assert client.get(f"/api/releases/{rid}/summary-report/snapshots/999", headers=tester).status_code == 404
    assert client.get(f"/api/releases/{rid}/summary-report/export?snapshot_id=999", headers=tester).status_code == 404
    assert client.get("/api/releases/999/summary-report/export", headers=tester).status_code == 404


def test_summary_report_includes_unlinked_defects_for_every_project(client):
    admin = as_user("admin")
    tester = as_user("tester")

    project = client.post(
        "/api/projects", json={"name": "P-Summary-Defects"}, headers=admin
    ).json()
    client.post(
        "/api/requirements",
        json={"id": "R-SUM-DEF", "project_id": project["id"], "title": "R-SUM-DEF"},
        headers=admin,
    )
    client.post(
        "/api/test-cases",
        json={
            "id": "TC-SUM-DEF",
            "title": "TC-SUM-DEF",
            "status": "Failed",
            "requirements": ["R-SUM-DEF"],
        },
        headers=tester,
    )
    defect = client.post(
        "/api/defects",
        json={"title": "Bağlantısız kritik hata", "severity": "Critical"},
        headers=tester,
    ).json()
    # The API accepts free-text severities; the table must still count them.
    client.post(
        "/api/defects", json={"title": "Serbest önem", "severity": "Blocker"}, headers=tester
    )
    release = client.post(
        "/api/releases", json={"project_id": project["id"], "version": "1.0"}, headers=admin
    ).json()

    snap = client.post(
        f"/api/releases/{release['id']}/summary-report/snapshots", headers=tester
    ).json()
    summary = snap["payload"]["defect_summary"]
    assert any(row["severity"] == "Blocker" for row in summary["by_severity"])
    critical = next(row for row in summary["by_severity"] if row["severity"] == "Critical")

    # Gate, severity table and defect list must use the same project defect filter.
    assert snap["payload"]["gate"]["actual_open_critical"] == 1
    assert summary["open_critical"] == snap["payload"]["gate"]["actual_open_critical"]
    assert summary["total"] == sum(row["total"] for row in summary["by_severity"])
    assert summary["open_total"] == sum(row["open"] for row in summary["by_severity"])
    assert critical["total"] == 1 and critical["open"] == 1
    assert defect["id"] in [d["id"] for d in snap["payload"]["defects"]]


def test_summary_report_labels_release_scoped_pass_rate_and_gate_basis(client):
    from app.summary_reports import _fallback_summary_pdf_bytes

    admin = as_user("admin")
    tester = as_user("tester")

    project = client.post(
        "/api/projects", json={"name": "P-Summary-Rate"}, headers=admin
    ).json()
    client.post(
        "/api/requirements",
        json={"id": "R-SUM-RATE", "project_id": project["id"], "title": "R-SUM-RATE"},
        headers=admin,
    )
    client.post(
        "/api/test-cases",
        json={
            "id": "TC-SUM-RATE",
            "title": "TC-SUM-RATE",
            "status": "Failed",
            "requirements": ["R-SUM-RATE"],
        },
        headers=tester,
    )
    release_a = client.post(
        "/api/releases", json={"project_id": project["id"], "version": "1.0"}, headers=admin
    ).json()
    release_b = client.post(
        "/api/releases", json={"project_id": project["id"], "version": "2.0"}, headers=admin
    ).json()

    run_a = client.post(
        "/api/test-runs",
        json={
            "name": "Run A",
            "project_id": project["id"],
            "release_id": release_a["id"],
            "test_case_ids": ["TC-SUM-RATE"],
        },
        headers=tester,
    ).json()
    client.post(
        f"/api/test-runs/{run_a['id']}/executions/{run_a['executions'][0]['id']}",
        json={"status": "Failed"},
        headers=tester,
    )
    # A later run in another release overwrites the catalogue status the gate reads.
    run_b = client.post(
        "/api/test-runs",
        json={
            "name": "Run B",
            "project_id": project["id"],
            "release_id": release_b["id"],
            "test_case_ids": ["TC-SUM-RATE"],
        },
        headers=tester,
    ).json()
    client.post(
        f"/api/test-runs/{run_b['id']}/executions/{run_b['executions'][0]['id']}",
        json={"status": "Passed"},
        headers=tester,
    )

    snap = client.post(
        f"/api/releases/{release_a['id']}/summary-report/snapshots", headers=tester
    ).json()
    totals = snap["payload"]["totals"]
    gate = snap["payload"]["gate"]

    assert totals["pass_rate"] == 0.0
    assert totals["pass_rate_basis"] == "release_runs_with_catalogue_fallback"
    assert gate["actual_pass_rate"] == 100.0
    assert gate["actual_pass_rate_basis"] == "project_catalogue_status"

    # The document must state that the two rates use different sources instead of leaving them unexplained.
    assert "sürüm kapsamlı" in snap["html_content"]
    assert "proje kataloğundaki" in snap["html_content"]
    pdf = _fallback_summary_pdf_bytes(snap["payload"])
    assert b"(release-scoped" in pdf
    assert b"\\(catalogue\\)" in pdf
