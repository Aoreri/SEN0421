# SDS-06 — Requirements Traceability Matrix (RTM) v1

**Plan item:** PLN-25  
**Version:** 1.0 — Draft for team review  
**Prepared:** 18 November 2026  
**Related documents:** `docs/srs.md`, `docs/test-plan.md`, `docs/software-design-description.md`, `docs/metric-definitions.md`

## 1. Purpose and traceability rules

This matrix connects the requirements visible in the inspected project materials to design components and verification evidence. It is a first version for review, not a claim that the original detailed R1–R8 specification has been recovered.

The current repository's seed migration inserts R1–R8 with placeholder titles and empty descriptions. The seed associations are TC-001 and TC-002 → R1, TC-003 → R3, TC-004 → R4, TC-005 → R6, and TC-006 → R7. There is no seed association for R2, R5, or R8. The exact original R1–R8 statements must be checked against the course assignment / original requirements source before the team freezes this matrix.

Status meanings:
- **Current:** behavior is present on `main` and backed by current tests or API evidence.
- **PR in review:** implementation is described by an open pull request and has not yet been treated as merged baseline behavior.
- **Gap / planned:** requirement is known, but the current baseline does not yet satisfy it.
- **Needs source confirmation:** original requirement wording is not available in the inspected repository materials.

## 2. R1–R8 traceability

| Requirement ID | Project-plan-derived area (provisional until original R text is confirmed) | SDD component / data | Verification specification / evidence | Status |
|---|---|---|---|---|
| R1 | Test Plan / test-document control. PLN-26 is explicitly associated with R1 and R3. | Test Plan Service, `test_plans`, `test_plan_snapshots`, Jinja2 renderer. | WFT-08 and WFT-09 in `docs/test-case-specification-workflow.md`; existing seed links TC-001 and TC-002 must be checked against their full titles before claiming detailed coverage. | PR #26 in review; seed link exists, detailed original wording needs confirmation. |
| R2 | Test-case and test-suite management, requirement traceability, and test execution. PLN-16, PLN-17, PLN-19, and PLN-20 are associated with R2. | Test Suite / Test Case Service, `test_suites`, `test_cases`, `test_case_requirements`, Test Run / Execution Service. | WFT-01 through WFT-05; existing seed migration has no R2-linked test case. | PRs #21, #22, #25 in review; test automation and exact R2 source statement need confirmation. |
| R3 | Test Plan / test-document generation. PLN-26 is explicitly associated with R1 and R3. | Test Plan Service, snapshot and HTML/PDF export. | WFT-08 and WFT-09; seeded association TC-003 → R3. | PR #26 in review; full R3 wording needs confirmation. |
| R4 | Defect lifecycle and verification before closure. PLN-17 and PLN-20 are associated with R4. | Defect Service, `defects`, `defect_history`, `test_executions`, `execution_defects`. | WFT-06; seeded association TC-004 → R4; existing defect lifecycle tests are in `backend/tests/test_api.py` and `backend/tests/test_integration.py`. | Existing lifecycle current; verification-execution gate is in PR #25. |
| R5 | Test metrics, monitoring, dashboard and metric aggregation. PLN-21 and PLN-24 are associated with R5. | Metrics Service, `GET /api/metrics`, planned aggregation queries and dashboard charts. | MET-01 through MET-06 in `docs/metric-definitions.md`; WFT-10. | Basic metrics current; expanded SQL metrics / dashboard work must be checked against open PRs and the assigned PLN-24 work. |
| R6 | Automated test-result import and coverage/result traceability. PLN-22 and PLN-23 are associated with R6. | JUnit importer, `imported_test_runs`, `imported_test_results`, future Cobertura importer. | Existing `backend/tests/test_junit_parser.py` and `backend/tests/test_junit_import.py`; WFT-11. | JUnit import current on `main`; Cobertura ingestion remains planned. Seed association TC-005 → R6. |
| R7 | Release lifecycle and exit criteria. PLN-18 and PLN-21 are associated with R7. | Release Service, release status, gate criteria and waiver fields. | WFT-07; seeded association TC-006 → R7. | PR #27 in review; full R7 wording needs confirmation. |
| R8 | Original requirement statement is not present in the inspected migration / SRS source. The current SRS separately documents authentication, role checks, and append-only defect history, but those facts do not prove R8's exact intent. | Authentication / RBAC, defect history and PostgreSQL integrity controls are current design areas. | Existing auth, role and append-only history tests; map to R8 only after the original R8 text is confirmed. | Needs source confirmation; do not claim an R8-to-test mapping yet. |

## 3. Explicit midterm requirements and quality targets

| SRS requirement | Requirement statement (preserved from the midterm) | Design component | Verification ID / method | Current status |
|---|---|---|---|---|
| FR-REQ-01 | Every test case must be linked to at least one requirement; a test case without a requirement must be rejected with HTTP 422. | Test Case Service and `test_case_requirements`. | WFT-02; API negative test for an empty requirement list. | The PLN-16 PR #21 proposes this validation; it is not yet a merged-main claim. |
| FR-REQ-02 | For a selected release, show each requirement's linked test-case count and the Passed, Failed, and Not Run counts. | Traceability / Metrics Service. | WFT-03 and an acceptance query using a known fixture. | Gap in the inspected current baseline; a release-specific report must be implemented and measured. |
| NFR-REQ-01 | With 200 requirements and 1,000 test cases, the traceability report shall be produced within 2 seconds at p95 in local Docker Compose. | Metrics / query layer. | Performance test with 200 requirements and 1,000 linked cases; capture p95 over a documented repeated sample. | Target only; no measured evidence found. |
| NFR-REQ-02 | On a clean machine with prerequisites, backend, frontend and PostgreSQL shall start in one `docker compose up` command within 10 minutes. | Docker Compose deployment. | Clean-machine installation demonstration; record elapsed time and manual steps. | Target only; no clean-machine measurement found. |

## 4. Cross-cutting verification coverage

| Concern | Test / evidence | SRS / design link |
|---|---|---|
| Authentication and role authorization | Login tests, invalid-token tests, role-denied mutation tests. | FR-AUTH-01/02/03; `auth.py` and role dependencies. |
| Requirement traceability | M:N link reads/writes; unknown IDs rejected; required-link validation in PLN-16 branch. | FR-TRACE-01/02, FR-REQ-01. |
| Defect workflow | Allowed and denied state transitions; immutable history; passed-verification gate before closure. | FR-DEF-01/02/03, R4. |
| Metrics | Seed fixture formula checks, zero-denominator checks, release gate thresholds. | FR-MET-01, NFR-REQ-01, R5/R7. |
| JUnit import | XML parser boundaries, stable-key mapping, unmatched result persistence and report. | FR-IMP-01, R6. |
| Test Plan lifecycle and output | Draft / In Review / Approved transitions, duplicate version rejection, snapshot and HTML/PDF output checks. | FR-PLAN-01/02, R1/R3. |

## 5. Open traceability actions

1. Replace placeholder R1–R8 descriptions with the exact approved requirement wording from the original course/project source.
2. Confirm the R8 intent and map it only when evidence supports the mapping.
3. Link each WFT verification specification to its eventual automated test name / CI result after its implementation PR is merged.
4. Add the release-specific FR-REQ-02 report and its measured performance evidence when delivered.
5. Reconcile `test_cases.requirement` legacy values with the many-to-many `test_case_requirements` relation during the integration review; do not remove the legacy field without compatibility checks.
