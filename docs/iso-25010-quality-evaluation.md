# SDS-06 — ISO/IEC 25010:2023 Product Quality Evaluation

**Plan item:** PLN-38  
**Prepared:** 22 November 2026  
**Baseline:** Integrated `main` reviewed 22 November 2026; open PR evidence is labelled separately.

## 1. Evaluation basis

This evaluation uses the product quality model in ISO/IEC 25010:2023 (Edition 2, published November 2023). The 2023 model defines nine product-quality characteristics. It replaces the 2011 edition, which ISO lists as withdrawn. This is a project-level evidence-based assessment, not a formal ISO certification or a full normative conformity assessment.

The model characteristics used below are: functional suitability, performance efficiency, compatibility, interaction capability, reliability, security, maintainability, flexibility, and safety.

## 2. Quality evaluation matrix

| Characteristic | SDS-06 interpretation and acceptance evidence | Current evidence | Evaluation |
|---|---|---|---|
| Functional suitability | Project/release/requirement management; test suites/cases and traceability; execution; defect lifecycle; metrics; release gate; Test Plan lifecycle and exports. | API integration tests cover catalogue CRUD, mandatory requirement links, test execution, defect transitions/verification gate, metrics, release gate, JUnit/Cobertura imports, and Test Plan CRUD/snapshots. Core features are in `main`. | **Substantially evidenced, with gaps.** FR-REQ-02 (release-specific requirement outcome report) remains missing; Incident/Log and Test Summary Report generators are in open PRs #37/#38. |
| Performance efficiency | p95 response/report generation under the required workload of 200 requirements and 1,000 test cases; target is at most 2 seconds for the traceability report. | The API/SQL metric tests verify functional correctness and scoping, but no repeatable benchmark report with sample distribution and p95 was found. | **Not measured.** Do not claim the performance target is met. |
| Compatibility | Operation across the supported browser/container stack; HTTP/JSON API boundaries; PostgreSQL 16 backend; JUnit/Cobertura import formats. | Docker Compose defines PostgreSQL 16, backend, and frontend; CI uses Python 3.12, Node.js 22, PostgreSQL 16. Parser tests cover JUnit and Cobertura XML inputs. | **Partially evidenced.** Browser matrix and interoperability against external CI producers are not documented as a complete compatibility campaign. |
| Interaction capability | Clear navigation, validation/error messages, traceability visibility, execution workflow, role-aware actions, and accessible interaction. | React/TypeScript pages exist for dashboard, projects/requirements, test cases/matrix, test runs, defects, and login. ESLint, TypeScript typecheck, and production build checks pass on the reported PR branches. | **Partially evidenced.** No formal accessibility/usability study or WCAG evaluation is recorded; Test Plan management UI is in PR #41. |
| Reliability | Correct state transitions, transactional imports, no partial writes on invalid data, append-only defect history, repeatable migrations. | Integration tests cover rejected operations leaving state/history unchanged, atomic JUnit imports, lifecycle behavior, and PostgreSQL history immutability. | **Substantially evidenced.** Final combined-stack migration verification remains required after all open migration PRs are sequenced. |
| Security | Password hashing, token integrity/expiry, authorization checks, protected operations, dependency/static scanning, secret handling. | bcrypt password hashing, signed eight-hour JWTs, and write/transition role checks are integrated. Read-endpoint authentication, Bandit, and npm audit hardening are in PR #39. Public demo credentials and local DB defaults are documented as demo-only. | **Partially evidenced / integration pending.** Do not describe the current integrated baseline as production-safe. |
| Maintainability | Layer separation, typed API client, automated lint/type/test/build pipeline, migration discipline, documentation. | Backend modules, frontend API client, SQLAlchemy/Alembic, and CI are separated. Reported PR checks include Ruff, mypy, pytest, npm lint, typecheck, and build. | **Substantially evidenced.** Migration sequencing and full integrated regression remain pending. |
| Flexibility | Support additional projects, releases, suites, requirements, cases, roles, metrics scopes, and configurable release gate criteria. | Project/release/suite/case entities, many-to-many traceability, scoped metrics, and configurable release criteria/waivers are implemented. | **Partially to substantially evidenced.** Sprint-based metric filtering is in PR #34 and not yet integrated. |
| Safety | Evaluate whether incorrect behavior can create a safety hazard or physical harm; document operational constraints where relevant. | SDS-06 is an academic test-management web application with no identified direct physical-control or safety-critical interface. Data loss, incorrect release decisions, and overclaiming test evidence remain project risks. | **Not safety-critical by intended scope; residual operational risks documented.** This is not a hazard analysis for a safety-certified system. |

## 3. Cross-cutting interpretation

- The evaluation uses evidence that exists in the repository or in explicitly identified open PRs. Open-PR evidence is not treated as integrated release evidence.
- “Partially evidenced” means that design/code/tests exist but a named measure, runtime demonstration, or integration step remains.
- Test success is evidence for the tested behavior only; it is not proof of all quality subcharacteristics.
- The seed metrics sample (six cases: three Passed, one Failed, two Not Run; three non-Closed defects) is a regression fixture, not a measurement of a real production workload.

## 4. Required follow-up measurements

| ID | Measurement / action | Acceptance target | Owner / dependency | Evidence required |
|---|---|---|---|---|
| Q-01 | Generate the release-specific traceability result for 200 requirements and 1,000 test cases; repeat enough samples to report p95. | p95 ≤ 2 seconds. | Backend/report implementation; FR-REQ-02. | Raw timings, dataset description, p95 calculation, environment. |
| Q-02 | Start the application on a clean machine using the documented Compose command. | One `docker compose up` flow reaches healthy frontend/backend/database within 10 minutes. | Documentation/QA. | Machine/OS/Docker versions, start/end timestamps, manual interventions. |
| Q-03 | Generate multi-page Test Plan, Incident Report, Test Log, and Test Summary Report PDFs in the supported container. | PDF opens, all expected sections/pages are present, content matches snapshot HTML. | Report PRs #37/#38 and Test Plan #26. | PDF artifacts, page inspection checklist, renderer/dependency versions. |
| Q-04 | Complete the security scan and read-endpoint authorization checks. | No unresolved High/Critical findings; intended endpoints return 401/403 as specified. | PLN-29 PR #39. | Bandit output, npm audit output, API authorization test output. |
| Q-05 | Re-run all checks after migration integration. | Single Alembic chain upgrades to head on PostgreSQL 16; all backend/frontend jobs pass. | Integration owner; all open schema PRs. | Migration history and CI run URL. |

## 5. References

1. ISO/IEC 25010:2023, *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — Product quality model*, Edition 2, published November 2023. [Official ISO catalogue](https://www.iso.org/standard/78176.html).
2. SDS-06 SRS v1.0, SDD v1.0, RTM v2, CI workflow, test suites, and open pull requests in `Aoreri/SEN0421` (reviewed 22 November 2026).
