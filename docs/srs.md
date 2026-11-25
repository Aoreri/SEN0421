# SDS-06 — Software Requirements Specification (SRS)

**Project:** Agile Test and Defect Tracking System  
**Project ID:** SDS-06  
**Plan item:** PLN-37  
**Standard basis:** ISO/IEC/IEEE 29148:2018 — Requirements Engineering  
**Version:** 1.0 — Baseline candidate for team approval  
**Prepared:** 22 November 2026  
**Repository:** [Aoreri/SEN0421](https://github.com/Aoreri/SEN0421)

> This document describes the requirements and implementation status visible in `main` on 22 November 2026. An item marked **In review** is implemented only on an open pull-request branch and is not part of the integrated baseline. This is a project-tailored SRS, not a declaration of formal ISO/IEC/IEEE 29148 conformance.

## 1. Introduction

### 1.1 Purpose

The SRS defines the intended functions, external interfaces, data constraints, quality requirements, and acceptance evidence for SDS-06. It is the requirements baseline used by design, implementation, test planning, verification, release evaluation, and change-impact analysis.

### 1.2 Scope

SDS-06 is a browser-based system for managing software projects, releases, requirements, test suites, test cases, test runs, executions, defects, traceability, metrics, and Test Plans. It provides a REST API and a React/TypeScript user interface. PostgreSQL stores application data; Alembic manages schema changes; Docker Compose provides the local demonstration environment; GitHub Actions verifies changes.

The system is an academic demonstration project. Public demo credentials and local-development database credentials are not suitable for production. The project does not claim independent certification or complete conformance to every clause of the standards listed in this SRS.

### 1.3 Intended audience

- Course instructor and project evaluators.
- Product owner and requirements/documentation contributors.
- Backend and frontend developers.
- Test Lead, Tester, Developer, and Admin users.
- QA / DevOps contributors and reviewers.

### 1.4 Requirement language and identifiers

The words **shall**, **should**, and **may** express mandatory, recommended, and optional project requirements respectively. `FR-*` identifiers denote functional requirements and `NFR-*` identifiers denote non-functional requirements. The course's original `R1`–`R8` identifiers are retained separately. The repository contains placeholder descriptions for R1–R8; therefore, the provisional project-area mappings in the RTM must not be presented as recovered original wording.

### 1.5 Definitions

| Term | Meaning |
|---|---|
| Test case | A uniquely identified verification scenario with steps, expected result, priority, automation flag, and requirement links. |
| Test suite | A named collection of test cases within a project. |
| Test run | A planned execution of selected test cases for a project and optionally a release or suite. |
| Test execution | The recorded result of one test case within a test run. |
| Defect | A recorded product or test problem with severity, status, and history. |
| Traceability | A relationship connecting requirements to test cases and verification evidence. |
| Snapshot | An immutable point-in-time representation of a generated test document. |
| Release gate | A decision based on configured quality criteria and any explicitly recorded waiver. |
| CI | Continuous Integration checks executed by GitHub Actions. |

## 2. Overall description

### 2.1 Product perspective

The product uses a three-tier architecture:

1. **Presentation:** React and TypeScript single-page application.
2. **Application:** FastAPI REST API, request validation, authentication, authorization, business rules, and report generation.
3. **Persistence:** SQLAlchemy models and sessions, Alembic migrations, and PostgreSQL 16.

GitHub Actions is the verification and delivery automation environment; it is not a runtime application tier.

### 2.2 User classes and responsibilities

| Role | Main responsibilities | Current authorization pattern |
|---|---|---|
| Admin | Administration, catalogue changes, oversight, and privileged release operations. | Broad protected-write access. |
| Test Lead | Organize projects/releases/requirements, manage test assets and Test Plans, review test outcomes, and manage release criteria. | Protected project, release, requirement, test-suite, test-case, Test Plan, and release-gate writes. |
| Tester | Maintain test cases and traceability, create defects, execute tests, and perform permitted verification actions. | Test-case/traceability writes, test execution, defect creation, and permitted status transitions. |
| Developer | Investigate and resolve defects. | Developer-authorized defect transitions; no general catalogue administration. |

The backend is authoritative for authorization. A user interface control is not a security boundary.

### 2.3 Operating environment

| Layer | Baseline technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, Uvicorn. |
| Database | PostgreSQL 16. |
| Frontend | React 18, TypeScript, Vite, and Nginx in the production container. |
| Local orchestration | Docker Engine/Desktop and Docker Compose v2. |
| CI | GitHub Actions, Python 3.12, Node.js 22, and PostgreSQL 16 service. |
| Browser endpoints | Frontend `http://localhost:5173`; API `http://localhost:8000`; OpenAPI UI `http://localhost:8000/docs`. |

### 2.4 Constraints

1. Schema changes shall be delivered through new Alembic revisions; merged revisions shall not be edited.
2. The integrated Alembic history shall be a single valid chain. The current `main` chain ends at revision `0010`; new changes shall continue from `0011` and use unique revision identifiers.
3. Test cases shall retain at least one valid requirement association. Cross-project suite/requirement links shall be rejected.
4. Defect history is append-only in PostgreSQL. Rejected transitions shall not create history entries.
5. All repository changes shall use task-specific branches and pull requests to `main`.
6. Tests and migrations shall use disposable databases only.
7. Reports, research notes, and generated binary submissions shall not be committed when repository policy requires them to remain outside the repository; Markdown source work products are maintained under `docs/`.

### 2.5 Assumptions and dependencies

- Users have a modern browser and network access to the local application.
- Docker Compose v2 is installed and the required local ports are available.
- PostgreSQL 16 is available through Compose or a disposable CI service.
- The instructor/team confirms the original R1–R8 wording before that mapping is frozen.
- Open PRs identified in Section 8 are not treated as integrated requirements until merged and verified on `main`.

## 3. System functions and functional requirements

### 3.1 Authentication and authorization

| ID | Requirement | Priority | Baseline status |
|---|---|---|---|
| FR-AUTH-01 | The system shall accept a valid username/password pair and return a signed bearer token with the user's identity and role. | High | Implemented: `POST /api/auth/login`. |
| FR-AUTH-02 | The system shall validate a bearer token and return the authenticated user's identity. | High | Implemented: `GET /api/auth/me`. |
| FR-AUTH-03 | The system shall enforce role checks on protected write and workflow operations at the backend. | High | Implemented for current protected operations. Read-endpoint authentication hardening is in PR #39 and remains a separate integration item. |

### 3.2 Project, release, and requirement catalogue

| ID | Requirement | Priority | Baseline status |
|---|---|---|---|
| FR-CAT-01 | Authorized users shall create, read, update, and delete projects subject to uniqueness and dependency constraints. | High | Implemented. |
| FR-CAT-02 | Authorized users shall manage project releases; duplicate version identifiers within one project shall be rejected. | Medium | Implemented. |
| FR-CAT-03 | Authorized users shall manage project requirements and preserve their project association. | High | Implemented. |

### 3.3 Test suite, test case, and traceability

| ID | Requirement | Priority | Baseline status |
|---|---|---|---|
| FR-CASE-01 | The system shall manage test suites within a project and reject duplicate suite names within that project. | High | Implemented. |
| FR-CASE-02 | A test case shall have a stable identifier, title, status, priority, automation flag, ordered steps, expected result, and optional suite membership. | High | Implemented. |
| FR-TRACE-01 | The system shall maintain a many-to-many association between test cases and requirements and expose the association from both directions. | High | Implemented. |
| FR-TRACE-02 | The system shall reject missing, invalid, or cross-project requirement/suite links without partially changing stored relationships. | High | Implemented. |
| FR-REQ-01 | Every test case shall be linked to at least one valid requirement; creation without a requirement and removal of all requirement links shall be rejected with HTTP 422. | High | Implemented and covered by `test_test_case_and_suite_validation_and_conflicts`. |
| FR-REQ-02 | For a selected release, the system shall show each requirement's linked test-case count and Passed, Failed, and Not Run counts. | High | Gap: a release-specific per-requirement report is not present in the integrated baseline. |

### 3.4 Test execution and defect management

| ID | Requirement | Priority | Baseline status |
|---|---|---|---|
| FR-RUN-01 | The system shall create a test run and one execution record for each selected test case, initially `Not Run`. | High | Implemented. |
| FR-RUN-02 | The system shall record `Passed`, `Failed`, `Blocked`, and `Skipped` results, actual result, notes, executor, and execution time. | High | Implemented. |
| FR-RUN-03 | The system shall allow a failed execution to be associated with one or more defects. | High | Implemented. |
| FR-DEF-01 | An authorized user shall create a defect with a non-empty title, severity, and optional related test case; creation shall start at `Open` and append an initial history record. | High | Implemented. |
| FR-DEF-02 | The backend shall enforce the configured defect transition graph and caller-role restrictions. Unsupported transitions shall return HTTP 409; unauthorized transitions shall return HTTP 403. | High | Implemented. |
| FR-DEF-03 | The system shall expose an ordered defect history containing previous status, new status, and timestamp. | High | Implemented; PostgreSQL protects the history table against UPDATE/DELETE. |
| FR-DEF-04 | A case-linked defect shall not transition from `Resolved` to `Closed` unless its latest relevant verification execution is `Passed`. | High | Implemented and tested. |

### 3.5 Metrics and release control

| ID | Requirement | Priority | Baseline status |
|---|---|---|---|
| FR-MET-01 | The system shall provide total tests, execution rate, pass rate, and open-defect counts. | Medium | Implemented through `GET /api/metrics`. |
| FR-MET-02 | The system shall provide scoped execution trends, requirement coverage, defect reopen rate, defect age, resolution time, burn-up, and severity distribution. | High | Implemented through `GET /api/metrics/expanded` for the current project/release/time scope. |
| FR-REL-01 | The system shall manage release statuses `Planned`, `In Test`, `Ready`, and `Released`. | High | Implemented. |
| FR-REL-02 | The system shall evaluate configurable pass-rate, open-Critical-defect, and requirement-coverage exit criteria before allowing a release to become `Ready` or `Released`. | High | Implemented. |
| FR-REL-03 | An Admin or Test Lead shall record and remove a waiver with a non-empty reason, user identity, and timestamp; a waiver shall not alter the underlying measured criteria. | Medium | Implemented. |
| FR-SPR-01 | The system shall persist named sprints and allow sprint-scoped expanded metrics. | Medium | In review: PLN-28, PR #34; not part of the integrated baseline as of this SRS. |

### 3.6 Imports and document generation

| ID | Requirement | Priority | Baseline status |
|---|---|---|---|
| FR-IMP-01 | The system shall import bounded JUnit XML, retain commit/branch metadata, map stable test-case keys, and report unmatched results rather than silently dropping them. | Medium | Implemented. |
| FR-IMP-02 | The system shall import Cobertura line/branch coverage evidence and associate it with project/import metadata. | Medium | Implemented. |
| FR-PLAN-01 | The system shall manage versioned Test Plan records with `Draft`, `In Review`, and `Approved` states and enforce valid transitions. | High | Implemented. |
| FR-PLAN-02 | The system shall preserve point-in-time Test Plan snapshots containing rendered HTML and structured data. | High | Implemented. |
| FR-PLAN-03 | The system shall export a live Test Plan or stored snapshot as HTML or PDF. | Medium | Implemented at API level. Actual WeasyPrint rendering in the supported container must still be verified; the application includes a fallback path. |
| FR-DOC-01 | The system should generate Test Incident Reports and Test Logs for defects and test runs, with snapshot and HTML/PDF export. | Medium | In review: PLN-39, PR #37. |
| FR-DOC-02 | The system should generate a release-based Test Summary Report with outcome totals, per-requirement results, defect summary, and exit-gate evaluation, with snapshot and HTML/PDF export. | Medium | In review: PLN-30, PR #38. |
| FR-REL-04 | The system should build and publish versioned v1.0 Docker images and release attachments from a version tag. | Medium | In review: PLN-36, PR #40. |

### 3.7 Original R1–R8 baseline

The database seeds R1–R8 with placeholder titles and empty descriptions. Seed links and project-plan associations provide provisional area-level clues, not the exact original requirement statements. This SRS therefore preserves R1–R8 as external course identifiers and maps them provisionally in `docs/requirements-traceability-matrix-v2.md`. The team must insert the approved original wording before claiming a final one-to-one R1–R8 baseline.

## 4. External interface requirements

### 4.1 User interface

The integrated frontend exposes the dashboard/metrics panel at `/`, test-case and traceability management at `/test-cases`, test-run execution at `/test-runs`, project/requirement management at `/projects`, login/role selection at `/login`, and defect details at `/defects/:id`. The dedicated Test Plan management screen is in review under PLN-31, PR #41; the Test Plan API is already available in `main`.

### 4.2 REST API

All application API routes are under `/api`. The principal route groups are:

| Area | Main routes |
|---|---|
| Health | `GET /api/health` |
| Authentication | `POST /api/auth/login`, `GET /api/auth/me` |
| Projects / releases / requirements | `/api/projects`, `/api/releases`, `/api/requirements` and their item routes |
| Suites / cases / traceability | `/api/test-suites`, `/api/test-cases`, `/api/test-cases/{id}/requirements`, `/api/requirements/{id}/test-cases` |
| Runs / executions | `/api/test-runs`, `/api/test-runs/{id}`, `/api/test-runs/{run_id}/executions/{execution_id}` and `/defects` subroute |
| Defects | `/api/defects`, `/api/defects/{id}/transition`, `/api/defects/{id}/history` |
| Metrics / release gate | `/api/metrics`, `/api/metrics/expanded`, `/api/releases/{id}/gate`, `/criteria`, `/status`, `/waiver` |
| JUnit / Cobertura | `/api/projects/{id}/runs/import`, `/runs/imports`, `/coverage/import` |
| Test Plans | `/api/test-plans`, `/api/test-plans/{id}/status`, `/snapshots`, `/export` |

FastAPI OpenAPI documentation is available at `/docs` when the backend is running.

### 4.3 Authentication interface

Protected operations accept `Authorization: Bearer <token>`. The login endpoint returns an HS256-signed token with an eight-hour lifetime. Read-endpoint authentication hardening is being addressed by PLN-29 (PR #39); until that change is merged, some GET endpoints in the current baseline remain public.

### 4.4 Persistence and deployment interfaces

The backend accesses PostgreSQL through SQLAlchemy sessions. Alembic manages the schema. Docker Compose defines the `db`, `backend`, and `frontend` services and service health checks. CI uses a disposable PostgreSQL 16 service for database integration tests.

## 5. Data requirements

The relational model includes:

- `users`, `projects`, `releases`, and `requirements`;
- `test_suites`, `test_cases`, and `test_case_requirements`;
- `test_runs`, `test_executions`, and `execution_defects`;
- `defects`, `defect_transitions`, and append-only `defect_history`;
- `imported_test_runs` and `imported_test_results` for JUnit snapshots;
- `coverage_imports` and related coverage-result data for Cobertura;
- `test_plans` and `test_plan_snapshots`.

The legacy `test_cases.requirement` field remains alongside the many-to-many association. Current API operations keep the returned relationship consistent; any future removal of the legacy field requires a separate migration and compatibility review. JUnit import snapshots are separate from interactive test runs and do not implicitly update live test-case statuses or execution metrics.

## 6. Non-functional requirements

| ID | Quality attribute | Requirement / target | Evidence and status |
|---|---|---|---|
| NFR-REQ-01 | Performance efficiency | With 200 requirements and 1,000 test cases, the release traceability report shall be generated within 2 seconds at p95 in local Compose. | Target only; the release-specific report and benchmark evidence are not yet available. |
| NFR-REQ-02 | Installability / portability | On a clean machine with stated prerequisites, the stack shall become healthy from one `docker compose up` command within 10 minutes. | Docker Compose and health checks exist; clean-machine elapsed-time evidence is still required. |
| NFR-SEC-01 | Security | Passwords shall be stored as bcrypt hashes; tokens shall be signed and time-limited; protected operations shall enforce backend role checks. | Core mechanisms are implemented. Public demo credentials are not production-safe. GET-endpoint hardening and audit work is in PR #39. |
| NFR-REL-01 | Reliability / data integrity | Every accepted defect creation and transition shall append history; PostgreSQL shall reject history UPDATE/DELETE. | Implemented and covered by PostgreSQL integration tests. |
| NFR-MAINT-01 | Maintainability | Backend, frontend, persistence, and migrations shall remain separated; PRs shall run lint, type checks, backend tests, PostgreSQL tests, and frontend build. | Repository CI implements these checks. |
| NFR-TRACE-01 | Traceability | Test cases shall preserve valid requirement links; invalid or cross-project references shall be rejected. | Implemented and covered by API tests. |
| NFR-OBS-01 | Observability | Test and release reports shall show their scope, source period, denominators, and generation time. | Implemented in metrics/reporting contracts where available; pending report PRs remain subject to integration review. |

## 7. Verification and acceptance

- Functional/API behavior is verified through FastAPI integration tests on disposable databases.
- PostgreSQL-only behavior, including append-only defect history, is verified against PostgreSQL 16; SQLite success is not used as a substitute for PostgreSQL evidence.
- Frontend quality is verified with ESLint, TypeScript type checking, and the Vite production build.
- Alembic migrations are verified by the PostgreSQL CI job; the integrated chain must remain linear after new PRs merge.
- Performance and clean-machine installability require separate measured evidence.
- HTML/PDF response tests prove the response type and basic file signature; they do not alone prove visual or multi-page PDF rendering quality in the target container.
- Each requirement-to-module-to-test mapping is recorded in `docs/requirements-traceability-matrix-v2.md`.

## 8. Baseline status and known limitations (22 November 2026)

| Item | Status at baseline date |
|---|---|
| Core catalogue, traceability, test execution, defect lifecycle, expanded metrics, release gate, JUnit/Cobertura import, Test Plan API | Integrated on `main`. |
| Test Incident Report / Test Log generation | PR #37 (PLN-39), open; individual PR checks reported successful. |
| Test Summary Report generation | PR #38 (PLN-30), open; individual PR checks reported successful. |
| Read-endpoint authentication hardening and security scans | PR #39 (PLN-29), open. |
| v1.0 release workflow and release attachments | PR #40 (PLN-36), open; not yet a published release. |
| Sprint entity and sprint metrics filter | PR #34 (PLN-28), open. |
| Test Plan management frontend screen | PR #41 (PLN-31), open. |
| FR-REQ-02 release-specific traceability report | Not present in the integrated baseline. |
| NFR-REQ-01 / NFR-REQ-02 measurement | Not yet evidenced. |
| Full original R1–R8 wording | Requires the original approved course/project source. |

## 9. References

1. ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements engineering*. Current published edition at the date of this SRS; a third edition is under development. [ISO catalogue](https://www.iso.org/standard/72089.html).
2. ISO/IEC/IEEE 12207 — software life-cycle processes; project standard baseline to be confirmed with the instructor.
3. ISO/IEC/IEEE 29119-2:2021 — test processes; ISO/IEC/IEEE 29119-3:2021 — test documentation.
4. IEEE 1016 — Software Design Descriptions.
5. ISO/IEC 25010:2023 — product quality model.
6. `README.md`, `AGENTS.md`, `docs/test-plan.md`, `docs/metric-definitions.md`, `docs/test-case-specification-workflow.md`, `docs/api-auth.md`, `backend/app/`, `backend/alembic/versions/`, `backend/tests/`, `docker-compose.yml`, and `.github/workflows/ci.yml` in `Aoreri/SEN0421` (baseline reviewed 22 November 2026).

## 10. Version history and approval

| Version | Date | Change | Status |
|---|---|---|---|
| 0.1 | 11 November 2026 | Initial project requirements draft. | Superseded. |
| 0.2 | 18 November 2026 | PLN-25 metrics and traceability expansion. | Superseded by this baseline candidate. |
| 1.0 | 22 November 2026 | Updated functional/API baseline, Test Plan integration, quality requirements, and pending-PR status for PLN-37. | Candidate for team/instructor review; not yet approved. |
