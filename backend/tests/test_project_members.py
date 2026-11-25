"""PLN-40: Tester ve Developer yalnızca üye oldukları projelerin kayıtlarını görür ve değiştirir."""
import pytest

from tests.conftest import as_user, grant

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("fresh_seed")]


def user_id(client, username: str) -> int:
    users = client.get("/api/users", headers=as_user("admin")).json()
    return next(u["id"] for u in users if u["username"] == username)


@pytest.fixture
def other(client):
    """Tester'ın üye olmadığı, gereksinim, test vakası, sürüm, koşum ve defect içeren proje."""
    admin, lead = as_user("admin"), as_user("testlead")
    project = client.post("/api/projects", json={"name": "Hidden"}, headers=admin).json()
    pid = project["id"]
    client.post("/api/requirements", json={"id": "RH-1", "project_id": pid, "title": "Hidden req"},
                headers=admin)
    client.post("/api/test-cases", json={"id": "TH-1", "title": "Hidden case", "requirements": ["RH-1"]},
                headers=admin)
    release = client.post("/api/releases", json={"project_id": pid, "version": "H1"}, headers=admin).json()
    run = client.post("/api/test-runs", json={"name": "Hidden run", "project_id": pid,
                                              "test_case_ids": ["TH-1"]}, headers=lead).json()
    defect = client.post("/api/defects", json={"title": "Hidden defect", "test_case": "TH-1"},
                         headers=admin).json()
    return {"project": pid, "release": release["id"], "run": run["id"], "defect": defect["id"]}


def test_seeded_tester_and_developer_keep_access_to_existing_projects(client):
    every = client.get("/api/projects", headers=as_user("admin")).json()
    assert every
    for username in ("tester", "developer"):
        assert client.get("/api/projects", headers=as_user(username)).json() == every


def test_non_member_cannot_see_or_change_project_records(client, other):
    tester = as_user("tester")
    pid = other["project"]
    assert pid not in [p["id"] for p in client.get("/api/projects", headers=tester).json()]
    assert other["release"] not in [r["id"] for r in client.get("/api/releases", headers=tester).json()]
    assert "TH-1" not in [t["id"] for t in client.get("/api/test-cases", headers=tester).json()]
    assert other["defect"] not in [d["id"] for d in client.get("/api/defects", headers=tester).json()]
    assert other["run"] not in [r["id"] for r in client.get("/api/test-runs", headers=tester).json()]
    for url in (f"/api/projects/{pid}", f"/api/releases/{other['release']}/gate", "/api/test-cases/TH-1",
                f"/api/test-runs/{other['run']}", f"/api/defects/{other['defect']}/history",
                f"/api/metrics/expanded?project_id={pid}", f"/api/projects/{pid}/runs/imports",
                f"/api/releases/{other['release']}/summary-report/snapshots",
                f"/api/defects/{other['defect']}/incident-report/snapshots"):
        assert client.get(url, headers=tester).status_code == 404, url
    assert client.post(f"/api/defects/{other['defect']}/transition", json={"to": "In Progress"},
                       headers=as_user("developer")).status_code == 404
    assert client.post("/api/test-runs", json={"name": "x", "project_id": pid, "test_case_ids": ["TH-1"]},
                       headers=tester).status_code == 422
    assert client.post("/api/defects", json={"title": "x", "test_case": "TH-1"},
                       headers=tester).status_code == 422


def test_granting_and_removing_membership_opens_and_closes_access(client, other):
    tester, admin = as_user("tester"), as_user("admin")
    pid, tid = other["project"], user_id(client, "tester")
    grant(client, pid, "tester")
    assert client.get(f"/api/projects/{pid}", headers=tester).status_code == 200
    assert "TH-1" in [t["id"] for t in client.get("/api/test-cases", headers=tester).json()]
    assert [m["username"] for m in client.get(f"/api/projects/{pid}/members", headers=admin).json()] == ["tester"]
    assert client.put(f"/api/projects/{pid}/members/{tid}", headers=admin).status_code == 200  # idempotent
    remaining = client.delete(f"/api/projects/{pid}/members/{tid}", headers=as_user("testlead"))
    assert remaining.status_code == 200 and remaining.json() == []
    assert client.get(f"/api/projects/{pid}", headers=tester).status_code == 404


