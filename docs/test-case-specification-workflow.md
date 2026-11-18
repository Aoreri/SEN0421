# SDS-06 — Workflow Test Case Specification

**Plan item:** PLN-27  
**Document type:** IEEE 829 Test Case Specification (course-facing document name)  
**Version:** 1.0 — Draft for team review  
**Prepared:** 18 November 2026  
**Test suite identifier:** `SDS06-WORKFLOW`  
**Test basis:** SRS v0.2, Test Plan v0.2, RTM v1, and the November PLN-16/17/18/26 feature branches

> These are planned, repeatable acceptance specifications. They are not a claim that every case has already been automated or executed. The `Actual result` and `Status` fields are intentionally left for the tester to complete during a run.

## 1. Test suite overview

The suite verifies the end-to-end test-management workflow: author test suites and cases, preserve requirement traceability, create a test run, record execution outcomes, open and verify defects, evaluate release exit criteria, and create/export a versioned Test Plan. It also includes basic metric regression and automated JUnit import checks.

**Execution preconditions:** use a disposable PostgreSQL test database with the approved Alembic chain; use the role-specific demo/test accounts from the repository; load the known seed dataset; and run the PRs only after their dependencies are integrated. See the migration sequencing warning in the updated SDD.

### 1.1 Result vocabulary

| Status | Meaning |
|---|---|
| Not Run | Test case has not yet been executed in the selected Test Run. |
| Passed | Actual result satisfies the expected result. |
| Failed | Actual result does not satisfy the expected result. |
| Blocked | The test cannot proceed because a prerequisite or dependency is unavailable. |
| Skipped | The test was intentionally not attempted for a documented reason. |

## 2. Test cases

### WFT-01 — Create and manage a project-scoped Test Suite

| Field | Specification |
|---|---|
| Objective | Verify suite CRUD, project ownership, uniqueness and deletion constraints. |
| Priority | High |
| Requirement link | R2 (provisional; confirm original wording) |
| Preconditions | A project exists; a Test Lead or Admin account is available. |
| Test data | Project ID `1`; suite name `Workflow Acceptance`; description `SDS-06 workflow suite`. |
| Steps | 1. POST `/api/test-suites` with the project, name and description. 2. GET the created suite and GET the suite list. 3. PUT the name/description. 4. Create a duplicate suite with the same project/name. 5. Attempt to delete the suite while a test case is attached. 6. Remove/reattach cases as permitted and delete an empty suite. |
| Expected result | Create returns 201; detail/list show the same project and suite data; update persists; duplicate name returns 409; a suite with attached test cases is not deleted (409); an empty suite can be deleted (204). |
| Actual result / status | To be recorded during execution. |

### WFT-02 — Create a fully specified Test Case with mandatory requirement link

| Field | Specification |
|---|---|
| Objective | Verify stable ID and the IEEE 829-style test-case specification fields. |
| Priority | High |
| Requirement link | R2; FR-REQ-01 |
| Preconditions | Project and a valid requirement exist; suite created by WFT-01; Test Lead / Tester identity available. |
| Test data | ID `WFT-CASE-001`; priority `High`; `automated=false`; steps `Open the test page`, `Submit valid data`; expected result `The record is saved and displayed`; requirement `R2` or another approved requirement for the test project. |
| Steps | 1. POST `/api/test-cases` with the stable ID, suite, title, priority, automation flag, ordered steps, expected result and a non-empty requirement array. 2. GET the created case. 3. Attempt creation with an empty requirements array. 4. Attempt creation with an unknown requirement ID. 5. Attempt a duplicate stable case ID. |
| Expected result | Valid case returns 201 and preserves all fields and links; an empty requirement list returns 422; an unknown requirement returns 404/422 according to the final API contract; duplicate ID is rejected without altering existing data. |
| Actual result / status | To be recorded during execution. |

### WFT-03 — Verify many-to-many requirement traceability

