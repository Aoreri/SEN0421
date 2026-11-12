# SDS-06 — Test Plan

**Legacy document name:** Test Plan (IEEE 829-style course deliverable)  
**Work package:** PLN-03  
**Version:** 0.1 — Draft for team review  
**Prepared:** 11 November 2026  
**Project:** Agile Test and Defect Tracking System  
**Repository:** [Aoreri/SEN0421](https://github.com/Aoreri/SEN0421)

> This document retains the familiar IEEE 829 `Test Plan` title for the course deliverable. The testing process and documentation approach are mapped by purpose to ISO/IEC/IEEE 29119-2:2021 and 29119-3:2021. This is not a claim of clause-level conformance or a one-to-one replacement of every IEEE 829 artefact.

## 1. Test plan identifier

`TP-SDS06-PLN03-v0.1`

## 2. Introduction

### 2.1 Purpose

This plan defines the test scope, approach, environment, responsibilities, entry/exit criteria, and initial test conditions for the current SDS-06 demo/template baseline. It supports verification of functional behavior, role checks, data integrity, traceability, and build quality.

### 2.2 Test objectives

- Verify that implemented functions behave according to the SRS and current API contract.
- Verify authentication and server-side authorization for the four user roles.
- Verify project/release/requirement operations and test-case traceability.
- Verify defect creation, allowed/denied status transitions, and history integrity.
- Verify the calculation of basic test metrics.
- Verify the frontend lint/type/build checks and backend quality/test checks through CI.
- Record planned features that cannot yet be tested because they are not implemented.

### 2.3 Test basis

- SDS-06 Bi-Weekly Progress Report #1 (30 October 2026).
- SDS-06 Midterm Questions and Evaluation Guide.
- `docs/srs.md` and `docs/standard-status-and-mapping.md`.
- Repository `README.md`, `AGENTS.md`, API routes, SQLAlchemy models, Alembic migrations, existing backend tests, and `.github/workflows/ci.yml` as checked 11 November 2026.

## 3. Test items

| Test item | Included content |
|---|---|
| Backend REST API | Health, authentication, test-case listing, defects, transition/history endpoints, metrics, projects, releases, requirements, and traceability. |
| Database | PostgreSQL schema/migrations, uniqueness and foreign-key constraints, transition-rule table, and append-only defect history. |
| Frontend | React + TypeScript source, ESLint, TypeScript type checking, and Vite production build. |
| Container environment | PostgreSQL 16, backend, and frontend services in Docker Compose; health dependencies and startup order. |
| CI workflow | Backend SQLite checks, PostgreSQL integration tests, frontend checks, and uploaded coverage artifacts. |
| Planned report/import functions | Test Plan/summary PDF or HTML generation and application-level JUnit/Cobertura import are recorded as future test items; they are not testable in the current baseline until implemented. |

## 4. Features to be tested

1. Health endpoint returns a healthy response.
2. Valid and invalid login; valid, invalid, forged, and expired token handling.
3. Server-side role restrictions on protected operations.
4. Project, release, and requirement create/read/update/delete behavior, including duplicate and dependency conflicts.
5. Requirement-to-test-case many-to-many traceability and invalid-link rejection.
6. Midterm FR-REQ-01 enforcement (every test case must have at least one requirement) and FR-REQ-02 release-specific traceability counts; these are explicit gaps in the current baseline and require implementation before their acceptance tests can pass.
7. Defect creation validation, state machine enforcement, role restrictions, and initial/transition history records.
7. PostgreSQL rejection of history UPDATE/DELETE.
8. Execution rate, pass rate, and open-defect metric values for known seed data and relevant boundary conditions.
9. Backend Ruff and mypy checks; backend pytest suite; frontend ESLint, TypeScript typecheck, and Vite build.
10. Docker Compose service readiness and documented local access paths.

## 5. Features not tested in the current implementation baseline

- PDF/HTML creation of IEEE 829-style Test Plan and Test Summary Report: planned, not yet implemented.
- JUnit result import and Cobertura ingestion/mapping to test-case IDs: planned, not yet implemented.
- Production deployment, production credentials, and real-user operational behavior: out of scope for this academic demo.
- Performance acceptance under the midterm workload is a target requiring a dedicated benchmark; it is not inferred from ordinary unit/integration test success. The midterm FR-REQ-01 minimum-link rule and FR-REQ-02 release-specific traceability report are not fully implemented in the current baseline and cannot yet pass their acceptance tests.

## 6. Test approach

### 6.1 Test levels and types

| Level/type | Approach | Main evidence |
|---|---|---|
| Unit | Test isolated validation and domain behavior without external production data. | `backend/tests/test_unit.py` and focused additions. |
| API/integration | Exercise FastAPI endpoints through the test client with a fresh migrated disposable database. | `backend/tests/test_api.py`, `test_integration.py`. |
| Database integration | Run migrations and verify PostgreSQL-specific trigger/constraint behavior against a disposable PostgreSQL 16 service. | `Backend PostgreSQL tests` CI job. |
| Frontend static verification | Run ESLint with zero warnings, TypeScript type checking, and production build. | Frontend CI job. |
| System/deployment smoke | Start Compose services and check health endpoints and expected service dependencies. | Compose health checks and documented `docker compose up --build -d --wait` procedure. |
| Security/authorization | Test accepted and rejected role/token combinations at the API boundary. | HTTP status and unchanged-data/history assertions. |
| Performance | Benchmark the traceability report using the midterm dataset target. | p95 measurement report; not yet provided by the current test suite. |

### 6.2 Test design principles

- Use stable test IDs and link them to requirements where the original requirement mapping has been confirmed.
- Include positive, negative, boundary, and authorization cases for each protected operation.
- Verify observable API behavior rather than internal wiring.
- Use only disposable databases for migration/integration tests. Never point tests at a database containing real or development data.
- Do not infer PostgreSQL trigger behavior from SQLite; execute the PostgreSQL-specific test job.
- Retain test output and CI run links as verification evidence.

### 6.3 Initial test case catalogue

The list below is the PLN-03 planning catalogue. Existing automated tests in the repository cover many of these behaviors; the table does not claim that every proposed test ID already exists under exactly this identifier.

| Test ID | Feature / condition | Expected result | Method / current evidence |
|---|---|---|---|
| TC-HEALTH-01 | Request `GET /api/health`. | HTTP 200 with `status=ok` and `template=true`. | API test. |
| TC-AUTH-01 | Login with a valid demo user and password. | HTTP 200; bearer token and user identity/role returned. | API integration test. |
| TC-AUTH-02 | Login with an incorrect password or unknown username. | HTTP 401; no access token returned. | API integration test. |
| TC-AUTH-03 | Call `/api/auth/me` with missing, malformed, forged, or expired token. | HTTP 401. | API integration test. |
| TC-AUTH-04 | Attempt a protected write with an authenticated but unauthorized role. | HTTP 403 and no unauthorized data change. | API integration test. |
| TC-CAT-01 | Create/read/update/delete a project with an authorized role. | Valid CRUD succeeds; duplicate project name returns conflict. | API integration test. |
| TC-CAT-02 | Create duplicate release version under the same project. | Second create is rejected with HTTP 409. | API integration test. |
| TC-REQ-01 | Create, read, update, and delete a requirement. | Valid operations succeed; duplicate or missing parent references are rejected. | API integration test. |
| TC-TRACE-01 | Link a requirement to multiple test cases and link a test case to multiple requirements. | Relationship is returned consistently from both directions. | API integration test. |
| TC-TRACE-02 | Submit an unknown test-case ID or an unknown requirement ID. | Invalid link is rejected; no partial relationship update is stored. | API integration test. |
| TC-TRACE-03 | Attempt to remove all requirement links from a test case (midterm FR-REQ-01). | The operation is rejected with HTTP 422 and the test case retains at least one requirement link. | Planned acceptance test; current API accepts an empty list, so this is a known implementation gap. |
| TC-TRACE-04 | Request a traceability report for a selected release (midterm FR-REQ-02). | Each requirement is returned with linked test-case count and Passed/Failed/Not Run counts. | Planned acceptance test; report endpoint is not implemented in the current baseline. |
| TC-DEF-01 | Create a defect with a valid title and optional test case. | HTTP 201; status is `Open`; initial history row exists. | API integration test. |
| TC-DEF-02 | Create a defect with a blank title or unknown test case. | HTTP 422; no defect is created. | API integration test. |
| TC-DEF-03 | Attempt an unsupported status transition. | HTTP 409; defect and history remain unchanged. | API integration test. |
| TC-DEF-04 | Attempt a valid transition with a role not allowed by the transition rule. | HTTP 403; defect and history remain unchanged. | API integration test. |
| TC-DEF-05 | Execute permitted transitions including Reopen. | Status follows the database-backed transition table; each transition adds an ordered history row. | API integration test. |
| TC-DEF-06 | Update or delete a history row directly on PostgreSQL. | Database trigger rejects the operation. | PostgreSQL integration test. |
| TC-MET-01 | Query metrics using the current six seeded test cases and three seeded defects. | `total_tests=6`, execution rate `66.7`, pass rate `75.0`, open defects `3`. | Existing integration assertion. |
| TC-BUILD-01 | Run backend Ruff, mypy, and pytest. | All commands exit successfully. | GitHub Actions backend job. |
| TC-BUILD-02 | Run frontend lint, typecheck, and production build. | All commands exit successfully. | GitHub Actions frontend job. |
| TC-PG-01 | Run all required integration tests against PostgreSQL 16. | Migrations and tests pass; PostgreSQL-specific history protection is verified. | GitHub Actions PostgreSQL job. |
| TC-PERF-01 | Generate a traceability report for 200 requirements and 1,000 test cases. | p95 response/generation time is at most 2 seconds. | Planned benchmark; no result claimed. |
| TC-PORT-01 | Start the application on a clean machine using the documented single Compose command. | Required services become healthy within 10 minutes. | Planned clean-machine demonstration; no result claimed. |

### 6.4 Regression scope

Any change to authentication, roles, data models, migrations, traceability, defect transition rules, history, metrics, or shared frontend API behavior requires regression of the corresponding test groups. Database changes require migration verification on PostgreSQL as well as the default disposable SQLite test setup.

## 7. Entry criteria

- The candidate branch is available and its pull request identifies the relevant plan item.
- The test basis and affected requirements are identified.
- Dependencies can be installed and the disposable test environment is available.
- Required migrations are present and the database can be reset/recreated safely.
- No real or irreplaceable data is connected to the test environment.

## 8. Exit criteria

- All applicable mandatory tests pass.
- Backend and frontend CI jobs pass for the candidate change.
- PostgreSQL-specific tests pass when database integrity or migration behavior is affected.
- No unresolved critical defect remains for the tested scope; any accepted lower-severity issue is recorded with rationale and owner.
- Deviations, blocked tests, and features not implemented are recorded in the Test Log / Test Incident Report.
- The reviewer confirms that the requirements and test evidence are traceable.

## 9. Suspension and resumption criteria

Suspend testing when the test environment is unavailable, a migration leaves the disposable database unusable, test data integrity is uncertain, or a blocking failure prevents meaningful execution. Resume after the environment is restored, the database is recreated from migrations, and the affected smoke test passes. Do not continue against an uncertain or non-disposable database.

## 10. Test environment

### 10.1 CI environment

- Ubuntu `ubuntu-latest`.
- Python 3.12 for backend checks.
- PostgreSQL 16 service for the PostgreSQL test job.
- Node.js 22 for frontend checks.
- SQLite temporary test database for the default backend test job.
- Dependency installation from `backend/requirements-dev.txt` and `frontend/package-lock.json`.

### 10.2 Local environment

The documented local stack uses Docker Compose v2, PostgreSQL 16, the FastAPI backend, and the frontend container. The Compose health checks gate backend/frontend startup on service readiness. The application can also be developed locally with PostgreSQL in Docker and separate backend/frontend development processes.

### 10.3 Test data

Use the migration-provided demo records and test fixtures. Reset only disposable test databases. The seed currently includes six test cases and three defects; seeded requirement rows R1–R8 contain placeholder titles and must not be treated as complete approved requirement text.

## 11. Responsibilities

| Responsibility | Assigned person / role from project report |
|---|---|
| Test Plan preparation and requirements/documentation coordination (PLN-03) | Emirhan Ulutürk |
| QA / DevOps and CI/test result approach | Esra Kaya |
| Backend implementation and API/database fixes | Caner Serbest |
| Frontend implementation and UI verification | Emirhan Canarslan |
| Independent review | Peer review by an available team member; no separate external verification team is defined. |

## 12. Schedule and deliverables

PLN-03 target date in Bi-Weekly Progress Report #1 is **13 November 2026**. Testing runs for each affected pull request and again on the integrated baseline. Test deliverables include this Test Plan, test case specifications/catalogue, repeatable test procedures, test logs/evidence, incident records for failures, and a Test Summary Report at the agreed completion checkpoint.

## 13. Risks and contingencies

- RSK-01: Reduce scope through vertical slices and documented prioritization.
- RSK-05: Verify metric formulas and query results using known seed data; use performance evidence before accepting metric scalability.
- RSK-06: Keep stable test-case identifiers for future automated result import and report unmatched results explicitly.
- RSK-07: Keep PDF generation in a container when implemented and preserve HTML as the stated fallback.
- RSK-08: Keep template/demo warnings and use PostgreSQL persistence; do not claim production readiness.

The full register is `docs/risk-register.md`.

## 14. Test reporting

- Automated results are available from GitHub Actions workflow runs.
- Backend coverage is exported as Cobertura XML and uploaded as CI artifacts when generated.
- Failures affecting requirements are recorded as test incidents/defects with reproducible steps and evidence.
- A Test Summary Report should summarize scope, execution, pass/fail/blocked results, coverage, open defects, limitations, and the release/demo recommendation. Generation of that report inside the application remains planned.

## 15. Standards references

1. IEEE 829-2008 — legacy course-facing Test Plan document structure; status is superseded.
2. ISO/IEC/IEEE 29119-2:2021 — test process reference.
3. ISO/IEC/IEEE 29119-3:2021 — test documentation reference.
4. ISO/IEC/IEEE 29119-4:2021 — test design technique reference.
5. ISO/IEC/IEEE 12207:2026 — software life-cycle process context, subject to instructor confirmation of the course baseline edition.
6. `docs/standard-status-and-mapping.md` — project-level standard status and mapping note.
