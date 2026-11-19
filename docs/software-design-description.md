# SDS-06 — Software Design Description (SDD)

**Standard reference:** IEEE 1016 — Software Design Descriptions  
**Work package:** PLN-14  
**Version:** 0.2 - Draft for team review
**Prepared:** 18 November 2026
**Project:** Agile Test and Defect Tracking System  
**Repository:** [Aoreri/SEN0421](https://github.com/Aoreri/SEN0421)

> This SDD describes the design visible in the current repository. It is an implementation-oriented design baseline for team review, not a claim of clause-level IEEE 1016 conformance. The CI evidence section records an existing successful workflow run; this documentation change does not create a new CI workflow.

## 1. Purpose and scope

This Software Design Description records the SDS-06 system context, logical composition, deployment arrangement, API boundaries, persistence model, security design, and key design decisions. It supports PLN-14 and provides a reference for implementation, verification, and change impact analysis.

The current architecture is a three-tier web application: React + TypeScript frontend, FastAPI backend, and PostgreSQL database. GitHub Actions is the continuous-integration environment, not a runtime application component.

## 2. Stakeholders and design concerns

| Stakeholder | Main design concern |
|---|---|
| Admin | Administrative access, user roles, catalogue integrity, oversight. |
| Test Lead | Project/release/requirement organization, test traceability, defect verification. |
| Tester | Test-case visibility, requirement links, defect reporting, verification transitions. |
| Developer | Defect investigation and implementation-side transitions. |
| Product owner / requirements contributor | Requirement coverage, traceability, project work products, standards alignment. |
| Backend developer | API contracts, persistence, migrations, authorization, transactional integrity. |
| Frontend developer | UI composition, API integration, validation, error display. |
| QA / DevOps | Repeatable test environment, CI checks, database test evidence, build/deployment setup. |
| Instructor / evaluator | Standards traceability, test artefacts, review evidence, and demonstrated system behavior. |

## 3. Design viewpoints

### 3.1 Context viewpoint

The Context Viewpoint describes the system boundary and external actors. Users interact with the browser UI. The frontend calls the FastAPI REST API. The backend authenticates users, applies role checks, executes business operations, and reads/writes PostgreSQL. GitHub Actions checks source changes independently and publishes workflow results to the repository.

```mermaid
flowchart LR
    Admin[Admin]
    Lead[Test Lead]
    Tester[Tester]
    Dev[Developer]
    Browser[Web Browser]
    UI[React + TypeScript UI]
    API[FastAPI REST API]
    DB[(PostgreSQL 16)]
    CI[GitHub Actions CI]
    Repo[GitHub Repository]

    Admin --> Browser
    Lead --> Browser
    Tester --> Browser
    Dev --> Browser
    Browser --> UI
    UI <-->|JSON over HTTP| API
    API <-->|SQLAlchemy / SQL| DB
    Repo --> CI
    CI -->|workflow results| Repo
```

**Concerns addressed:** system boundary, user roles, frontend/backend separation, persistence location, and the distinction between runtime requests and source-code verification.

### 3.2 Logical / composition viewpoint

The Logical Viewpoint separates presentation, API/application behavior, persistence access, and data storage. The backend currently groups authentication in `app/auth.py`, project/release/requirement operations in `app/projects.py`, shared database setup in `app/db.py`, and core records in `app/models.py`. Defect and metric routes are in `app/main.py`. PLN-22 adds bounded, entity-safe XML parsing in `app/junit.py` and authenticated import/report routes in `app/junit_imports.py`; see [the import contract](junit-import.md).

```mermaid
flowchart TB
    subgraph Presentation[Presentation Layer]
        React[React + TypeScript SPA]
        APIClient[frontend/src/api.ts]
    end
    subgraph Application[FastAPI Application Layer]
        Routes[REST routes / request validation]
        Auth[JWT authentication + role checks]
        Catalog[Projects / releases / requirements]
        Defects[Defect lifecycle + history]
        Metrics[Test metrics]
    end
    subgraph Persistence[Persistence Layer]
        ORM[SQLAlchemy models and sessions]
        Migrations[Alembic migrations]
    end
    DB[(PostgreSQL 16)]
    React --> APIClient --> Routes
    Routes --> Auth
    Routes --> Catalog
    Routes --> Defects
    Routes --> Metrics
    Auth --> ORM
    Catalog --> ORM
    Defects --> ORM
    Metrics --> ORM
    ORM --> DB
    Migrations --> DB
```

**Concerns addressed:** separation of responsibilities, dependency direction, testability, and the location of authorization and data integrity controls.

### 3.3 Deployment viewpoint

```mermaid
flowchart TB
    subgraph Host[Developer / Demo Host]
        Browser[Browser :5173]
        subgraph Compose[Docker Compose Network]
            Frontend[Frontend container: Nginx serving Vite build]
            Backend[Backend container: FastAPI :8000]
            Postgres[(PostgreSQL 16 :5432)]
        end
    end
    Browser --> Frontend
    Frontend -->|/api requests| Backend
    Backend --> Postgres
    Backend -. startup waits for healthy DB .-> Postgres
    Frontend -. startup waits for healthy API .-> Backend
```

The Compose file defines three services: `db`, `backend`, and `frontend`. PostgreSQL uses a named `pgdata` volume. The backend uses `DATABASE_URL` to connect to the `db` service, applies Alembic migrations on startup as documented in the repository, and exposes a health endpoint. The frontend image serves the built application with Nginx and routes `/api/` requests to the backend. Local ports are 5432, 8000, and 5173 respectively.

GitHub Actions is outside this runtime deployment diagram. It checks repository changes using hosted runners and a PostgreSQL 16 service for the database-specific test job.

## 4. Information viewpoint and data model

### 4.1 Entity relationship diagram

```mermaid
erDiagram
    USER {
        int id PK
        string username UK
        string password_hash
        string role
    }
    PROJECT {
        int id PK
        string name UK
        string description
    }
    RELEASE {
        int id PK
        int project_id FK
        string version
    }
    REQUIREMENT {
        string id PK
        int project_id FK
        string title
        string description
    }
    TEST_CASE {
        string id PK
        string title
        string requirement
        string status
    }
    TEST_CASE_REQUIREMENTS {
        string test_case_id PK, FK
        string requirement_id PK, FK
    }
    DEFECT {
        int id PK
        string title
        string severity
        string status
        string test_case FK
    }
    DEFECT_TRANSITION {
        string from_status PK
        string to_status PK
        json allowed_roles
    }
    DEFECT_HISTORY {
        int id PK
        int defect_id FK
        string from_status
        string to_status
        datetime at
    }

    IMPORTED_TEST_RUN {
        int id PK
        int project_id FK
        int imported_by FK
        string commit_sha
        string branch
        datetime created_at
        json summary
    }
    IMPORTED_TEST_RESULT {
        int id PK
        int run_id FK
        int position
        string reported_key
        string test_case_id FK
        string status
        string unmatched_reason
    }

    PROJECT ||--o{ IMPORTED_TEST_RUN : receives
    USER ||--o{ IMPORTED_TEST_RUN : imports
    IMPORTED_TEST_RUN ||--o{ IMPORTED_TEST_RESULT : contains
    TEST_CASE o|--o{ IMPORTED_TEST_RESULT : matches
    PROJECT ||--o{ RELEASE : contains
    PROJECT ||--o{ REQUIREMENT : defines
    REQUIREMENT ||--o{ TEST_CASE_REQUIREMENTS : linked_by
    TEST_CASE ||--o{ TEST_CASE_REQUIREMENTS : linked_by
    TEST_CASE o|--o{ DEFECT : associated_with
    DEFECT ||--o{ DEFECT_HISTORY : records
```

`USER` links to imported runs via `imported_by`; defects/history still have no user foreign key. `DEFECT_TRANSITION` remains a rule catalogue without a relationship to a specific user row.

PLN-22 import snapshots are independent of future PLN-17 general test runs. Migration `0005_junit_imports` adds these tables without changing existing test-case states, metrics, or defect history.

### 4.2 Entity/table catalogue

| Table | Key attributes | Purpose / constraints |
|---|---|---|
| `users` | `id` PK, `username` unique, `password_hash`, `role` | Login identity and application role. Password values are stored as bcrypt hashes. |
| `imported_test_runs` | `id` PK, `project_id` FK, `imported_by` FK, optional `commit_sha`/`branch`, `created_at`, `summary` JSON | Persisted JUnit import snapshot and result totals. |
| `imported_test_results` | `id` PK, `run_id` FK, `position`, nullable `test_case_id` FK, reported key/name/class/suite, status, duration, message, unmatched reason | Unique `(run_id, position)` preserves ordered results, including unmatched keys. Run and results are stored in one transaction. |
| `projects` | `id` PK, `name` unique, `description` | Project catalogue. |
| `releases` | `id` PK, `project_id` FK, `version` | Release catalogue; `(project_id, version)` is unique. |
| `requirements` | `id` PK (string), `project_id` FK, `title`, `description` | Requirements belonging to a project. Initial IDs R1–R8 are seeded with placeholder descriptions. |
| `test_cases` | `id` PK (string), `title`, `requirement`, `status` | Test-case catalogue. `requirement` is a legacy string field and is not declared as a foreign key in the current model. |
| `test_case_requirements` | Composite PK (`test_case_id`, `requirement_id`); both are FKs | Many-to-many requirement/test-case traceability. Migration 0004 populates it using the legacy `test_cases.requirement` values. |
| `defects` | `id` PK, `title`, `severity`, `status`, nullable `test_case` FK | Defect records; a defect may refer to a test case. |
| `defect_transitions` | Composite PK (`from_status`, `to_status`), `allowed_roles` JSON | Configurable allowed status transitions and role lists. |
| `defect_history` | `id` PK, `defect_id` FK, `from_status`, `to_status`, `at` | Ordered, append-only record of defect creation and state changes. PostgreSQL trigger rejects UPDATE/DELETE. |

### 4.3 Important traceability design note

The current implementation has both a legacy single-value `test_cases.requirement` string and the many-to-many `test_case_requirements` association. The migration initializes the association table from the legacy string, and the API returns the relationship list. The two representations must be kept consistent during future schema changes. A future migration may remove or formally deprecate the legacy field only after all readers/writers and seed data are updated and verified.

## 5. Component responsibilities and interfaces

| Component / file | Responsibility | Main interface |
|---|---|---|
| `frontend/src/` | Browser UI and user interaction | Calls API functions through `frontend/src/api.ts`. |
| `backend/app/main.py` | Health, test-case list, defect workflow/history, metrics | FastAPI routes under `/api`. |
| `backend/app/auth.py` | Login, JWT validation, role dependencies | `/api/auth/login`, `/api/auth/me`, dependency helpers. |
| `backend/app/projects.py` | Project, release, requirement CRUD and traceability | `/api/projects`, `/api/releases`, `/api/requirements`. |
| `backend/app/junit.py` / `backend/app/junit_imports.py` | Safe JUnit parsing, authenticated project-scoped mapping and atomic import snapshots | POST import and GET list/detail under `/api/projects/{project_id}/runs`; see `junit-import.md`. |
| `backend/app/models.py` | SQLAlchemy entity definitions and association table | ORM model layer. |
| `backend/app/db.py` | Database engine and session dependency | SQLAlchemy engine/session. |
| `backend/alembic/` | Versioned schema evolution and seed rules | `alembic upgrade head`. |
| `docker-compose.yml` | Local service orchestration and health ordering | `docker compose up --build -d --wait`. |
| `.github/workflows/ci.yml` | Automated verification for repository changes | Push to main, pull requests, and manual dispatch. |

## 6. Main data and control flows

### 6.1 Authentication flow

1. User submits username/password through the frontend.
2. Frontend calls `POST /api/auth/login`.
3. Backend retrieves the user record, verifies the bcrypt password hash, and issues a signed HS256 JWT with an eight-hour lifetime.
4. Frontend uses the bearer token for protected requests.
5. Backend validates token expiry/signature, resolves the user, and applies role checks for protected operations.

The JWT secret is read from `JWT_SECRET`; the current code generates a random process-local fallback when the environment variable is absent. A stable configured secret is required for multi-worker or persistent deployment. The repository's demo configuration is not a production security baseline.

### 6.2 Defect flow

```mermaid
stateDiagram-v2
    [*] --> Open: create defect
    Open --> InProgress: Developer / Admin
    InProgress --> Resolved: Developer / Admin
    Resolved --> Closed: Tester / Test Lead / Admin
    Resolved --> Open: Reopen by Tester / Test Lead / Admin
    Closed --> Open: Reopen by Tester / Test Lead / Admin
```

Each accepted creation/transition writes a new `defect_history` row. Unsupported transitions return HTTP 409; role-denied transitions return HTTP 403. A rejected operation should not create a history row. PostgreSQL trigger protection makes the history table append-only.

### 6.3 Requirement traceability flow

1. An authorized user creates or updates a requirement under a project.
2. A Tester, Test Lead, or Admin updates `/api/requirements/{requirement_id}/test-cases` with the target test-case IDs.
3. The backend verifies that each test case exists and replaces the relationship list in `test_case_requirements`.
4. Requirement reads return linked test-case IDs; test-case reads return linked requirement IDs.

## 7. Security and integrity design

- Passwords are stored as bcrypt hashes, not plaintext.
- JWT bearer tokens are signed using HS256 and expire after eight hours.
- Role enforcement is implemented in FastAPI dependencies and transition-rule checks.
- Invalid/expired/forged tokens are rejected with HTTP 401.
- Authorization failures return HTTP 403; unsupported defect transitions return HTTP 409.
- PostgreSQL protects defect history against UPDATE/DELETE through a trigger.
- Demo accounts and local database credentials are public development data. They must be changed and secrets configured before any non-demo deployment.
- The current API CORS configuration is permissive for the template; production origins should be restricted before deployment.

## 8. Continuous integration design and PLN-14 evidence

The current `.github/workflows/ci.yml` workflow runs on pushes to `main`, pull requests, and manual dispatch. It has three jobs:

1. **Backend checks:** Python 3.12; install backend dev requirements; Ruff lint; mypy; pytest with Cobertura coverage output on the default disposable SQLite setup.
2. **Backend PostgreSQL tests:** PostgreSQL 16 service; run backend pytest and generate Cobertura output.
3. **Frontend checks:** Node.js 22; `npm ci`; ESLint; TypeScript type check; Vite production build.

A successful workflow execution is already present on `main`:

- Run ID: `42972187931`
- Date: 11 November 2026
- Conclusion: `success`
- Evidence: https://github.com/Aoreri/SEN0421/actions/runs/42972187931

This provides evidence that the current CI pipeline has completed successfully. It does not prove every future PR will pass, and CI success alone does not verify unimplemented report-generation or result-import functionality.

## 9. Design constraints and open decisions

1. Confirm with the instructor whether course documentation should explicitly baseline ISO/IEC/IEEE 12207:2026 or retain a previously expected edition.
2. Obtain and validate the original full R1–R8 wording. The current database has placeholder requirement descriptions.
3. Decide whether to deprecate the legacy `test_cases.requirement` column after verifying compatibility with all current data and API consumers.
4. Implement Cobertura ingestion and decide how PLN-22 JUnit snapshots integrate with future PLN-17 general test runs. JUnit XML import, project-scoped key mapping, and unmatched-result reporting are available; see `junit-import.md`.
5. Implement document generation and verify PDF/HTML output inside the container before marking report generation complete.
6. Review CORS, JWT secret configuration, demo credentials, and database credentials before any production-like deployment.

## 10. Standards and references

1. IEEE 1016 — Software Design Descriptions (design-description reference).
2. ISO/IEC/IEEE 12207:2026 — software life-cycle process context, subject to instructor confirmation of the course baseline edition.
3. ISO/IEC/IEEE 29119-2:2021 and 29119-3:2021 — testing process and test documentation context.
4. SDS-06 Bi-Weekly Progress Report #1 and Midterm Questions/Evaluation Guide.
5. Repository implementation: `backend/app/`, `backend/alembic/versions/`, `backend/tests/`, `docker-compose.yml`, `.github/workflows/ci.yml`, `README.md`, and `AGENTS.md`.

## 11. PLN-27 design update — workflow verification, demonstration and November modules

**Prepared:** 18 November 2026  
**Plan item:** PLN-27 — IEEE 829 Test Case Specification, interim demonstration scenario, and SDD update for the new modules.

This section extends the PLN-14 design baseline. It documents the November work-package design as it appears in the team's open PRs; it does not mark those branches as merged or production-ready.

### 11.1 Updated logical composition

The application retains its three-tier architecture. The application layer is expanded with the following responsibilities:

```mermaid
flowchart TB
    subgraph UI[React + TypeScript Presentation]
        CatalogUI[Test Case / Suite screens]
        RunUI[Test Run execution workbench]
        MetricsUI[Metrics charts and Release Gate card]
        PlanUI[Test Plan editor and export actions]
    end
    subgraph API[FastAPI Application]
        Auth[JWT and RBAC]
        Catalog[Test Suite / Test Case / Requirement APIs]
        Runs[Test Run / Test Execution APIs]
        Defects[Defect workflow and verification gate]
        Releases[Release status / exit-criteria / waiver service]
        Plans[Test Plan lifecycle / snapshot / renderer]
        Metrics[Metrics and report aggregation]
        Imports[JUnit XML importer]
    end
    subgraph Data[Persistence]
        ORM[SQLAlchemy models and sessions]
        Migrations[Alembic migration chain]
        PG[(PostgreSQL 16)]
    end
    CatalogUI --> Catalog
    RunUI --> Runs
    RunUI --> Defects
    MetricsUI --> Metrics
    MetricsUI --> Releases
    PlanUI --> Plans
    API --> Auth
    Catalog --> ORM
    Runs --> ORM
    Defects --> ORM
    Releases --> ORM
    Plans --> ORM
    Metrics --> ORM
    Imports --> ORM
    ORM --> PG
    Migrations --> PG
```

**Design responsibilities:**

- **Test Suite / Test Case service (`projects.py` in PLN-16 branch):** project-scoped suite management; stable test-case IDs; ordered steps; expected result; priority; automation flag; optional suite membership; requirement links.
- **Test Run / Test Execution service (`runs.py` in PLN-17 branch):** run creation, per-case execution rows, result/notes, executor and time, and execution-to-defect association.
- **Defect verification gate (`main.py` in PLN-17 branch):** a case-linked defect cannot transition from `Resolved` to `Closed` when the latest relevant verification execution is missing or is not `Passed`.
- **Release gate (`projects.py` in PLN-18 branch):** release status, configurable pass-rate / Critical-defect / requirement-coverage thresholds, status-transition validation, and privileged waiver recording.
- **Test Plan service (`test_plans.py` in PLN-26 branch):** Test Plan CRUD, `Draft / In Review / Approved` lifecycle, point-in-time snapshot and Jinja2-based HTML/PDF rendering.
- **Metrics presentation (`PLN-21` branch) and metrics aggregation (`PLN-24` plan item):** run-outcome trends, defect trend / severity views, and release-gate summary. UI work and backend aggregation must be tracked independently.

### 11.2 Information-model delta

The following are the proposed / PR-described data structures. They are not part of the current `main` schema until their PRs are merged and migrations are applied.

| Entity / relation | Key attributes described by the plan / PR | Purpose and constraints |
|---|---|---|
| `test_suites` | `id` PK, `project_id` FK, `name`, `description` | A project-scoped suite; `(project_id, name)` is unique. A suite with attached test cases must not be deleted. |
| `test_cases` extension | Existing stable `id`; `suite_id` nullable FK; `priority`; `automated`; `steps` JSON; `expected_result`; requirement associations | Keeps a stable external test-case key and enough specification data to execute and review the case. Priority values in PLN-16 are `Low`, `Medium`, `High`, `Critical`. |
| `test_runs` | `id` PK, `name`, `project_id` FK, optional `release_id` FK, optional `suite_id`, `created_by`, `created_at` | Groups the planned case executions for a project/release. |
| `test_executions` | `id` PK, `run_id` FK, `test_case_id` FK, `status`, `actual_result`, `notes`, `executed_by`, `executed_at` | One execution row per selected case in a run; unique `(run_id, test_case_id)`; initial status `Not Run`. |
| `execution_defects` | Composite key (`execution_id`, `defect_id`) | Associates one execution with one or more defects; supports failed-test investigation and verification evidence. |
| `releases` extension | `status`, `min_pass_rate`, `max_open_critical`, `min_req_coverage`, `waived_by`, `waiver_reason`, `waived_at` | Stores release lifecycle, exit thresholds and waiver metadata. Proposed states: `Planned`, `In Test`, `Ready`, `Released`. |
| `test_plans` | `id` PK, project/release IDs, `version`, `title`, `status`, `scope`, `approach`, `pass_fail_criteria`, `environment`, `schedule_risks`, `created_by`, `created_at` | Stores a versioned, reviewable Test Plan. `(project_id, version)` is unique. |
| `test_plan_snapshots` | `id` PK, `test_plan_id` FK, `version`, `status`, `html_content`, structured `payload`, `generated_by`, `generated_at` | Preserves point-in-time output for audit / reproducible report export. |

The existing `imported_test_runs` / `imported_test_results` entities represent PLN-22 JUnit import snapshots. They are deliberately distinct from interactive `test_runs` / `test_executions`; import snapshots do not automatically mutate test-case status or interactive-run metrics.

### 11.3 Execution and defect-control flow

```mermaid
sequenceDiagram
    actor Tester
    participant UI as React UI
    participant Run as Test Run API
    participant DB as PostgreSQL
    participant Defect as Defect API
    Tester->>UI: Create run for project / release / cases
    UI->>Run: POST /api/test-runs
    Run->>DB: Create run and Not Run rows
    DB-->>Run: Persisted run + executions
    Run-->>UI: Run detail
    Tester->>UI: Record Failed result and notes
    UI->>Run: POST/PUT execution result
    Run->>DB: Save Failed result and executed_at
    Tester->>UI: Open defect from failed execution
    UI->>Run: POST execution/defects
    Run->>DB: Create defect link and initial defect history
    Tester->>UI: Resolve defect and attempt close
    UI->>Defect: POST /api/defects/{id}/transition (Closed)
    Defect->>DB: Check latest verification execution
    DB-->>Defect: Latest result is not Passed
    Defect-->>UI: HTTP 409 — closure blocked
    Tester->>UI: Record a later Passed verification execution
    UI->>Run: Update verification execution
    Tester->>UI: Close defect again
    UI->>Defect: POST transition (Closed)
    Defect->>DB: Verify latest result Passed and append history
    Defect-->>UI: Closed
```

The history table remains append-only. Rejected transitions must not create a history row. The verification gate is an additional condition for `Resolved → Closed`; it does not replace the existing transition table or role authorization.

### 11.4 Release-gate control flow

1. An Admin or Test Lead configures `min_pass_rate`, `max_open_critical`, and `min_req_coverage` for a release.
2. `GET /api/releases/{id}/gate` reports actual values, per-criterion booleans, combined `gate_passed`, and any active waiver.
3. A release may move through `Planned → In Test → Ready → Released` only as allowed by the lifecycle rules.
4. A transition to `Ready` or `Released` is rejected with HTTP 409 when the criteria are not satisfied and there is no active waiver.
5. An Admin or Test Lead may record a non-empty waiver reason. The waiver records the user and time; metrics remain unchanged and the UI must show that the gate was waived rather than passed.

### 11.5 Test Plan lifecycle and snapshot flow

The Test Plan service stores versioned plans with `Draft`, `In Review`, and `Approved` states. The PR-described transitions are constrained; direct `Draft → Approved` is invalid. A snapshot stores rendered HTML and structured source payload at a point in time, including the plan version/status and generated-by/time metadata. HTML/PDF export may use the live plan or an identified stored snapshot. PDF output must be validated in the supported container/runtime; a Windows fallback is not a substitute for target-runtime validation.

### 11.6 API boundaries added by the plan items

| Component | Routes described by the corresponding PR | Plan item / current review state |
|---|---|---|
| Test Suites / Test Cases | `/api/test-suites`; `/api/test-suites/{id}`; `/api/test-cases`; `/api/test-cases/{id}`; `/api/test-cases/{id}/requirements` | PLN-16, PR #21 open |
| Test Runs / Executions | `/api/test-runs`; `/api/test-runs/{id}`; `/api/test-runs/{run_id}/executions/{execution_id}`; execution `/defects` subroute | PLN-17, PR #25 open |
| Release gate | `/api/releases/{id}/gate`; `/criteria`; `/status`; `/waiver` | PLN-18, PR #27 open |
| Test Plans | `/api/test-plans`; `/api/test-plans/{id}`; `/status`; `/snapshots`; `/export` | PLN-26, PR #26 open |

These are PR-described boundaries. Confirm the final merged OpenAPI schema before updating the stable API reference.

### 11.7 Integration dependency — Alembic revision sequencing

The current `main` migration chain ends at `0005_junit_imports`. The open PLN-16, PLN-17, PLN-18 and PLN-26 branches each introduce a migration whose draft uses revision ID `0006` and `down_revision = "0005"`. Those revisions cannot coexist unchanged in one linear Alembic history.

Before the combined feature set is merged or demonstrated against one upgraded database, the integration owner must coordinate a single linear chain. A possible sequence following the plan dates is:

1. `0006_test_suites_and_cases` (PLN-16 / PR #21)
2. `0007_test_runs_and_executions` (PLN-17 / PR #25)
3. `0008_test_plans` (PLN-26 / PR #26)
4. `0009_release_exit_criteria` (PLN-18 / PR #27)

This is a sequencing proposal, not a change already made to the team's branches. The actual order must follow dependency/review decisions. Each migration's `revision` and `down_revision` must be updated consistently, and `alembic upgrade head`, `alembic check`, and PostgreSQL integration tests must pass on the combined branch before the system is considered demo-ready.

### 11.8 Verification and review notes

- Workflow case definitions are provided by `docs/test-case-specification-workflow.md`; the live demonstration steps are in `docs/mid-period-demo-scenario.md`.
- Metric formulas and seed-data acceptance values are defined in `docs/metric-definitions.md`.
- The R1–R8 mapping is provisional until the original full requirement wording is confirmed; see `docs/requirements-traceability-matrix-v1.md`.
- Open PR status is not proof of integrated behavior. For each component, use the final merged PR commit and successful CI run as the configuration baseline.
- Keep UI, API, data model, migration, and test descriptions synchronized after integration. Do not describe the frontend preview fallback as a persisted backend capability.
