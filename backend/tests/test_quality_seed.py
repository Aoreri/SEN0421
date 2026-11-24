"""PLN-35: retained migration executions must not count as benchmark-created rows."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_benchmark_preserves_and_separately_counts_migration_executions(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    # This subprocess owns an empty database; the patched upgrade simulates a
    # future seed migration adding one real preexisting execution.
    program = '''
import runpy
from alembic import command
real_upgrade = command.upgrade
def upgrade(config, revision):
    real_upgrade(config, revision)
    from app.db import SessionLocal
    from app.models import Release, TestRun, TestExecution
    with SessionLocal() as db:
        release = Release(project_id=1, version="future seed release")
        db.add(release); db.flush()
        run = TestRun(project_id=1, release_id=release.id, name="retained seed run", created_by="tester")
        db.add(run); db.flush()
        db.add(TestExecution(run_id=run.id, test_case_id="TC-001", status="Failed"))
        db.commit()
command.upgrade = upgrade
runpy.run_path("scripts/seed_quality.py", run_name="__main__")
'''
    result = subprocess.run([sys.executable, "-c", program], cwd=backend,
                            env={**os.environ, "PLN35_DISPOSABLE": "1",
                                 "DATABASE_URL": f"sqlite:///{tmp_path / 'sds06_pln35_seed_test.db'}"},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout.splitlines()[-1])
    assert value["executions"] == 10_000
    assert value["panel_executions"] == 10_001
    assert value["panel_pass_rate"] == round(7000 / 8001 * 100, 1)
