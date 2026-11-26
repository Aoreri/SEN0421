# SDS-06 — Final Project Deliverable Report (Draft for Report #4)

**Plan item:** PLN-38  
**Project:** SDS-06 — Agile Test and Defect Tracking System  
**Prepared:** 22 November 2026  
**Target project completion:** 26 November 2026  
**Target report submission:** 27 November 2026  
**Status:** Draft; final merge/release/video evidence must be inserted before submission.

## Executive summary

SDS-06 is a web-based system for requirements traceability, test planning, test execution, defect lifecycle management, release criteria, imports, metrics, and test documentation. The integrated codebase provides a React/TypeScript frontend, FastAPI backend, SQLAlchemy/Alembic persistence layer, PostgreSQL 16 database, Docker Compose environment, and GitHub Actions verification pipeline.

The project has a substantial integrated baseline: project/release/requirement management, test suites and test cases, many-to-many traceability, interactive Test Runs and Executions, defect transitions and history, execution-based defect closure verification, expanded metrics, release gate controls, JUnit/Cobertura imports, and versioned Test Plan API/snapshots/exports. Additional work for Test Incident Reports, Test Logs, Test Summary Reports, security hardening, sprint filtering, Test Plan UI, and v1.0 release automation is represented by open PRs and must not be treated as integrated until merged.

**Interim conclusion:** The project is not yet ready for unconditional final acceptance. The migration chain, PDF renderer, required performance/clean-machine measurements, final release workflow, and demo video remain explicit closure items.

## 1. Project scope and delivered system

The application supports four roles: Admin, Test Lead, Tester, and Developer. It manages project data and test assets, preserves requirement links, records execution outcomes, associates failures with defects, enforces server-side lifecycle rules, and reports test/release metrics.

### 1.1 Integrated features on `main`

- JWT-based login and role-based protection of write/workflow operations.
- Project, release, and requirement catalogue CRUD.
- Test Suite and Test Case CRUD, ordered steps, expected result, priority, automation flag, stable IDs, and requirement links.
- Test Run and Test Execution lifecycle with Passed/Failed/Blocked/Skipped outcomes and execution-defect links.
- Defect lifecycle, append-only history, and Passed-verification requirement before `Resolved → Closed` for a linked case.
- Base and expanded SQL metrics, dashboard charts, release statuses, configurable exit criteria, and waiver records.
- JUnit XML import with stable-key mapping and unmatched-result reporting; Cobertura coverage import.
- Versioned Test Plan records, `Draft/In Review/Approved` workflow, snapshots, and HTML/PDF API exports.

### 1.2 Features awaiting integration/release

| Work | Evidence | Current disposition |
|---|---|---|
| Sprint entity and sprint metrics filter | PLN-28, PR #34 | Open PR. |
| Test Incident Report and Test Log generation | PLN-39, PR #37 | Open PR. |
| Test Summary Report generation | PLN-30, PR #38 | Open PR. |
| Read-endpoint authentication and security scans | PLN-29, PR #39 | Open PR. |
| v1.0 release workflow and report attachments | PLN-36, PR #40 | Open PR; no release tag/asset claim yet. |
| Test Plan management UI | PLN-31, PR #41 | Open PR. |

## 2. Verification summary

The detailed records are in `ieee-1012-verification-results.md` and `test-summary-report-v1.0.md`. The current evidence includes API/integration coverage for catalogue, traceability, execution, defects, metrics, release gate, imports, and Test Plan behavior; PostgreSQL 16 history-integrity tests; and frontend lint/typecheck/build checks.

The reviewed open feature PR branches report successful CI checks. Their individual test counts are not added together because test suites overlap and the branches have not all been verified as one integrated build. The combined integrated mainline must be tested again after the PRs merge and Alembic revisions are sequenced.

## 3. ISO/IEC 25010 product quality evaluation

The project-level quality assessment is in `iso-25010-quality-evaluation.md`. ISO/IEC 25010:2023's nine product-quality characteristics are considered. Functional suitability, reliability, maintainability, and parts of flexibility have useful implementation/test evidence. Performance efficiency, installability, PDF rendering quality, and security hardening require additional measurements or integration work. The evaluation is an evidence-based project assessment, not a certification claim.

## 4. IEEE 1012 verification and validation

The verification register is in `ieee-1012-verification-results.md`. It records requirements/design review, static analysis, backend tests, PostgreSQL integration, frontend build, imports, document generation, and known gaps. The current status is conditional: integrated migration verification, target-container PDF inspection, performance/clean-machine measurements, and a recorded demo remain outstanding.

## 5. Standards alignment

`standards-compliance-checklist.md` maps the project to ISO/IEC/IEEE 12207, ISO/IEC/IEEE 29148:2018, IEEE 1016, ISO/IEC/IEEE 29119-2/-3, legacy IEEE 829 artefact naming, IEEE 1012-2024, and ISO/IEC 25010:2023. The mapping is tailored to the academic scope and does not assert formal conformance to all clauses.

## 6. Retrospective

The team established useful task decomposition, typed API boundaries, migration-driven persistence, traceability, negative API tests, PostgreSQL-specific integrity tests, and CI evidence. The main integration challenges were parallel migration numbering, incomplete original R1–R8 source wording, PDF renderer/target-container verification, and the difference between a green feature branch and the combined release baseline.

The improvement actions and follow-up owners are listed in `retrospective.md`.

## 7. Final demonstration video

**Recording status:** Recorded from the integrated application following `demo-video-script.md` and published on the team's demo site.

## 8. Final acceptance checklist

- [ ] All required open PRs reviewed and merged to `main`.
- [ ] Alembic migrations form one unique, linear chain starting at the current `0010` baseline; PostgreSQL 16 `alembic upgrade head` passes.
- [ ] Backend Ruff, mypy, pytest, PostgreSQL tests, frontend lint, typecheck, and build pass on the integrated release commit.
- [ ] Read-endpoint auth/security work is integrated and scan evidence is attached.
- [ ] Test Incident Report, Test Log, Test Summary Report, and Test Plan PDFs are generated and visually inspected in the supported container.
- [ ] FR-REQ-02 and NFR-REQ-01 performance evidence is complete or formally accepted as a documented deviation.
- [ ] NFR-REQ-02 clean-machine Compose timing is recorded or formally accepted as a documented deviation.
- [ ] v1.0.0 tag, GitHub Release, Docker images, and report attachments exist (after release workflow execution).
- [x] Demo video is recorded and published on the demo site.
- [ ] Original R1–R8 wording is confirmed and the RTM is approved.

## 9. Report references

- `srs.md` — SRS v1.0.
- `software-design-description.md` — SDD v1.0.
- `requirements-traceability-matrix-v2.md` — RTM v2.
- `installation-and-user-guide.md` — installation and usage.
- `iso-25010-quality-evaluation.md` — product quality evaluation.
- `ieee-1012-verification-results.md` — verification/validation evidence.
- `standards-compliance-checklist.md` — standards mapping.
- `retrospective.md` — lessons and actions.
- `demo-video-script.md` — final video storyboard and recording checklist.
- `test-summary-report-v1.0.md` — interim Test Summary Report.
