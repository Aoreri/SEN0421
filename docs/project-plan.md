# SDS-06 — Project Plan

**Project:** Agile Test and Defect Tracking System  
**Work package:** PLN-02  
**Version:** 0.1 — Draft for team review  
**Prepared:** 11 November 2026  
**Repository:** [Aoreri/SEN0421](https://github.com/Aoreri/SEN0421)

## 1. Project overview

SDS-06 is an academic project to develop an Agile Test and Defect Tracking System that brings project and release information, requirements, test-case traceability, defect workflow, and basic test metrics into one web application. The project uses a tailored software life-cycle approach based on ISO/IEC/IEEE 12207 and testing-documentation practices informed by the legacy IEEE 829 document names and the ISO/IEC/IEEE 29119 series.

The current repository is a demo/template baseline. It is not a production deployment and it does not have a live customer or production security configuration.

## 2. Objectives and success criteria

1. Maintain a traceable requirements baseline and connect test cases to requirements.
2. Provide authenticated, role-aware access for Admin, Test Lead, Tester, and Developer users.
3. Manage projects, releases, requirements, defects, defect transitions, and defect history.
4. Provide basic execution/pass metrics and open-defect counts.
5. Produce project planning and test documentation suitable for the course deliverables.
6. Maintain repeatable quality checks through GitHub Actions.
7. Preserve project decisions and work products in the repository through branch-based pull requests.

Success for the current delivery period is demonstrated by the PLN-02 planning package, the PLN-03 Test Plan, the PLN-14 Software Design Description, and a successful run of the repository CI pipeline. Product performance and clean-machine installation targets remain separately measurable acceptance targets.

## 3. Scope

### 3.1 In scope

- Requirements definition, project planning, and risk management.
- Project/release/requirement catalog management.
- Requirement-to-test-case traceability.
- User authentication and role-based authorization.
- Defect creation, allowed state transitions, and append-only history.
- Basic execution/pass metrics.
- Test Plan and design documentation.
- Backend/frontend quality checks and PostgreSQL-backed CI verification.
- Docker Compose local development environment.

### 3.2 Out of scope or not yet in the current baseline

- Production hosting, production credentials, and live customer operation.
- Commercial service-level commitments or operational support.
- A separate independent verification organization; the four-person academic team uses peer review and a QA/DevOps role.
- Complete implementation of PDF/HTML Test Plan and Test Summary Report generation.
- Application-level JUnit/Cobertura result import and automatic mapping of imported results.
- Any standard conformance claim that requires clause-level validation against licensed full standard texts not reviewed by the team.

## 4. Delivery approach and life-cycle tailoring

The team follows an iterative, incremental approach. Work is divided into named work packages and plan items. Each change is tied to a `WP-xx` or `PLN-xx` identifier, developed on a task-specific branch, and submitted through a pull request. Review and automated checks provide team-level verification.

The tailoring described in the project midterm is retained: requirements definition, planning, documentation, implementation, verification, and configuration/change control are applied. Acquisition, supply, and live operation processes are not part of this academic project because there is no external customer or production service. Independent verification is replaced by peer review and the assigned QA/DevOps role. The team initially prioritizes a limited IEEE 829-style document set (especially Test Plan and Test Summary Report) and maps it by purpose to the current 29119 framework; no one-to-one equivalence is claimed.

For current standard status and the distinction between the 12207 life-cycle reference and the 29119 testing framework, see `docs/standard-status-and-mapping.md`. The instructor's decision on whether the course baseline explicitly uses ISO/IEC/IEEE 12207:2026 or an earlier edition remains an open confirmation item.

## 5. Team organization and responsibilities

| Team member | Role stated in Progress Report #1 | Main responsibilities stated in the report |
|---|---|---|
| Emirhan Ulutürk | Product owner / requirements and documentation | WP-01 requirements set, WP-02 standards analysis, WP-03 tool-analysis contribution, WP-08 roadmap and risk register, WP-12 README/progress report; PLN-02, PLN-03, and joint PLN-14. |
| Caner Serbest | Backend lead | WP-04 defect workflow, WP-05 core model/technology contribution, WP-09 demo backend; PLN-04, PLN-05, PLN-06, PLN-07, PLN-15. |
| Emirhan Canarslan | Frontend lead | WP-03 tool-analysis contribution, WP-06 metrics, WP-10 demo frontend; PLN-08, PLN-09, PLN-10. |
| Esra Kaya | QA and DevOps | WP-05 technology/deployment contribution, WP-07 CI and result-import design, WP-11 repository/local environment; PLN-11, PLN-12, PLN-13, and joint PLN-14. |

The task assignments above reproduce the project progress report. They do not transfer another member's individual plan items to the current author.

## 6. Work breakdown and plan-item schedule

### 6.1 Completed initial work packages (Progress Report #1)

| Work package | Output | Owner(s) stated in report |
|---|---|---|
| WP-01 | Initial R1–R8 requirement set derived from the assignment brief | Emirhan Ulutürk |
| WP-02 | Standards and legacy/current testing-documentation analysis | Emirhan Ulutürk |
| WP-03 | Tool and gap analysis | Emirhan Canarslan, Emirhan Ulutürk |
| WP-04 | Defect lifecycle and transition-rule design | Caner Serbest |
| WP-05 | Technology stack, logical architecture, core model, security approach | Caner Serbest, Esra Kaya |
| WP-06 | Test coverage/success metric catalogue and release-gate proposal | Emirhan Canarslan |
| WP-07 | Test-document and CI/result-import approach | Esra Kaya |
| WP-08 | Seven-sprint roadmap proposal, team roles, risk register | Emirhan Ulutürk |
| WP-09 | Demo backend | Caner Serbest |
| WP-10 | Demo frontend | Emirhan Canarslan |
| WP-11 | Repository structure, local development setup, smoke tests | Esra Kaya |
| WP-12 | README and Bi-Weekly Progress Report #1 | Emirhan Ulutürk |

### 6.2 Plan items and target dates from the report

| Plan item | Planned output | Owner(s) | Target date | Repository evidence/status checked 11 Nov 2026 |
|---|---|---|---|---|
| PLN-01 | Standards mapping verification | Emirhan Ulutürk | 06.11.2026 | PR #4 merged. |
| PLN-02 | SRS, Project Plan, Definition of Done, and risk register based on R1–R8 | Emirhan Ulutürk | 13.11.2026 | This documentation package. |
| PLN-03 | Test Plan draft for the demo scope | Emirhan Ulutürk | 13.11.2026 | This Test Plan. |
| PLN-04 | PostgreSQL schema, SQLAlchemy models, Alembic migration | Caner Serbest | 06.11.2026 | PR #2 merged. |
| PLN-05 | JWT authentication and role-based access | Caner Serbest | 13.11.2026 | PR #6 merged. |
| PLN-06 | Project/release/requirement CRUD and traceability | Caner Serbest | 13.11.2026 | PR #8 merged. |
| PLN-07 | Database-backed defect transitions and role constraints | Caner Serbest | 13.11.2026 | PR #7 merged. |
| PLN-08 | Shared UI components, validation, and error messages | Emirhan Canarslan | 06.11.2026 | PR #5 merged. |
| PLN-09 | React Router pages and project/requirement screens | Emirhan Canarslan | 13.11.2026 | No status inferred in this document. |
| PLN-10 | Defect detail page and history timeline | Emirhan Canarslan | 13.11.2026 | No status inferred in this document. |
| PLN-11 | Initial GitHub Actions CI checks | Esra Kaya | 06.11.2026 | PR #1 merged; workflow currently runs. |
| PLN-12 | Docker Compose for backend, frontend, PostgreSQL | Esra Kaya | 13.11.2026 | PR #9 merged. |
| PLN-13 | Backend tests and Cobertura CI coverage | Esra Kaya | 13.11.2026 | PR #10 merged. |
| PLN-14 | Design document (architecture and data model) and first successful CI pipeline | Emirhan Ulutürk, Esra Kaya | 13.11.2026 | SDD is this document package's companion; current CI success is recorded below. |
| PLN-15 | Repository governance, PR template/review and issue/project setup | Caner Serbest | 06.11.2026 | PR #3 merged. |

Target dates and owners are copied from Bi-Weekly Progress Report #1. PR states are based on repository history checked on 11 November 2026; they should be refreshed if the repository changes.

### 6.3 Current CI evidence

The repository's `CI` workflow completed successfully on `main` on 11 November 2026:

- Run ID: `42972187931`
- Conclusion: `success`
- Run: https://github.com/Aoreri/SEN0421/actions/runs/42972187931

The workflow currently contains three jobs: backend checks on the SQLite test setup, backend PostgreSQL tests, and frontend checks. The PLN-14 delivery should reference this evidence rather than claiming that a new workflow was created in this documentation change.

## 7. Project work products

| Work product | Repository path / evidence | Responsible plan item |
|---|---|---|
| SRS | `docs/srs.md` | PLN-02 |
| Project Plan | `docs/project-plan.md` | PLN-02 |
| Definition of Done | `docs/definition-of-done.md` | PLN-02 |
| Risk Register | `docs/risk-register.md` | PLN-02 |
| Test Plan | `docs/test-plan.md` | PLN-03 |
| Software Design Description | `docs/software-design-description.md` | PLN-14 |
| Standards status and mapping | `docs/standard-status-and-mapping.md` | PLN-01 |
| CI evidence | GitHub Actions run linked above | PLN-11 / PLN-13 / PLN-14 evidence |

## 8. Configuration and change management

- `main` is the integration branch. Work is performed on a branch containing the plan item identifier.
- Pull requests must use the repository PR template and identify the plan item and applicable standard.
- The PR description workflow validates the required sections and the `Agent:` line.
- Reviewers should check the relevant requirements, tests, data model, README, and related work products.
- Merged database schema changes are extended by a new Alembic migration; they are not edited retrospectively.
- Generated reports, secrets, `.env` files, and runtime coverage outputs are not committed.

## 9. Monitoring and control

Progress is monitored through plan-item status, pull requests, review comments, CI results, and the two-week progress report. Risks are reviewed during sprint planning and before a release/demo. A change that affects requirements must update the SRS and its test-case traceability; a change to the data model must update the SDD, migration, and tests.

## 10. Acceptance and completion

A plan item is complete when its required work product or code is present, traceable to the item and applicable standard, reviewed through a pull request, and supported by the verification evidence required for that item. The project-level completion checklist is in `docs/definition-of-done.md`.

## 11. References

1. SDS-06 Bi-Weekly Progress Report #1, 30 October 2026.
2. SDS-06 Midterm Questions and Evaluation Guide.
3. `README.md`, `AGENTS.md`, `.github/pull_request_template.md`, `.github/workflows/ci.yml`, and current source/migration files in Aoreri/SEN0421.
4. `docs/standard-status-and-mapping.md` (PLN-01).
