"""PLN-38: demo hesapları ve verisi yalnızca DEMO_MODE=1 iken gelir; varsayılan kurulum boştur."""
from pathlib import Path

import pytest
from sqlalchemy import func, select

from alembic import command
from alembic.config import Config
from app.db import SessionLocal
from app.demo import bootstrap
from app.models import Defect, Project, TestCase, User

pytestmark = pytest.mark.integration
BACKEND = Path(__file__).resolve().parents[1]


def migrate_fresh() -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


def counts() -> tuple[int, ...]:
    with SessionLocal() as db:
        return tuple(db.scalar(select(func.count()).select_from(m)) or 0
                     for m in (User, Project, TestCase, Defect))


@pytest.fixture
def restore_demo():
    yield
    migrate_fresh()  # conftest sets DEMO_MODE=1, so later tests get the demo data back


def test_default_install_is_empty_and_admin_comes_from_environment(monkeypatch, restore_demo):
    monkeypatch.setenv("DEMO_MODE", "0")
    monkeypatch.delenv("ADMIN_USERNAME", raising=False)
    migrate_fresh()
    assert counts() == (0, 0, 0, 0)
    monkeypatch.setenv("ADMIN_USERNAME", "owner")
    monkeypatch.setenv("ADMIN_PASSWORD", "change-me-now")
    bootstrap()
    bootstrap()  # idempotent: users already exist
    with SessionLocal() as db:
        assert [(u.username, u.role) for u in db.scalars(select(User))] == [("owner", "Admin")]


def test_demo_install_has_demo_accounts_and_data(client, restore_demo):
    migrate_fresh()
    assert counts() == (4, 1, 6, 3)
    assert client.get("/api/health").json()["demo"] is True
    login = client.post("/api/auth/login", json={"username": "tester", "password": "demo1234"})
    assert login.status_code == 200
    token = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert [p["name"] for p in client.get("/api/projects", headers=token).json()] == ["SDS-06"]


def test_nightly_reset_restores_demo_data_and_refuses_outside_demo(monkeypatch, restore_demo):
    from app.demo import reset

    migrate_fresh()
    with SessionLocal() as db:
        db.add(Project(name="Visitor project"))
        db.commit()
    reset()
    assert counts() == (4, 1, 6, 3)
    monkeypatch.setenv("DEMO_MODE", "0")
    with pytest.raises(SystemExit):
        reset()
