"""API + migrasyon testi. Varsayılan olarak geçici SQLite kullanır; DATABASE_URL verilirse o veritabanında çalışır."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mkdtemp()}/test.db")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
cfg = Config(str(BACKEND / "alembic.ini"))
cfg.set_main_option("script_location", str(BACKEND / "alembic"))
command.downgrade(cfg, "base")
command.upgrade(cfg, "head")
client = TestClient(app)


def test_seed_and_metrics():
    assert len(client.get("/api/test-cases").json()) == 6
    assert client.get("/api/metrics").json() == {
        "total_tests": 6, "execution_rate": 66.7, "pass_rate": 75.0, "open_defects": 3,
    }


def test_defect_lifecycle_and_history():
    d = client.post("/api/defects", json={"title": "Yeni hata", "test_case": "TC-001"}).json()
    assert d["id"] == 4 and d["status"] == "Open" and d["allowed"] == ["In Progress"]

    assert client.post(f"/api/defects/{d['id']}/transition", json={"to": "Closed"}).status_code == 400
    for to in ("In Progress", "Resolved", "Closed", "Open"):
        assert client.post(f"/api/defects/{d['id']}/transition", json={"to": to}).json()["status"] == to

    hist = client.get(f"/api/defects/{d['id']}/history").json()
    assert [(h["from"], h["to"]) for h in hist] == [
        (None, "Open"), ("Open", "In Progress"), ("In Progress", "Resolved"),
        ("Resolved", "Closed"), ("Closed", "Open"),
    ]


def test_validation():
    assert client.post("/api/defects", json={"title": "  "}).status_code == 422
    assert client.post("/api/defects", json={"title": "x", "test_case": "TC-999"}).status_code == 422
    assert client.post("/api/defects/999/transition", json={"to": "Open"}).status_code == 404


def test_health():
    assert client.get("/api/health").json() == {"status": "ok", "template": True}


def test_rejected_requests_leave_data_unchanged():
    before = client.get("/api/defects/1/history").json()
    count = len(client.get("/api/defects").json())
    assert client.post("/api/defects/1/transition", json={"to": "Closed"}).status_code == 400
    assert client.post("/api/defects", json={"title": " "}).status_code == 422
    assert client.get("/api/defects/1/history").json() == before
    assert len(client.get("/api/defects").json()) == count
