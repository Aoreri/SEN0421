"""PLN-35 deterministic population. Refuse nonempty or non-designated databases.

The benchmark owns the disposable database; it never drops existing tables.
Run from backend with DATABASE_URL and PLN35_DISPOSABLE=1 set.
"""
import json
import os
import platform
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    if os.environ.get("PLN35_DISPOSABLE") != "1":
        raise SystemExit("PLN35_DISPOSABLE=1 required; only use an empty disposable database")
    url = make_url(os.environ["DATABASE_URL"])
    if not Path(url.database or "").name.startswith("sds06_pln35_"):
        raise SystemExit("Database name must start with sds06_pln35_")
    check = create_engine(url)
    try:
        if inspect(check).get_table_names():
            raise SystemExit("Refusing nonempty database; create a fresh disposable instance")
    finally:
        check.dispose()
    from alembic import command
    from alembic.config import Config
    from app.db import SessionLocal, engine
    from app.models import (
        Defect,
        DefectHistory,
        Project,
        Release,
        Requirement,
        TestCase,
        TestExecution,
        TestPlan,
        TestRun,
        execution_defects,
    )
    try:
        command.upgrade(Config("alembic.ini"), "head")
        with SessionLocal() as db:
            project = db.scalar(select(Project).order_by(Project.id))
            release = db.scalar(select(Release).where(Release.project_id == project.id).order_by(Release.id))
            if release is None:
                release = Release(project_id=project.id, version="PLN-35 measured release")
                db.add(release)
                db.flush()
            empty_release = Release(project_id=project.id, version="PLN-35 empty control")
            db.add(empty_release)
            db.flush()
            requirement = db.scalar(select(Requirement).where(Requirement.project_id == project.id).order_by(Requirement.id))
            cases = [TestCase(id=f"P35-{i:03}", title=f"Performance case {i}", requirement=requirement.id,
                              requirements=[requirement], status="Passed", automated=True,
                              steps=["Execute deterministic benchmark action"], expected_result="Expected result") for i in range(100)]
            db.add_all(cases)
            at = datetime.now(UTC) - timedelta(days=100)
            test_runs = [TestRun(name=f"PLN-35 run {i:03}", project_id=project.id,
                                release_id=release.id, created_by="admin", created_at=at + timedelta(days=i)) for i in range(100)]
            db.add_all(test_runs)
            db.flush()
            statuses = ["Passed"] * 7 + ["Failed", "Blocked", "Skipped"]
            executions = [dict(run_id=run.id, test_case_id=case.id, status=statuses[j % 10],
                               actual_result="PLN-35 deterministic fixture", notes="Disposable measurement",
                               executed_by="admin", executed_at=run.created_at) for run in test_runs for j, case in enumerate(cases)]
            db.execute(TestExecution.__table__.insert(), executions)
            defects = [Defect(title=f"Performance incident {i:03}", severity=["Low", "Medium", "High", "Critical"][i % 4],
                              status=["Open", "In Progress", "Resolved", "Closed"][i % 4], test_case=cases[i].id) for i in range(100)]
            db.add_all(defects)
            db.flush()
            lifecycle = ["Open", "In Progress", "Resolved", "Closed"]
            for i, defect in enumerate(defects):
                previous = None
                for j, status in enumerate(lifecycle[:i % 4 + 1]):
                    db.add(DefectHistory(defect_id=defect.id, from_status=previous, to_status=status,
                                         at=at + timedelta(hours=j)))
                    previous = status
            execution_ids = db.scalars(select(TestExecution.id).where(TestExecution.run_id == test_runs[0].id).order_by(TestExecution.id)).all()
            db.execute(execution_defects.insert(), [dict(execution_id=ex, defect_id=d.id) for ex, d in zip(execution_ids, defects, strict=True)])
            plan = TestPlan(project_id=project.id, release_id=release.id, title="PLN-35 measured Test Plan",
                            version="pln35-benchmark", created_by="admin", scope="100 cases, 100 runs, 10,000 executions and 100 added incidents")
            db.add(plan)
            db.commit()
            count = db.scalar(select(func.count()).select_from(TestExecution))
            assert count == 10_000, count
            print(json.dumps({"executions": count, "runs_added": 100, "cases_added": 100,
                              "defects_added": 100,
                              "cases_total": db.scalar(select(func.count()).select_from(TestCase)),
                              "defects_total": db.scalar(select(func.count()).select_from(Defect)),
                              "requirements_total": db.scalar(select(func.count()).select_from(Requirement)),
                              "history_total": db.scalar(select(func.count()).select_from(DefectHistory)),
                              "project_id": project.id,
                              "release_id": release.id, "empty_release_id": empty_release.id, "plan_id": plan.id,
                              "python": platform.python_version(),
                              "database": engine.dialect.name, "database_version": list(engine.dialect.server_version_info or [])}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
