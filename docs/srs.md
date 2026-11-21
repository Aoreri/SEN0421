# SDS-06 — Software Requirements Specification (SRS)

**Project:** Agile Test and Defect Tracking System  
**Project ID:** SDS-06  
**Work package:** PLN-02  
**Version:** 0.2 — Draft for team review  
**Prepared:** 18 November 2026  
**Repository:** [Aoreri/SEN0421](https://github.com/Aoreri/SEN0421)

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification defines the intended behavior, external interfaces, quality targets, and constraints of SDS-06. It is a project-level working baseline for implementation, verification, and change review. It reflects the first bi-weekly progress report, the project midterm answers, and the implementation currently present in the repository as of 11 November 2026.

### 1.2 Product scope

SDS-06 is a web-based Agile Test and Defect Tracking System. It brings project/release/requirement information, test-case traceability, defect management, role-based access, and basic test metrics into one system. The project is an academic demo/template, not a production service. JUnit XML import, project-scoped stable-key mapping, and unmatched-result reports are implemented in PLN-22; see [the import contract](junit-import.md). PDF/HTML test-document generation and Cobertura import remain planned.

### 1.3 Intended audience

- Product owner and requirements/documentation contributor.
- Backend and frontend developers.
- QA / DevOps contributor.
- Test Lead, Tester, Developer, and Admin users.
- Course instructor and project evaluators.

### 1.4 Definitions

| Term | Meaning |
|---|---|
| Defect | A recorded problem associated with the product or a test case. |
| Test case | An identifiable verification scenario with a result status. |
| Requirement traceability | A relationship connecting a requirement to one or more test cases. |
| Test incident | An event or result requiring investigation; the project defect workflow records its resolution. |
| SRS | Software Requirements Specification. |
| SDD | Software Design Description. |
| RBAC | Role-based access control. |
| CI | Continuous Integration. |

## 2. Overall description

### 2.1 Product perspective

The product is organized as a browser-based React + TypeScript frontend, a FastAPI REST backend, and a PostgreSQL database. SQLAlchemy provides persistence access and Alembic manages schema changes. Docker Compose defines the local PostgreSQL, backend, and frontend services. GitHub Actions runs backend and frontend quality checks and PostgreSQL-backed integration tests.

### 2.2 User classes and roles

| Role | Intended responsibility | Implemented authorization pattern |
|---|---|---|
| Admin | Administrative access and oversight | Can perform protected catalog and defect operations. |
| Test Lead | Test coordination and review | Can perform project/release/requirement writes and verification transitions. |
| Tester | Execute tests, create defects, maintain traceability, verify defects | Can create defects and update requirement-to-test-case links; can close/reopen allowed defects. |
| Developer | Investigate and fix defects | Can perform the implementation-side defect transitions; cannot perform protected catalog writes. |

The exact permission for each operation is enforced by backend dependencies and database-backed defect transition rules. The API, not the frontend, is authoritative for authorization.

### 2.3 Operating environment

- Backend: Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL driver.
- Database: PostgreSQL 16 for the local Compose environment and PostgreSQL CI job.
- Frontend: React 18, TypeScript, Vite, Node.js 22 in CI.
- Local container orchestration: Docker Compose v2.
- CI: GitHub Actions on `ubuntu-latest`.
- Browser access: local frontend at `http://localhost:5173`; API documentation at `http://localhost:8000/docs` when running the documented Compose environment.

### 2.4 Design and implementation constraints

1. The repository is maintained through task-specific branches and pull requests; changes are not pushed directly to `main`.
2. Database schema changes require a new Alembic migration. Already-merged migrations are not edited.
3. Every test case must retain its requirement association; current seed data preserves the legacy `requirement` value and also populates the many-to-many traceability table.
4. Defect history is append-only. PostgreSQL prevents UPDATE and DELETE operations on the history table through a trigger.
5. Demo accounts and local database credentials documented in the repository are public development values and must not be reused in production.
6. The project is tailored to an academic team and does not include a real customer, live operational service, or independent external verification organization.

### 2.5 Assumptions and dependencies

- Users have a supported browser and network access to the application.
- PostgreSQL is available through Docker Compose for local end-to-end use.
- CI services can install the pinned backend and frontend dependencies.
- The instructor confirms whether the course baseline should explicitly name ISO/IEC/IEEE 12207:2026 or retain an earlier edition for course consistency.
- The original detailed R1–R8 requirement descriptions are supplied/confirmed by the team before final baseline approval. The current repository migration creates R1–R8 as placeholder rows; it does not contain their complete normative descriptions.

## 3. System functions

### 3.1 Functional requirements

The IDs below preserve the midterm identifiers where they were explicitly defined (FR-REQ-01/02); other SRS IDs are descriptive identifiers created for this draft. They do not replace or redefine the team's original R1–R8 identifiers.

| SRS ID | Requirement statement | Priority | Baseline status |
|---|---|---|---|
| FR-AUTH-01 | The system shall accept a username and password and, when the credentials are valid, return a bearer access token and the authenticated user's identity and role. | High | Implemented (`POST /api/auth/login`). |
| FR-AUTH-02 | The system shall validate a bearer token before returning the current authenticated user's identity. | High | Implemented (`GET /api/auth/me`). |
| FR-AUTH-03 | The system shall enforce the Admin, Test Lead, Tester, and Developer permissions on protected operations at the backend. | High | Implemented for the current API operations. |
| FR-CAT-01 | The system shall allow authorized users to create, read, update, and delete projects, subject to dependency and uniqueness constraints. | High | Implemented. |
| FR-CAT-02 | The system shall allow authorized users to create, read, update, and delete project releases; a project shall not contain duplicate version identifiers. | Medium | Implemented. |
| FR-CAT-03 | The system shall allow authorized users to create, read, update, and delete requirements associated with a project. | High | Implemented. |
| FR-TRACE-01 | The system shall maintain requirement-to-test-case associations and return the related test-case IDs when a requirement is read. The association shall support multiple test cases per requirement and multiple requirements per test case. | High | Implemented through `test_case_requirements`. |
| FR-TRACE-02 | The system shall reject a traceability update that references a nonexistent test case or requirement. | High | Implemented with HTTP 422/404 responses. |
| FR-REQ-01 | The system shall require every test case to be associated with at least one requirement; a test case without a requirement association shall be rejected with HTTP 422. | High | Midterm requirement; not fully enforced by the current many-to-many API because an empty association list is currently accepted. Gap to close. |
| FR-REQ-02 | For a selected release, the system shall produce a traceability report showing each requirement's linked test-case count and the Passed, Failed, and Not Run result counts. | High | Midterm requirement; a release-specific per-requirement traceability report is not implemented in the current baseline. |
| FR-DEF-01 | The system shall allow an authorized Admin, Test Lead, or Tester to create a defect with a non-empty title, severity, and optional related test case. A new defect shall start in `Open` and create an initial history entry. | High | Implemented. |
| FR-DEF-02 | The system shall permit only transitions stored in the defect transition rules and only for a role listed as authorized for that transition. | High | Implemented; invalid transition returns 409 and an unauthorized role returns 403. |
| FR-DEF-03 | The system shall expose the ordered history of a defect, including the previous status, new status, and timestamp for each recorded event. | High | Implemented. |
| FR-MET-01 | The system shall report total test cases, execution rate, pass rate among executed cases, and the count of defects not in `Closed` status. | Medium | Implemented (`GET /api/metrics`). |
| FR-DOC-01 | The system should provide a Test Plan and Test Summary Report generation capability in a documented output format (PDF or HTML). | Medium | Planned; not implemented in the current baseline. |
| FR-IMP-01 | The system should support importing JUnit test results and Cobertura coverage results and associating imported results with stable test-case identifiers. Unmatched results should be reported rather than silently discarded. | Medium | JUnit XML import, stable-key mapping, and unmatched-result reporting implemented (PLN-22); Cobertura ingestion remains planned. |

### 3.2 Original R1–R8 baseline traceability note

The repository's initial migration inserts requirement records `R1` through `R8` with placeholder titles (`Gereksinim R1` … `Gereksinim R8`) and empty descriptions. The seed test cases associate `TC-001` and `TC-002` with R1, `TC-003` with R3, `TC-004` with R4, `TC-005` with R6, and `TC-006` with R7. Those test-case names provide limited evidence of the intended areas (login, defect creation, defect transitions, test summary generation, and JUnit import), but do not provide the complete original requirement wording. R2, R5, and R8 are not described in the inspected source material.

Therefore, the team must cross-check the original R1–R8 definition set before claiming that the draft FR identifiers above are an approved one-to-one mapping. This SRS intentionally does not invent missing R2/R5/R8 descriptions.

### 3.3 Interface requirements

| Interface | Description |
|---|---|
| User interface | React + TypeScript single-page frontend served from the frontend container. |
| Application interface | JSON REST endpoints provided by FastAPI under `/api`. |
| Authentication interface | `POST /api/auth/login` returns a bearer token; protected endpoints accept `Authorization: Bearer <token>`. |
| Database interface | SQLAlchemy sessions access PostgreSQL; Alembic migrations define schema evolution. |
| CI interface | GitHub Actions checks repository changes and reports workflow status in the repository. JUnit XML import is available through the authenticated API (PLN-22); Cobertura ingestion remains planned. |

### 3.4 External API surface in the current baseline

| Area | Current endpoints |
|---|---|
| Health | `GET /api/health` |
| Authentication | `POST /api/auth/login`, `GET /api/auth/me` |
| Test cases / defects | `GET /api/test-cases`, `GET/POST /api/defects`, `POST /api/defects/{id}/transition`, `GET /api/defects/{id}/history` |
| Metrics | `GET /api/metrics` |
| JUnit imports | `POST /api/projects/{project_id}/runs/import`, `GET /api/projects/{project_id}/runs/imports`, `GET /api/projects/{project_id}/runs/imports/{import_id}`; raw XML upload, JSON reports. |
| Projects | `GET/POST /api/projects`, `GET/PUT/DELETE /api/projects/{project_id}` |
| Releases | `GET/POST /api/releases`, `GET/PUT/DELETE /api/releases/{release_id}` |
| Requirements | `GET/POST /api/requirements`, `GET/PUT/DELETE /api/requirements/{requirement_id}`, `PUT /api/requirements/{requirement_id}/test-cases` |

## 4. Non-functional requirements

| SRS ID | Quality attribute | Requirement / acceptance target | Status |
|---|---|---|---|
| NFR-REQ-01 | Performance efficiency | For a test dataset containing 200 requirements and 1,000 test cases, the requirement traceability report shall be generated within 2 seconds at the 95th percentile in the local Docker Compose environment. | Target from the project midterm; report feature and performance benchmark still required. |
| NFR-REQ-02 | Portability / installability | On a clean machine with the stated prerequisites, the backend, frontend, and PostgreSQL environment shall start with one `docker compose up` command within 10 minutes. | Target from the project midterm; clean-machine timing evidence still required. |
| NFR-SEC-01 | Security | Passwords shall be stored as bcrypt hashes, API access tokens shall be signed and time-limited, and protected operations shall enforce role checks on the server. | Implemented in current backend; demo credentials and default local settings are not production-safe. |
| NFR-REL-01 | Reliability / data integrity | Every accepted defect creation and status transition shall create a history record. PostgreSQL shall reject UPDATE and DELETE operations on `defect_history`. | Implemented and included in PostgreSQL tests. |
| NFR-MAINT-01 | Maintainability | Backend, frontend, persistence models, and migrations shall remain separated. Pull requests shall run lint, type checks, backend tests, PostgreSQL tests, and frontend build checks. | Current CI pipeline implements these checks. |
| NFR-TRACE-01 | Traceability | Every test case shall preserve its requirement association; invalid link references shall be rejected rather than stored as dangling references. | Implemented for the current traceability API. |

The functional traceability requirements FR-REQ-01/02 and the performance/portability targets NFR-REQ-01/02 are explicitly described in the midterm response. FR-REQ-01 is not fully enforced by the current API, FR-REQ-02 is not implemented, and the two quality targets have not been demonstrated by measurements. They are requirements, not completed-feature claims.

## 5. Data requirements

The current relational model includes users, projects, releases, requirements, test cases, the test-case/requirement association table, defects, defect transition rules, defect history, and PLN-22 imported test runs/results. The exact attributes, primary keys, foreign keys, and the legacy `TestCase.requirement` field are described in `docs/software-design-description.md`.

## 6. Verification and acceptance

- Functional requirements are verified through API and integration tests against disposable databases.
- PostgreSQL-specific history immutability is verified against a disposable PostgreSQL 16 database, not inferred from SQLite behavior.
- Frontend maintainability checks are verified using ESLint, TypeScript type checking, and the Vite production build.
- Performance and clean-machine portability targets require separate measurement evidence.
- Report generation and Cobertura ingestion remain open. The JUnit portion of FR-IMP-01 is implemented and tested in PLN-22; import snapshots do not update existing test-case states or interactive executions. PLN-33 creates deduplicated Open defects for matched failed JUnit results, with one immutable creation-history entry; these incidents contribute to normal defect metrics.

## 7. References

1. SDS-06 Bi-Weekly Progress Report #1, 30 October 2026 (work-package assignments, risks, initial plan, and next sprint items).
2. SDS-06 Midterm Questions and Evaluation Guide (role definitions, requirement traceability examples, performance and portability targets, and design viewpoints).
3. `README.md`, `AGENTS.md`, `backend/app/`, `backend/alembic/versions/`, `backend/tests/`, `docker-compose.yml`, and `.github/workflows/ci.yml` in the project repository (implementation baseline checked 11 November 2026).
4. `docs/standard-status-and-mapping.md` (PLN-01 standards status and project-level mapping).

## 8. Version 0.2 update — PLN-25 (18 November 2026)

This section extends the PLN-02 SRS draft to cover the plan items scheduled for 16 and 19 November. The original sections remain in place. Behavior merged to `main` is marked **Current on `main`**, while work still under an open pull request or pending implementation is labelled **PR in review** or **Planned**.

### 8.1 Additional functional requirements

| SRS ID | Requirement | Priority | Status on `main` |
|---|---|---|---|
| FR-TC-01 | The system shall provide project-scoped Test Suite create, read, update, and delete operations. A suite name shall be unique within its project; a suite with attached test cases shall not be deleted. | High | Current on `main` (PLN-16, PR #21; UI in PLN-19, PR #22). |
| FR-TC-02 | The system shall provide Test Case create, read, update, and delete operations with a stable case ID, title, ordered steps, expected result, priority, automation flag, optional suite, status, and one or more requirement links. | High | Current on `main` (PLN-16, PR #21; UI in PLN-19, PR #22). |
| FR-TC-03 | The system shall reject a test case create/update or requirement-link replacement (`POST/PUT /api/test-cases`, `PUT /api/test-cases/{id}/requirements`) with an empty requirement list and reject links to nonexistent requirements or test cases with HTTP 422 (`PUT /api/requirements/{id}/test-cases` intentionally accepts an empty list to clear a requirement's links). | High | Current on `main` (required by midterm FR-REQ-01; enforced by PLN-16, PR #21 in `backend/app/projects.py:90,107,445,567`). |
| FR-RUN-01 | The system shall create and list project/release-scoped Test Runs. When a run is created, the system shall create one `Not Run` execution record for each selected test case. | High | Current on `main` (PLN-17, PR #25; UI in PLN-20, PR #23). |
| FR-RUN-02 | The system shall record an execution result as `Passed`, `Failed`, `Blocked`, or `Skipped`, together with actual result, notes, executor, execution time, and optional linked defect IDs. | High | Current on `main` (PLN-17, PR #25; UI in PLN-20, PR #23). |
| FR-RUN-03 | The system shall allow a defect in `Resolved` state to move to `Closed` only when the latest relevant verification execution for its linked test case is `Passed`; otherwise the API shall reject the transition with HTTP 409. | High | Current on `main` (PLN-17, PR #25). |
| FR-REL-01 | The system shall manage release states `Planned`, `In Test`, `Ready`, and `Released`. | High | Current on `main` (PLN-18, PR #27). |
| FR-REL-02 | The system shall evaluate configurable release exit criteria: minimum pass rate, maximum open Critical defects, and minimum requirement coverage. A transition to `Ready` or `Released` shall be rejected with HTTP 409 when `gate_passed` is false (i.e., the criteria fail and no active waiver exists). | High | Current on `main` (PLN-18, PR #27). |
| FR-REL-03 | An Admin or Test Lead shall be able to record a release-gate waiver with a non-empty reason and later remove it. The waiver metadata shall identify the user and timestamp; an active waiver sets `gate_passed = true` to permit status transitions while `passed_criteria` and `actual_*` measured values remain unchanged and visible. | Medium | Current on `main` (PLN-18, PR #27). |
| FR-PLAN-01 | The system shall provide versioned Test Plan records with `Draft`, `In Review`, and `Approved` states. A project shall not contain duplicate Test Plan version values. | High | Current on `main` (PLN-26, PR #26, assigned to Caner Serbest; PR #26 also carries work shared with the Test Plan owner). |
| FR-PLAN-02 | The system shall enforce valid Test Plan status transitions and prevent editing or deleting an Approved plan except through the explicitly supported revision path (`Approved → Draft`). | High | Current on `main` (PLN-26, PR #26). |
| FR-PLAN-03 | The system shall create point-in-time Test Plan snapshots containing the rendered HTML and structured payload, and shall support HTML and PDF export of a live plan or stored snapshot. | Medium | Current on `main` (PLN-26, PR #26). |
| FR-MET-02 | The system shall define and report test-run outcome counts, execution completion rate, run pass rate, requirement coverage, open Critical defects, and release-gate result using the formulas in `docs/metric-definitions.md`. | High | Release-gate metrics current on `main` (PLN-18, PR #27); definitions delivered by PLN-25; dashboard UI in PR #24 (PLN-21); expanded SQL aggregation API remains planned under PLN-24. |

### 8.2 Metrics as measurable requirements

The metric names, formulas, denominators, zero-denominator behavior, scope, and example checks are defined in [`metric-definitions.md`](metric-definitions.md). The current `/api/metrics` values remain distinct from the run-level values:

- Current `execution_rate` counts only `Passed` and `Failed` cases as executed.
- Current `pass_rate` is `Passed / (Passed + Failed)`.
- The Test Run completion rate counts `Passed`, `Failed`, `Blocked`, and `Skipped` as completed attempts; `Not Run` remains in the denominator.
- Run pass rate continues to use `Passed / (Passed + Failed)` and shows blocked/skipped counts separately.

The formulas are definitions and acceptance criteria. They do not imply that every expanded time-series metric is already calculated by a dedicated SQL aggregation endpoint on `main`.

### 8.3 Requirements Traceability Matrix

`docs/requirements-traceability-matrix-v1.md` is the companion RTM v1. It maps R1–R7 provisionally from the plan-item references and seed-case links, preserves the explicit FR-REQ-01/02 and NFR-REQ-01/02 statements from the midterm, and marks R8 as requiring its original source wording. The matrix must be updated when the approved R1–R8 baseline is supplied and when WFT test specifications become automated CI tests.

### 8.4 API surface delivered in the November plan items

The following routes have been integrated onto `main` across the November plan items:

| Area | API surface on `main` | Plan item / evidence |
|---|---|---|
| Test Suites | `GET/POST /api/test-suites`, `GET/PUT/DELETE /api/test-suites/{id}` | PLN-16, PR #21 (merged) |
| Test Cases | `GET/POST /api/test-cases`, `GET/PUT/DELETE /api/test-cases/{id}`, `PUT /api/test-cases/{id}/requirements` | PLN-16, PR #21 (merged) |
| Test Runs | `GET/POST /api/test-runs`, `GET /api/test-runs/{id}` | PLN-17, PR #25 (merged) |
| Executions | `POST/PUT /api/test-runs/{run_id}/executions/{execution_id}`, `POST /api/test-runs/{run_id}/executions/{execution_id}/defects` | PLN-17, PR #25 (merged) |
| Release Gate | `GET /api/releases/{id}/gate`, `PUT /api/releases/{id}/criteria`, `PUT /api/releases/{id}/status`, `POST/DELETE /api/releases/{id}/waiver` | PLN-18, PR #27 (merged) |
| Test Plans | `GET/POST /api/test-plans`, `GET/PUT/DELETE /api/test-plans/{id}`, `PUT /api/test-plans/{id}/status`, snapshot and export routes | PLN-26, PR #26 (merged) |
| Cobertura Coverage | `POST /api/projects/{id}/coverage/import`, `GET /api/projects/{id}/coverage/imports`, `GET /api/projects/{id}/coverage/imports/{import_id}` | PLN-23, PR #30 (merged) |

### 8.5 Baseline and integration limitations

1. The original R1–R8 wording remains a source-confirmation item; placeholder rows must not be treated as full requirement statements.
2. FR-REQ-02's release-specific requirement coverage report and the p95 performance target still need implementation / measurement evidence.
3. The JUnit XML and Cobertura import snapshot paths remain separate from interactive PLN-17 Test Runs; imported records do not automatically change test-case status or run-level metrics.
4. Alembic migrations are sequenced on a single linear revision chain from `0001` through `0010` (`0005_junit_imports` → `0006_test_suites_and_cases` → `0007_test_runs_and_executions` → `0008_release_exit_criteria` → `0009_test_plans` → `0010_pln23_coverage`) with no duplicate revision IDs.
5. Test Plan snapshots and exports must be verified on the supported container environment; a successful HTML response alone is not proof that PDF rendering works on the target runtime.
