# SDS-06 — Installation and User Guide

**Plan item:** PLN-37  
**Version:** 1.0 — Draft for demonstration  
**Prepared:** 22 November 2026  
**Repository:** [Aoreri/SEN0421](https://github.com/Aoreri/SEN0421)

## 1. Purpose

This guide explains how to start the SDS-06 local demonstration environment and use the integrated project, test, defect, metrics, import, and Test Plan functions. It assumes a development/demo machine and non-production sample data.

## 2. Prerequisites

| Requirement | Expected setup |
|---|---|
| Operating system | Windows 10/11, macOS, or Linux supported by Docker Desktop/Engine. |
| Container runtime | Docker Desktop or Docker Engine with Docker Compose v2. |
| Git client | Git for Windows/macOS/Linux if cloning the repository. |
| Network | Access to download the PostgreSQL, Python, and frontend build images/dependencies. |
| Ports | Local ports 5432, 8000, and 5173 available (or update Compose port mappings). |

The documented Compose setup runs PostgreSQL 16, the FastAPI backend, and the frontend container. A Python or Node installation on the host is not required for the container demonstration.

## 3. Get the source

Clone the repository and enter its directory:

```powershell
git clone https://github.com/Aoreri/SEN0421.git
cd SEN0421
```

On macOS/Linux, the equivalent commands are:

```bash
git clone https://github.com/Aoreri/SEN0421.git
cd SEN0421
```

Use the integrated `main` branch for the baseline demonstration. Open PR branches may contain work that has not yet been integrated.

## 4. Start the application with Docker Compose

From the repository root run:

```bash
docker compose up --build -d --wait
```

The command builds the backend/frontend images, starts PostgreSQL 16, waits for the database health check, starts the backend, applies Alembic migrations, then waits for the frontend health check.

When startup completes, open:

| Service | Address |
|---|---|
| Web UI | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger / OpenAPI | http://localhost:8000/docs |
| Health endpoint | http://localhost:8000/api/health |

A healthy API response is `{"status":"ok"}`. The Compose frontend proxy forwards `/api` requests to the backend.

### 4.1 Stop the application

Stop containers while preserving the named database volume:

```bash
docker compose down
```

To remove the local demo database volume as well:

```bash
docker compose down -v
```

`down -v` permanently removes the local Compose database volume. Use it only when the demonstration data is disposable and a reset is intended.

## 5. Sign in and roles

With `DEMO_MODE=1` the system loads sample users and data for demonstration; their shared sample password is `demo1234`. By default the database starts empty and the first Admin comes from `ADMIN_USERNAME`/`ADMIN_PASSWORD`.

| Username | Role | Typical demonstration responsibility |
|---|---|---|
| `admin` | Admin | Administration and privileged operations. |
| `testlead` | Test Lead | Manage project/release/requirement catalogues, test suites/cases, Test Plans, and release criteria. |
| `tester` | Tester | Maintain test cases/traceability, execute tests, create defects, and perform permitted verification actions. |
| `developer` | Developer | Perform developer-authorized defect transitions. |

These are public demo credentials, not secure user accounts. Never reuse the credentials or default local database password in a production or internet-exposed environment.

The application uses a bearer token for protected operations. The backend is authoritative for role permissions. A control hidden or disabled in the frontend is not a substitute for backend authorization.

## 6. Main user workflows

### 6.1 Create a project and organize requirements

1. Open **Projeler & Gereksinimler** (`/projects`).
2. Sign in as `admin` or `testlead`.
3. Create a project and, where needed, a release.
4. Add requirements using stable identifiers such as the approved project requirement IDs.
5. Keep the project association correct; the API rejects references that belong to a different project.

### 6.2 Create test suites and test cases

1. Open **Test Vakaları & Matris** (`/test-cases`).
2. Create a suite for a project if the tests should be grouped.
3. Create a test case using a stable ID, a clear title, priority, automation flag, ordered steps, expected result, and at least one requirement link.
4. Link requirements to test cases through the traceability matrix.
5. Check both directions: a requirement should display its linked test cases and a test case should display its linked requirements.

The API rejects test cases without requirement links, duplicate suite names within the same project, unknown references, and invalid cross-project suite/requirement combinations.

### 6.3 Create and execute a test run

1. Open **Test Koşumları** (`/test-runs`).
2. Create a run for a project and optionally associate a release/suite and selected cases.
3. The run creates one execution row per selected case, initially `Not Run`.
4. Record `Passed`, `Failed`, `Blocked`, or `Skipped`, plus actual result and notes where appropriate.
5. Use run history to inspect the recorded executions.

### 6.4 Create and close a defect

1. From a failed execution, use the defect action or open the defect workflow.
2. Enter a non-empty title, severity, and related test case when available.
3. A new defect starts in `Open` and receives an initial history entry.
4. The normal lifecycle is `Open → In Progress → Resolved → Closed`. Permitted Reopen transitions return a defect to `Open`.
5. For a case-linked defect, `Resolved → Closed` requires the latest relevant verification execution to be `Passed`.
6. Inspect the ordered history on the defect detail page (`/defects/:id`).

The backend returns HTTP 409 for an invalid state transition and HTTP 403 when a transition exists but the caller's role is not allowed to perform it.

### 6.5 Review dashboard metrics and release gates

1. Open **Panel & Metrikler** (`/`).
2. Review the visible test counts, execution/pass rates, trends, defect summaries, and release gate status.
3. For a release, review its configured pass-rate, open-Critical-defect, and requirement-coverage criteria.
4. A release cannot move to `Ready` or `Released` if configured criteria fail unless an authorized waiver is recorded.
5. A waiver records its reason and identity/time metadata; it does not change the underlying metric values.

Expanded metrics can also be queried through `GET /api/metrics/expanded` with supported project/release/date filters. See the OpenAPI page for current query parameters.

### 6.6 Import JUnit and Cobertura evidence

- JUnit: upload XML to `POST /api/projects/{project_id}/runs/import` using `Content-Type: application/xml`; optional `commit` and `branch` query parameters preserve source metadata. The API reports matched and unmatched results.
- JUnit imports are snapshots distinct from interactive Test Runs; they do not silently change existing test-case statuses.
- Cobertura: use `POST /api/projects/{project_id}/coverage/import` with the supported XML payload. The API stores coverage evidence and can associate it with the related import metadata.

Use the relevant API contract files and `/docs` for payload shape and response details.

### 6.7 Manage a Test Plan (API baseline)

The Test Plan API is integrated in `main`. The dedicated frontend Test Plan management screen is tracked separately in PR #41 and should not be assumed to be present until that PR is merged.

Principal routes:

| Operation | Route |
|---|---|
| List/create plans | `GET/POST /api/test-plans` |
| Read/update/delete a plan | `GET/PUT/DELETE /api/test-plans/{id}` |
| Change status | `PUT /api/test-plans/{id}/status` |
| Create/list snapshots | `POST/GET /api/test-plans/{id}/snapshots` |
| Read a snapshot | `GET /api/test-plans/{id}/snapshots/{snapshot_id}` |
| Export HTML/PDF | `GET /api/test-plans/{id}/export?format=html|pdf` (optional `snapshot_id`) |

The workflow is `Draft → In Review → Approved`; direct `Draft → Approved` is rejected. Approved plans cannot be edited or deleted without taking the supported revision path.

## 7. API and error reference

| HTTP status | Meaning in the application |
|---|---|
| 200 | Request completed successfully. |
| 201 | Resource/snapshot created successfully. |
| 204 | Resource deleted successfully; no response body. |
| 401 | Authentication is missing, invalid, or expired for a protected route. |
| 403 | Authenticated user does not have the required role. |
| 404 | Requested resource does not exist. |
| 409 | Domain conflict or invalid lifecycle transition. |
| 422 | Request body, reference, or validation rule is invalid. |

Use the response `detail` field for the validation/error explanation. Do not bypass backend validation by writing directly to the database.

## 8. Local development and verification

For backend development with a local PostgreSQL service:

```bash
docker compose up -d db
cd backend
python -m venv .venv
# Activate the virtual environment, then:
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

For frontend development in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Before submitting code changes, run the repository checks:

```bash
cd backend && ruff check . && mypy app && python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm run build
```

The default backend tests use a disposable SQLite database. PostgreSQL-specific migration/trigger behavior must be verified against a disposable PostgreSQL 16 database; never point test reset/migration commands at irreplaceable data.

## 9. Troubleshooting

| Symptom | Recommended check |
|---|---|
| Frontend does not load | Check `docker compose ps`, frontend logs, and port 5173 availability. |
| API is unavailable | Check backend health at `/api/health`, backend logs, and port 8000. |
| Database connection failure | Confirm the `db` service is healthy and port 5432 is not occupied. |
| Migration error | Do not manually edit a merged migration. Inspect Alembic history and resolve branch migration ordering on a disposable database. |
| 401 response | Sign in again and verify that the request carries a valid bearer token. |
| 403 response | Use an account whose role is permitted for the requested action. |
| 409 response | Review duplicate/version/dependency constraints or the allowed workflow transition. |
| PDF differs from HTML | Verify WeasyPrint dependencies in the supported container; a PDF response signature alone does not prove visual fidelity. |

## 10. Known limitations at the 22 November 2026 baseline

- The dedicated Test Plan management UI is in PR #41 (PLN-31).
- Test Incident Report / Test Log generation is in PR #37 (PLN-39), and Test Summary Report generation is in PR #38 (PLN-30); both are open PRs, not integrated baseline functionality.
- Read-endpoint authentication/security hardening is in PR #39 (PLN-29).
- Sprint entity/metrics filter is in PR #34 (PLN-28).
- Release automation is in PR #40 (PLN-36); no v1.0.0 release is claimed here.
- Clean-machine installation time, the 200-requirement/1,000-case p95 target, and full target-container PDF rendering still require recorded evidence.
- R1–R8 original wording requires confirmation from the approved course/project source.

## 11. Related documents

- [SRS](srs.md)
- [SDD](software-design-description.md)
- [RTM v2](requirements-traceability-matrix-v2.md)
- [Test Plan](https://github.com/Aoreri/SEN0421/blob/main/docs/test-plan.md)
- [Metric definitions](https://github.com/Aoreri/SEN0421/blob/main/docs/metric-definitions.md)
- [Standards status and mapping](https://github.com/Aoreri/SEN0421/blob/main/docs/standard-status-and-mapping.md)
- [Workflow Test Case Specification](https://github.com/Aoreri/SEN0421/blob/main/docs/test-case-specification-workflow.md)
