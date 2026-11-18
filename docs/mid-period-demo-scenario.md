# SDS-06 — Mid-Period Demonstration Scenario

**Plan item:** PLN-27  
**Version:** 1.0 — Draft for team review  
**Prepared:** 18 November 2026  
**Estimated presentation:** 10–12 minutes  
**Audience:** Course instructor and project team

## 1. Demonstration objective

Demonstrate one traceable workflow from requirements and test-case authoring through test execution, defect verification, release readiness and Test Plan evidence. The scenario should show how the modules work together, rather than presenting unrelated screens.

## 2. Demo readiness checklist

Before presenting:

1. Use a disposable demo database and the documented local Docker Compose environment.
2. Confirm that the Test Suite / Test Case, Test Run / Execution, Release Gate and Test Plan PRs are integrated into one branch.
3. Resolve the Alembic revision collision described in the updated SDD. Do not run a combined `alembic upgrade head` while multiple `0006` revisions still depend on `0005`.
4. Run migrations to head and confirm `/api/health` returns `{"status":"ok"}`.
5. Run the backend, PostgreSQL and frontend checks on the integrated candidate.
6. Prepare Admin, Test Lead, Tester and Developer demo identities; avoid showing secrets or private tokens on screen.
7. Prepare test data and a short JUnit XML fixture; keep one unknown case key to demonstrate unmatched-result handling.

If an implementation PR is still open or its migration chain is not integrated, present the design and its PR status as pending. Do not simulate a feature and describe it as a merged, working feature.

## 3. Scenario and presentation flow

| Time | Presenter action | Expected evidence / narration |
|---|---|---|
| 0:00–1:00 | Introduce SDS-06 and its user roles. Show the project dashboard and project/release context. | Explain that the system connects requirements, suites/cases, executions, defects and release evidence. |
| 1:00–2:30 | Open the Test Suite / Test Case screen. Create or show suite `Workflow Acceptance`; open a case with stable ID, steps, expected result, priority and automation flag. | Show that the case has at least one requirement link and can appear in the requirement-to-test matrix. |
| 2:30–3:30 | Show the requirement traceability matrix. Select one requirement and inspect linked cases and coverage. | Explain many-to-many traceability and note that the approved R1–R8 wording must remain the source of the final requirement baseline. |
| 3:30–5:00 | Create a Test Run for the workflow suite. Open its execution workbench and record one Failed result with actual result and notes. | Show that the run creates `Not Run` execution rows and that the result records executor and timestamp. |
| 5:00–6:30 | Open a defect from the failed execution. Move it through the legal workflow to `Resolved`; attempt to close it before a Passed verification run. | Show the HTTP 409 / user-facing rejection and explain that no invalid history event is recorded. |
| 6:30–7:30 | Record a subsequent Passed verification execution and close the defect with an authorized role. | Show the new execution-to-defect relationship and append-only history timeline. |
| 7:30–8:30 | Open the release gate card. Show pass rate, open Critical defects and requirement coverage. Attempt `Ready` while a criterion fails; then show criteria/waiver flow with a Test Lead or Admin. | Distinguish measured gate values from an administrative waiver; a waiver is not a metric pass. |
| 8:30–9:45 | Open the Test Plan. Show Draft → In Review → Approved, create a snapshot, and export HTML/PDF. | Demonstrate version identifier, snapshot timestamp and output; use the same stored snapshot when comparing outputs. |
| 9:45–10:45 | Show metric definitions and the dashboard trends / severity view. | Explain execution completion rate vs pass rate and show the denominator/counts. |
| 10:45–12:00 | Show JUnit import report with matched/unmatched results and finish with CI / RTM evidence. | Explain that JUnit import snapshots remain separate from interactive Test Runs; point to RTM and CI checks. |

## 4. Demo fixture

Use a clearly labelled demo project and synthetic records only.

| Fixture | Suggested value | Purpose |
|---|---|---|
| Project | Existing seeded `SDS-06` project or a disposable `SDS-06 Demo` project | Project boundary for suite, test cases and release. |
| Release | `demo-0.2` | Release-gate walkthrough. |
| Suite | `Workflow Acceptance` | Groups the demonstration cases. |
| Test case A | `DEMO-WF-001` — valid workflow path | Record a Passed execution after the initial failure. |
| Test case B | `DEMO-WF-002` — validation error path | Record Failed / Blocked / Skipped as needed for the dashboard. |
| Requirement links | Use existing approved requirement IDs; if using placeholder R1–R8 seed rows, state that their wording is pending confirmation. | Demonstrate traceability without inventing requirement statements. |
| Failed execution defect | `Demo defect from failed execution`, severity `High` | Demonstrate execution-to-defect linking and verification before closure. |
| Test Plan | Version `0.2-demo` | Demonstrate plan state, snapshot and export. |
| JUnit file | One known test-case key and one unknown key | Demonstrate mapping and explicit unmatched result. |

## 5. Success criteria

The demonstration is successful when the audience can see:

- A test case has a stable ID, specification fields, and at least one requirement link.
- A run contains execution records and supports the four result outcomes.
- A failed execution can create a linked defect.
- A defect cannot be closed before a successful verification execution when the rule applies.
- Release readiness is based on explicit pass-rate, Critical-defect and requirement-coverage criteria; waivers are separately auditable.
- A versioned Test Plan has a controlled review lifecycle and a stored, reproducible snapshot.
- Metric formulas and traceability evidence are available, and CI status can be linked to the candidate commit.

## 6. Known limitations to disclose

- The original detailed R1–R8 text must be confirmed from the approved source; database seed titles are placeholders.
- Expanded metrics and dashboards must be identified as pending if their respective PRs are not integrated.
- JUnit import snapshots do not automatically update interactive Test Run results or test-case statuses.
- A green PR check proves the checks configured in CI passed; it does not replace the end-to-end demonstration or the course standards review.
- The project is an academic demo/template, not a production service.