def test_only_admin_and_test_lead_manage_members(client, other):
    pid, tid = other["project"], user_id(client, "tester")
    for username in ("tester", "developer"):
        headers = as_user(username)
        assert client.get("/api/users", headers=headers).status_code == 403
        assert client.put(f"/api/projects/{pid}/members/{tid}", headers=headers).status_code == 403
        assert client.delete(f"/api/projects/{pid}/members/{tid}", headers=headers).status_code == 403
    admin = as_user("admin")
    assert client.put(f"/api/projects/{pid}/members/{user_id(client, 'testlead')}",
                      headers=admin).status_code == 422
    assert client.put(f"/api/projects/99999/members/{tid}", headers=admin).status_code == 404
    assert client.put(f"/api/projects/{pid}/members/99999", headers=admin).status_code == 404


def test_defect_without_test_case_stays_visible_to_everyone(client, other):
    defect = client.post("/api/defects", json={"title": "Unscoped"}, headers=as_user("admin")).json()
    assert defect["id"] in [d["id"] for d in client.get("/api/defects", headers=as_user("tester")).json()]


def test_project_with_members_can_still_be_deleted(client):
    admin = as_user("admin")
    project = client.post("/api/projects", json={"name": "Members only"}, headers=admin).json()
    grant(client, project["id"])
    assert client.delete(f"/api/projects/{project['id']}", headers=admin).status_code == 204


def test_admin_creates_accounts_but_never_another_admin(client):
    admin = as_user("admin")
    body = {"username": "new.tester", "password": "s3cret-pass", "role": "Tester"}
    created = client.post("/api/users", json=body, headers=admin)
    assert created.status_code == 201 and created.json()["role"] == "Tester"
    assert client.post("/api/users", json=body, headers=admin).status_code == 409
    assert client.post("/api/users", json={**body, "username": "boss", "role": "Admin"},
                       headers=admin).status_code == 422
    assert client.post("/api/users", json={**body, "username": "short", "password": "x"},
                       headers=admin).status_code == 422
    for username in ("testlead", "tester", "developer"):
        assert client.post("/api/users", json={**body, "username": f"by-{username}"},
                           headers=as_user(username)).status_code == 403
    login = client.post("/api/auth/login", json={"username": "new.tester", "password": "s3cret-pass"})
    token = {"Authorization": f"Bearer {login.json()['access_token']}"}
    # Yeni hesap üye yapılana kadar hiçbir projeyi görmez.
    assert client.get("/api/projects", headers=token).json() == []


def test_admin_deletes_accounts_except_admins(client):
    admin = as_user("admin")
    new = client.post("/api/users", json={"username": "temp.dev", "password": "s3cret-pass",
                                          "role": "Developer"}, headers=admin).json()
    grant(client, 1, "temp.dev")
    assert client.delete(f"/api/users/{new['id']}", headers=admin).status_code == 204
    assert "temp.dev" not in [u["username"] for u in client.get("/api/users", headers=admin).json()]
    assert client.delete(f"/api/users/{user_id(client, 'admin')}", headers=admin).status_code == 422
    assert client.delete(f"/api/users/{user_id(client, 'tester')}",
                         headers=as_user("testlead")).status_code == 403


def test_shared_test_case_needs_every_project_to_change(client, other):
    admin, tester = as_user("admin"), as_user("tester")
    seed_req = next(r["id"] for r in client.get("/api/requirements", headers=admin).json()
                    if r["project_id"] == 1)
    assert client.post("/api/test-cases", json={"id": "TX-1", "title": "Shared",
                                                "requirements": [seed_req, "RH-1"]},
                       headers=admin).status_code == 201
    assert client.get("/api/test-cases/TX-1", headers=tester).status_code == 200
    assert client.put("/api/test-cases/TX-1", json={"title": "Moved", "requirements": [seed_req]},
                      headers=tester).status_code == 404
    assert client.delete("/api/test-cases/TX-1", headers=tester).status_code == 404


def test_test_case_cannot_lose_its_last_project_link(client, other):
    response = client.put("/api/requirements/RH-1/test-cases", json={"test_cases": []},
                          headers=as_user("admin"))
    assert response.status_code == 422
    assert "TH-1" in [t["id"] for t in client.get("/api/test-cases", headers=as_user("admin")).json()]
