# SDS-06 — Project Retrospective

**Plan item:** PLN-38  
**Prepared:** 22 November 2026  
**Review point:** After the November sprint increments; before final v1.0 acceptance.

## 1. What worked well

- Work was decomposed into plan items with named owners, dates, branches, and pull requests.
- Backend API contracts, frontend TypeScript client, SQLAlchemy models, and Alembic migrations were generally kept in separate layers.
- Stable test-case identifiers and requirement links made automated JUnit import and traceability possible.
- API/integration tests covered meaningful negative cases such as role denial, invalid transitions, duplicate versions, invalid cross-project references, and atomic import failures.
- PostgreSQL-specific testing was used for append-only defect-history behavior instead of relying on SQLite alone.
- CI checks made lint, type checking, backend tests, PostgreSQL tests, and frontend build evidence visible on pull requests.
- Documentation work products (SRS, SDD, Test Plan, RTM, metric definitions, workflow test specification) were kept under version control as Markdown source.

## 2. What was difficult

- Several parallel feature branches introduced Alembic revisions with the same next revision number. Each branch could be tested independently, but the combined migration history requires an explicit integration order and unique sequential IDs.
- The original R1–R8 descriptions were not fully available in the repository. Some mappings remain provisional and must be confirmed against the approved course source.
- A passing API response with a PDF content type/signature did not by itself prove that the intended renderer and page layout work in the target container.
- Performance and clean-machine installation targets were stated as measurable requirements but were not yet accompanied by reproducible measurement reports.
- The integrated baseline and the contents of open PR branches needed to be distinguished carefully to avoid describing planned or in-review behavior as a released feature.
- The final demonstration video was recorded from an actual application session; the script alone would not have been a video artifact.

## 3. Improvement actions

| ID | Improvement | Action / expected evidence | Priority |
|---|---|---|---|
| RET-01 | Migration coordination | Merge schema PRs in an agreed order; assign unique revisions from `0011`; run the full Alembic upgrade on disposable PostgreSQL 16. | Critical |
| RET-02 | Requirements baseline | Obtain the original R1–R8 text and confirm each mapping with the course owner. | High |
| RET-03 | PDF quality assurance | Install/verify the intended renderer in Docker; generate multi-page outputs; inspect content and layout for all report types. | High |
| RET-04 | Performance evidence | Implement/confirm FR-REQ-02; benchmark 200 requirements and 1,000 test cases; publish repeated samples and p95. | High |
| RET-05 | Portability evidence | Perform a clean-machine Compose startup and record time/prerequisites/manual steps. | High |
| RET-06 | Security hardening | Complete read-endpoint authorization review and security scans; record findings and remediation. | High |
| RET-07 | Final demonstration | Record a reproducible end-to-end walkthrough, upload it to the agreed location, and insert the link in the final report. | High |
| RET-08 | Integrated acceptance | After merge, run complete backend, PostgreSQL, frontend and release checks on the exact release commit. | Critical |

## 4. Action ownership

Use the current post-report work allocation for the owners of each technical action. Documentation/traceability and final delivery evidence are coordinated by the documentation owner; API and database corrections by the backend owner; UI work by the frontend owner; and test/DevOps verification by the QA/DevOps owner. The team should confirm individual assignments before closing the actions.

## 5. Retrospective conclusion

The project established a substantial feature and verification baseline, but final completion depends on integrated migration verification, security closure, document-renderer inspection, measurement evidence, and a recorded demo. The team should not mark the v1.0 release complete solely because each individual feature branch has green CI.
