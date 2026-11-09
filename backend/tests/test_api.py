"""API + migrasyon testi. Varsayılan olarak geçici SQLite kullanır; DATABASE_URL verilirse o veritabanında çalışır."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/test.db")

from datetime import UTC, datetime, timedelta  # noqa: E402
from functools import cache  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.auth import JWT_ALGORITHM, JWT_SECRET  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import DefectTransition  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
cfg = Config(str(BACKEND / "alembic.ini"))
cfg.set_main_option("script_location", str(BACKEND / "alembic"))
client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_seed():
    """Her testi temiz tohum durumuyla başlat; testler sıradan bağımsız olsun."""
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@cache
def as_user(username: str) -> dict:
    """Giriş yapıp Authorization başlığı döner (bcrypt yavaş olduğundan önbelleklenir)."""
    res = client.post("/api/auth/login", json={"username": username, "password": "demo1234"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_seed_and_metrics():
    assert len(client.get("/api/test-cases").json()) == 6
    assert client.get("/api/metrics").json() == {
        "total_tests": 6, "execution_rate": 66.7, "pass_rate": 75.0, "open_defects": 3,
    }


def test_defect_lifecycle_and_history():
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


def test_validation():
    tester = as_user("tester")
    assert client.post("/api/defects", json={"title": "  "}, headers=tester).status_code == 422
    assert client.post("/api/defects", json={"title": "x", "test_case": "TC-999"},
                       headers=tester).status_code == 422
    assert client.post("/api/defects/999/transition", json={"to": "Open"},
                       headers=tester).status_code == 404


def test_health():
    assert client.get("/api/health").json() == {"status": "ok", "template": True}


def test_rejected_requests_leave_data_unchanged():
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
def test_login_and_me(username, role):
    body = client.post("/api/auth/login", json={"username": username, "password": "demo1234"}).json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == username and body["user"]["role"] == role
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json() == body["user"]


@pytest.mark.parametrize("username,password", [("tester", "yanlis"), ("yok", "demo1234")])
def test_login_rejects_bad_credentials(username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 401 and "access_token" not in res.json()


def forged(secret=JWT_SECRET, expires_in=60, sub="1") -> dict:
    claims = {"sub": sub, "exp": datetime.now(UTC) + timedelta(seconds=expires_in)}
    return {"Authorization": f"Bearer {jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)}"}


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": "Bearer garbage"},
    forged(secret="x" * 32),
    forged(expires_in=-60),
    forged(sub="999"),
])
def test_bad_tokens_are_rejected(headers):
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_mutations_require_login_and_role():
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
def test_transition_roles(defect, to, allowed, denied):
    url = f"/api/defects/{defect}/transition"
    assert client.post(url, json={"to": to}, headers=as_user(denied)).status_code == 403
    res = client.post(url, json={"to": to}, headers=as_user(allowed))
    assert res.status_code == 200 and res.json()["status"] == to


def test_closed_defect_reopen_roles():
    url = "/api/defects/3/transition"
    client.post(url, json={"to": "Closed"}, headers=as_user("tester"))
    assert client.post(url, json={"to": "Open"}, headers=as_user("developer")).status_code == 403
    assert client.post(url, json={"to": "Open"}, headers=as_user("tester")).status_code == 200


def test_allowed_depends_on_role():
    def allowed(headers):
        return {d["id"]: d["allowed"] for d in client.get("/api/defects", headers=headers).json()}

    assert allowed({}) == {1: [], 2: [], 3: []}
    assert allowed(as_user("developer")) == {1: ["In Progress"], 2: ["Resolved"], 3: []}
    assert allowed(as_user("tester")) == {1: [], 2: [], 3: ["Closed", "Open"]}
    assert allowed(as_user("admin")) == {1: ["In Progress"], 2: ["Resolved"], 3: ["Closed", "Open"]}
    assert client.get("/api/defects", headers=forged(expires_in=-60)).status_code == 401


def test_denied_transitions_write_no_history():
    before = client.get("/api/defects/1/history").json()
    url = "/api/defects/1/transition"
    assert client.post(url, json={"to": "In Progress"}, headers=as_user("tester")).status_code == 403
    assert client.post(url, json={"to": "Nope"}, headers=as_user("admin")).status_code == 409
    assert client.get("/api/defects/1/history").json() == before


def test_transition_rules_come_from_the_database():
    with SessionLocal() as db:
        db.get_one(DefectTransition, ("Open", "In Progress")).allowed_roles = ["Tester"]
        db.commit()
    url = "/api/defects/1/transition"
    assert client.post(url, json={"to": "In Progress"}, headers=as_user("developer")).status_code == 403
    assert client.post(url, json={"to": "In Progress"}, headers=as_user("tester")).status_code == 200


def test_project_crud():
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


def test_release_crud():
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


def test_requirement_crud():
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
def test_invalid_writes(url, body, status):
    assert client.post(url, json=body, headers=as_user("admin")).status_code == status


def test_duplicate_release_version_conflicts():
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
def test_catalog_writes_are_role_guarded(method, url, body):
    send = getattr(client, method)
    kwargs = {"json": body} if body else {}
    assert send(url, **kwargs).status_code == 401
    for username in ("tester", "developer"):
        assert send(url, headers=as_user(username), **kwargs).status_code == 403


def test_delete_with_dependents_is_rejected():
    admin = as_user("admin")
    assert client.delete("/api/projects/1", headers=admin).status_code == 409
    assert client.delete("/api/requirements/R1", headers=admin).status_code == 409
    assert client.get("/api/requirements/R1").json()["test_cases"] == ["TC-001", "TC-002"]


def test_project_with_only_releases_cannot_be_deleted():
    admin = as_user("admin")
    project = client.post("/api/projects", json={"name": "P"}, headers=admin).json()
    client.post("/api/releases", json={"project_id": project["id"], "version": "v1"}, headers=admin)
    assert client.delete(f"/api/projects/{project['id']}", headers=admin).status_code == 409


def test_seed_traceability_matches_test_case_requirement():
    for case in client.get("/api/test-cases").json():
        assert case["requirements"] == [case["requirement"]]
    assert len(client.get("/api/requirements").json()) == 8


def test_traceability_is_many_to_many_and_replaceable():
    tester = as_user("tester")
    url = "/api/requirements/R2/test-cases"
    assert client.put(url, json={"test_cases": ["TC-001", "TC-003", "TC-001"]},
                      headers=tester).json()["test_cases"] == ["TC-001", "TC-003"]
    tc1 = next(c for c in client.get("/api/test-cases").json() if c["id"] == "TC-001")
    assert tc1["requirements"] == ["R1", "R2"]
    assert client.put(url, json={"test_cases": []}, headers=tester).json()["test_cases"] == []
    assert client.delete("/api/requirements/R2", headers=as_user("admin")).status_code == 204


def test_traceability_rejects_bad_input():
    url = "/api/requirements/R1/test-cases"
    body = {"test_cases": ["TC-999"]}
    assert client.put(url, json=body, headers=as_user("tester")).status_code == 422
    assert client.put("/api/requirements/R99/test-cases", json={"test_cases": []},
                      headers=as_user("tester")).status_code == 404
    links = {"test_cases": ["TC-001"]}
    assert client.put(url, json=links).status_code == 401
    assert client.put(url, json=links, headers=as_user("developer")).status_code == 403
    assert client.get("/api/requirements/R1").json()["test_cases"] == ["TC-001", "TC-002"]
