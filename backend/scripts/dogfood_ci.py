"""PLN-23: import this CI job's actual reports into an isolated SDS-06 instance.

No deployment credentials or real project database are used. Persist the API report
responses as a CI artifact, including unmatched JUnit results instead of guessing IDs.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--output", type=Path, default=Path("dogfood-report.json"))
    args = parser.parse_args()
    junit, coverage = args.junit.read_bytes(), args.coverage.read_bytes()
    backend = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend))
    with tempfile.TemporaryDirectory(prefix="sds06-ci-import-") as directory:
        # Override inherited CI test URLs; migrations must never target a deployment.
        os.environ["DATABASE_URL"] = f"sqlite:///{directory}/dogfood.db"
        from fastapi.testclient import TestClient

        from alembic import command
        from alembic.config import Config
        from app.db import engine
        from app.main import app

        config = Config(str(backend / "alembic.ini"))
        config.set_main_option("script_location", str(backend / "alembic"))
        try:
            command.upgrade(config, "head")
            with TestClient(app) as client:
                login = client.post("/api/auth/login", json={"username": "tester", "password": "demo1234"})
                login.raise_for_status()
                headers = {"Authorization": f"Bearer {login.json()['access_token']}",
                           "Content-Type": "application/xml"}
                projects = client.get("/api/projects", headers=headers)
                projects.raise_for_status()
                project_id = projects.json()[0]["id"]
                params = {"commit": args.commit, "branch": args.branch}
                run = client.post(f"/api/projects/{project_id}/runs/import", content=junit,
                                  headers=headers, params=params)
                if run.is_error:
                    raise RuntimeError(f"JUnit import failed: {run.status_code}: {run.text}")
                result = run.json()
                report = client.post(f"/api/projects/{project_id}/coverage/import", content=coverage,
                                     headers=headers, params={"junit_import_id": result["id"]})
                if report.is_error:
                    raise RuntimeError(f"Coverage import failed: {report.status_code}: {report.text}")
                # Read through fresh API requests to verify persisted evidence.
                stored_run = client.get(f"/api/projects/{project_id}/runs/imports/{result['id']}", headers=headers)
                stored_coverage = client.get(
                    f"/api/projects/{project_id}/coverage/imports/{report.json()['id']}", headers=headers)
                stored_run.raise_for_status()
                stored_coverage.raise_for_status()
                run_data = stored_run.json()
                if run_data["summary"]["matched"] < 1:
                    raise RuntimeError("Expected at least one matched JUnit testcase (TC-005)")
                evidence = {"environment": "isolated-ci-instance", "commit": args.commit,
                            "branch": args.branch, "junit": run_data,
                            "coverage": stored_coverage.json()}
                args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
                print(f"Imported {result['summary']['total']} JUnit results "
                      f"({result['summary']['unmatched']} unmatched) and "
                      f"{report.json()['summary']['lines_valid']} coverage lines")
        finally:
            engine.dispose()


if __name__ == "__main__":
    main()
