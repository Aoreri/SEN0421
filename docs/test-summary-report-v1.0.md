# SDS-06 — Interim Test Summary Report

**Plan item:** PLN-38  
**Report ID:** TSR-SDS06-2026-11-22  
**Prepared:** 22 November 2026  
**Baseline reviewed:** `main` at `2fef309092999099cce8bb82c08c8014817c70d6`  
**Status:** Interim report; final integrated report must be regenerated after merge/release.

## 1. Purpose and test scope

This interim report summarizes verification evidence available for the SDS-06 integrated baseline and explicitly identified open PR branches. It covers the backend API, database integrity, frontend build, JUnit/Cobertura import, metrics/release gate, Test Plan API, and the next report/security/release increments.

The report distinguishes:

- **Integrated evidence:** tests/features present on `main`.
- **PR evidence:** checks reported successful on a branch that is still under review.
- **Unmeasured target:** a requirement for which no reproducible measurement report was found.

It does not combine test counts from separate branches into a single total because the test suites overlap and the branches have not all been merged together.

## 2. Summary of available verification

| Verification area | Available evidence | Interim result |
|---|---|---|
| Backend API / domain rules | Tests for login, role restrictions, catalogue CRUD, traceability, run/execution behavior, defect lifecycle/history, verification gate, metrics, release gate, imports and Test Plans. | Core integrated behavior has focused API/integration coverage. |
| PostgreSQL integrity | PostgreSQL 16 CI job and append-only `defect_history` test. PR #34 and PR #37 descriptions also report focused PostgreSQL migration/test success on their branches. | Individual evidence exists; complete merged migration chain must be revalidated. |
| Frontend | ESLint, TypeScript typecheck and Vite production build. | Reported passing in CI for the reviewed feature branches. |
| Test Incident Report / Test Log | PLN-39 PR #37 reports 9 focused SQLite and PostgreSQL tests passing. | Branch evidence only; PR remains open. |
| Test Summary Report | PLN-30 PR #38 reports its focused SQLite and PostgreSQL summary-report test passing. | Branch evidence only; PR remains open. |
| Security | PLN-29 PR #39 reports Bandit with zero High/Medium findings and npm audit with zero vulnerabilities. | Branch evidence only; PR remains open. |
| v1.0 release automation | PLN-36 PR #40 adds release workflow and report generator; PR checks reported successful. | Release not yet published; tag workflow still needs to run after integration. |
| Performance / portability | p95 traceability target and clean-machine Compose target are defined. | No measured result found. |
| Final demonstration | Script/shot list prepared. | Actual video recording and link still outstanding. |

## 3. Regression seed-data example (not a production result)

The integrated backend test fixture includes six test cases: three `Passed`, one `Failed`, and two `Not Run`, plus three defects whose status is not `Closed`. The legacy `/api/metrics` regression assertion expects:

| Metric | Fixture result |
|---|---:|
| Total test cases | 6 |
| Executed (`Passed` + `Failed`) | 4 |
| Execution rate | 66.7% |
| Pass rate among decisive executions | 75.0% |
| Non-Closed defects | 3 |

These values are a deterministic seed-fixture check only. They are not measured user/project production data and must not be presented as a release-wide Test Summary Report for a real operational deployment.

## 4. Open issues affecting the release recommendation

1. Complete migration sequencing from the integrated `0010` baseline for all open `0011*` PRs, then run the complete PostgreSQL upgrade/test suite.
2. Merge and verify PLN-29 security hardening; current integrated GET routes include public reads.
3. Verify WeasyPrint in the supported container and inspect multi-page Test Plan/Incident/Log/Summary PDFs.
4. Implement and measure the FR-REQ-02 release-specific traceability result and NFR-REQ-01 p95 target.
5. Record clean-machine Compose startup time for NFR-REQ-02.
6. Merge report and release PRs, run the release workflow, and inspect the generated assets.
7. Record the final demonstration video and insert its shareable URL.

## 5. Interim release recommendation

**Recommendation: conditional / not yet final acceptance.** The integrated baseline has meaningful test evidence and the individual feature PRs report green checks, but the project should not be declared fully complete until migration integration, security review, document rendering, required measurements, final release artifacts, and the demonstration recording are complete.

## 6. References

- Current CI workflow: `.github/workflows/ci.yml`.
- Automated test source: `backend/tests/`.
- SRS v1.0, SDD v1.0, RTM v2, ISO/IEC 25010 evaluation, IEEE 1012 V&V results.
- Relevant open PRs: [#34 PLN-28](https://github.com/Aoreri/SEN0421/pull/34), [#37 PLN-39](https://github.com/Aoreri/SEN0421/pull/37), [#38 PLN-30](https://github.com/Aoreri/SEN0421/pull/38), [#39 PLN-29](https://github.com/Aoreri/SEN0421/pull/39), [#40 PLN-36](https://github.com/Aoreri/SEN0421/pull/40), [#41 PLN-31](https://github.com/Aoreri/SEN0421/pull/41).
