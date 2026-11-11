"""Shared fixtures; DATABASE_URL must only identify a disposable test database."""
import os
import tempfile
from pathlib import Path

# Set the URL before importing app.db so unit tests never select the dev DB by accident.
_TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="sds06-pytest-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DIRECTORY.name}/test.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]


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
