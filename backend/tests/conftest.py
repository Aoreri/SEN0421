"""Shared fixtures; DATABASE_URL must only identify a disposable test database."""
import os
import tempfile
from functools import cache
from pathlib import Path

# Set the URL before importing app.db so unit tests never select the dev DB by accident.
_TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="sds06-pytest-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DIRECTORY.name}/test.db")
# Tests run against the demo accounts and data (app/demo.py).
os.environ["DEMO_MODE"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]


@cache
def as_user(username: str) -> dict:
    """Giriş yapıp Authorization başlığı döner (bcrypt yavaş olduğundan önbelleklenir)."""
    with TestClient(app) as test_client:
        res = test_client.post("/api/auth/login", json={"username": username, "password": "demo1234"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fresh_seed():
    """Recreate the schema via real migrations, independently for each integration test."""
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def pytest_sessionfinish(session, exitstatus):
    engine.dispose()
    _TEST_DIRECTORY.cleanup()


def grant(client, project_id: int, *usernames: str) -> None:
    """PLN-40: Tester/Developer yalnızca üye oldukları projeleri görür; yeni projeye üye ekler."""
    admin = as_user("admin")
    users = {u["username"]: u["id"] for u in client.get("/api/users", headers=admin).json()}
    for name in usernames or ("tester", "developer"):
        res = client.put(f"/api/projects/{project_id}/members/{users[name]}", headers=admin)
        assert res.status_code == 200, res.text