| Field | Specification |
|---|---|
| Objective | Verify a requirement can link to multiple test cases and a test case can link to multiple requirements without dangling links. |
| Priority | High |
| Requirement link | R2; FR-REQ-01 / FR-REQ-02 |
| Preconditions | At least two requirements and two test cases exist in the same project. |
| Test data | Requirements `R2` and `R4`; cases `WFT-CASE-001` and `WFT-CASE-002` (use valid project records). |
| Steps | 1. Assign both cases to R2. 2. Assign WFT-CASE-001 to R4 as well. 3. GET both requirements and both cases. 4. Attempt to link a nonexistent case. 5. Attempt a cross-project link if the API supports project separation. |
| Expected result | R2 returns both case IDs; R4 returns WFT-CASE-001; WFT-CASE-001 returns both requirement IDs; unknown/cross-project links are rejected and no partial invalid relationship is persisted. |
| Actual result / status | To be recorded during execution. |

### WFT-04 — Create a Test Run and initialize execution rows

| Field | Specification |
|---|---|
| Objective | Verify project/release scope and one `Not Run` execution row per selected case. |
| Priority | High |
| Requirement link | R2 (provisional) |
| Preconditions | A project, optional release, suite and at least two cases exist; Tester or Test Lead identity available. |
| Test data | Run name `SDS-06 Workflow Demo Run`; project ID `1`; selected cases WFT-CASE-001 and WFT-CASE-002. |
| Steps | 1. POST `/api/test-runs` with project, optional release/suite and selected case IDs. 2. GET the run detail. 3. Confirm each selected case appears once. 4. Attempt to include a case from another project or a nonexistent ID. |
| Expected result | A valid run is created; one execution row per selected case has status `Not Run`; run and execution records are persisted; invalid scope or missing case is rejected without partial run data. |
| Actual result / status | To be recorded during execution. |

### WFT-05 — Record all supported execution outcomes

| Field | Specification |
|---|---|
| Objective | Verify execution result, notes, actual result, executor/time and synchronization with case status. |
| Priority | High |
| Requirement link | R2 / R4 (provisional) |
| Preconditions | A run with `Not Run` execution rows exists. |
| Test data | Four execution records, one each for `Passed`, `Failed`, `Blocked`, and `Skipped`; add `actual_result`, `notes`, and the current Tester identity. |
| Steps | 1. Record each outcome through POST/PUT `/api/test-runs/{run_id}/executions/{execution_id}`. 2. GET the run detail. 3. GET test cases and metrics. 4. Verify executor and `executed_at` are present for recorded results. |
| Expected result | Each execution stores the selected status and metadata; the corresponding case status is synchronized as specified by the API; run details show all four outcome counts; no `Not Run` row is reported as completed. |
| Actual result / status | To be recorded during execution. |

### WFT-06 — Open a defect from a failed execution and enforce verification before closure

| Field | Specification |
|---|---|
| Objective | Verify the execution-to-defect link and the `Resolved → Closed` successful-verification rule. |
| Priority | Critical |
| Requirement link | R4 |
| Preconditions | WFT-04 and WFT-05 completed; a Failed execution is available; Admin / Developer / Tester identities are available as required by the transition rules. |
| Test data | Failed execution for WFT-CASE-001; defect title `Workflow verification failure`; severity `High`. |
| Steps | 1. POST `/api/test-runs/{run_id}/executions/{execution_id}/defects` to create a defect from the failed execution. 2. Verify the defect and execution reference each other as specified. 3. Move the defect through the legal transitions to `Resolved` using an authorized role. 4. Attempt `Resolved → Closed` while the latest relevant execution is Failed or absent. 5. Record a later Passed verification execution for the linked case. 6. Retry `Resolved → Closed` with an authorized Tester / Test Lead / Admin. 7. Read the defect history. |
| Expected result | The defect is created and linked to the failed execution; closure before a Passed verification is rejected with HTTP 409 and does not add a history row; after a Passed verification, closure succeeds and adds exactly one new history event. Existing role rules still apply (403 for a role-denied transition; 409 for an invalid transition). |
| Actual result / status | To be recorded during execution. |

### WFT-07 — Evaluate release criteria, state changes and waiver authorization

| Field | Specification |
|---|---|
| Objective | Verify individual release criteria, combined gate result, state restrictions and waiver audit data. |
| Priority | Critical |
| Requirement link | R7 |
| Preconditions | A release belongs to a project with linked requirements, test outcomes and defects. Test Lead, Admin and Tester identities are available. |
| Test data | Seed fixture: 4 decisive test outcomes (3 Passed, 1 Failed), 8 requirements with 5 covered, and 0 open Critical defects. Default criteria described by PLN-18 PR: min pass rate 80%, max open Critical 0, min coverage 80%. |
| Steps | 1. GET `/api/releases/{id}/gate`. 2. Verify `actual_pass_rate=75.0`, `actual_req_coverage=62.5`, `actual_open_critical=0` for the seed fixture. 3. Attempt to move to `Ready`. 4. As Tester, attempt to change criteria or create waiver. 5. As Test Lead, record a non-empty waiver reason. 6. Re-read the gate and attempt the permitted status transition. 7. Remove the waiver and verify the gate is still measured using the actual metrics. |
| Expected result | Gate fails on pass-rate and requirement-coverage criteria but passes Critical-defect criterion; `Ready` / `Released` is rejected with 409 without a waiver; Tester cannot change criteria/waive (403); Test Lead/Admin waiver records user, reason and time; waiver does not alter measured metric values. |
| Actual result / status | To be recorded during execution. |

### WFT-08 — Manage Test Plan version and review lifecycle

| Field | Specification |
|---|---|
| Objective | Verify versioned Test Plan CRUD and allowed status transitions. |
| Priority | High |
| Requirement link | R1 / R3 (provisional) |
| Preconditions | Project and release exist; Test Lead or Admin identity available. |
| Test data | Project ID `1`; version `1.0-demo`; title `SDS-06 Workflow Test Plan`. |
| Steps | 1. POST `/api/test-plans` with scope, approach, pass/fail criteria, environment and schedule risks. 2. Verify initial status `Draft`. 3. Attempt a duplicate version within the same project. 4. Update while Draft. 5. Attempt direct Draft → Approved. 6. Transition Draft → In Review → Approved using the documented status route. 7. Attempt to edit/delete the Approved plan. |
| Expected result | Plan returns 201 and starts in Draft; duplicate project/version returns 409; direct Draft → Approved returns 409; valid transitions succeed; Approved plan is protected from ordinary editing/deletion as described by the final API contract. |
| Actual result / status | To be recorded during execution. |

### WFT-09 — Generate, persist and export a Test Plan snapshot

| Field | Specification |
|---|---|
| Objective | Verify point-in-time snapshot persistence and HTML/PDF output. |
| Priority | High |
| Requirement link | R1 / R3 (provisional) |
| Preconditions | WFT-08 plan exists; a role permitted to generate snapshots is available. |
| Test data | Approved or review-ready Test Plan with non-empty scope, approach, criteria and environment. |
| Steps | 1. POST the snapshot endpoint. 2. GET the snapshot detail. 3. Compare the stored HTML and structured payload to the plan version/status used at generation time. 4. Export HTML. 5. Export PDF for the same snapshot. 6. Update a Draft plan or create a later version and verify the earlier snapshot remains unchanged. |
| Expected result | Snapshot stores version/status, HTML, payload, generator and timestamp; HTML export returns `text/html`; PDF export returns `application/pdf` and a structurally valid PDF from the supported runtime; earlier snapshot remains an immutable point-in-time record. |
| Actual result / status | To be recorded during execution. |

### WFT-10 — Verify metric definitions against known seed data

| Field | Specification |
|---|---|
| Objective | Verify that each displayed metric follows the catalogue formula and shows enough counts to interpret the value. |
| Priority | High |
| Requirement link | R5 |
| Preconditions | Fresh disposable seed database; baseline API and, when merged, Test Run / Release Gate APIs. |
| Test data | Current seed fixture described in `metric-definitions.md`: 6 cases; 3 Passed, 1 Failed, 2 Not Run; 3 non-Closed defects. |
| Steps | 1. GET `/api/metrics` on the current baseline. 2. Confirm total tests, execution rate, pass rate and open defects. 3. For a run fixture, add 2 Passed, 1 Failed, 1 Blocked, 1 Skipped and 1 Not Run execution. 4. Recalculate completion rate and run pass rate independently. 5. For release scope, verify requirement coverage and open Critical count. |
| Expected result | Current API returns `6`, `66.7`, `75.0`, and `3` for the seed fixture. Run completion rate is `83.3%`; run pass rate is `66.7%`; blocked/skipped counts are visible and not misreported as passes. Release-gate measurements match the configured scope. |
| Actual result / status | To be recorded during execution. |

### WFT-11 — Import JUnit XML with matched and unmatched results

| Field | Specification |
|---|---|
| Objective | Verify project-scoped stable-key mapping and explicit unmatched-result reporting. |
| Priority | Medium |
| Requirement link | R6 |
| Preconditions | Project contains requirement-linked test cases; authenticated Admin / Test Lead / Tester token. |
| Test data | Valid small JUnit XML with one known stable test-case key and one unknown key; include commit and branch metadata. |
| Steps | 1. POST the XML to `/api/projects/{id}/runs/import`. 2. GET the import list and detail. 3. Verify matched and unmatched result rows, counts, commit and branch metadata. 4. Try malformed or oversized XML. |
| Expected result | Valid XML is stored atomically; known key maps to the case; unknown key is retained with an unmatched reason; malformed/oversized input is rejected; import snapshot does not silently alter case statuses or interactive Test Run metrics. |
| Actual result / status | To be recorded during execution. |

### WFT-12 — Verify role authorization and negative paths across workflow modules

| Field | Specification |
|---|---|
| Objective | Verify protected operations enforce server-side roles, not only frontend visibility. |
| Priority | Critical |
| Requirement link | Cross-cutting; map to R8 only after original R8 wording is confirmed. |
| Preconditions | Admin, Test Lead, Tester and Developer identities are available; all feature routes are integrated. |
| Test data | Attempt privileged Test Suite, Test Case, Test Plan, criteria and waiver operations using each role. |
| Steps | 1. Execute the documented allowed mutations with the intended role. 2. Repeat the same mutation using a lower-privileged role. 3. Submit invalid IDs, statuses and empty required fields. 4. Re-read data and history after each rejected request. |
| Expected result | Allowed roles succeed; disallowed roles receive HTTP 403; invalid data or references receive the documented 4xx response; rejected operations do not leave partial data or history side effects. |
| Actual result / status | To be recorded during execution. |

## 3. Execution record template

Copy this table for each executed case or link the corresponding Test Run / Test Execution record after PLN-17 integration.

| Test case ID | Run ID | Build / commit | Tester | Executed at | Status | Actual result / evidence | Defect ID |
|---|---|---|---|---|---|---|---|
| WFT-01 … WFT-12 | To be assigned | To be recorded | To be recorded | To be recorded | Not Run | To be recorded | Optional |

## 4. Review notes

- WFT-01 through WFT-05 depend on PLN-16 / PR #21 and its frontend follow-on PR #22.
- WFT-04 through WFT-06 depend on PLN-17 / PR #25 and frontend PR #23.
- WFT-07 depends on PLN-18 / PR #27 and the dashboard follow-on PR #24.
- WFT-08 and WFT-09 depend on PLN-26 / PR #26, which is a shared task with Caner Serbest.
- WFT-10 is aligned with PLN-25 and the expanded metrics implementation work in PLN-24.
- Do not mark a case Passed based solely on a green PR check if the acceptance behavior itself was not exercised.
