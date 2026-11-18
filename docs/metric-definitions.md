# SDS-06 — Metric Definitions Catalogue

**Plan item:** PLN-25  
**Version:** 1.0 — Draft for team review  
**Prepared:** 18 November 2026  
**Standards context:** ISO/IEC/IEEE 29119-2 — Test Monitoring and Control; ISO/IEC/IEEE 12207 — Measurement and Information Management

## 1. Purpose and measurement rules

This catalogue defines the meaning, formula, scope, and interpretation of the metrics used by SDS-06. A metric name must not be treated as self-explanatory: every report or dashboard should identify its population, time window, denominator, filters, and data source.

Unless a report says otherwise:

- Percentages are rounded to one decimal place, matching the current `GET /api/metrics` implementation.
- A percentage whose denominator is zero is displayed as `0.0%` by the current endpoint; it must not be interpreted as evidence of success.
- Project and release filters must be applied consistently to the numerator and denominator.
- Imported JUnit snapshots are not the same thing as interactive test runs. The PLN-22 import endpoint stores import evidence and unmatched results; it does not update test-case statuses or the current metrics endpoint.
- A metric is marked **Current** only when its calculation is present in the current `main` implementation. Definitions for work under open pull requests or later plan items are marked **Planned / PR in review**.

## 2. Current baseline metrics — `GET /api/metrics`

| Metric / API key | Formal definition | Formula | Included / excluded records | Current status |
|---|---|---|---|---|
| Total test cases (`total_tests`) | Number of test-case records in the current project scope. | `COUNT(test_cases)` | Includes every stored test case regardless of status, including `Not Run`. | Current |
| Execution rate (`execution_rate`) | Percentage of test cases with a recorded `Passed` or `Failed` status. | `(Passed + Failed) / total_tests × 100` | In the current endpoint, `Blocked` and `Skipped` are not counted as executed; `Not Run` is not counted. | Current; definition follows `backend/app/main.py` |
| Pass rate (`pass_rate`) | Percentage of executed cases that passed. | `Passed / (Passed + Failed) × 100` | Denominator includes only `Passed` and `Failed`; it excludes `Blocked`, `Skipped`, and `Not Run`. | Current |
| Open defects (`open_defects`) | Number of defects whose current status is not `Closed`. | `COUNT(defects WHERE status != 'Closed')` | Includes `Open`, `In Progress`, and `Resolved`; a reopened defect is counted because its status returns to `Open`. | Current |

### 2.1 Reproducible seed-data example

The repository's current backend integration test asserts the following seed result:

| Input | Value |
|---|---:|
| Stored test cases | 6 |
| Passed | 3 |
| Failed | 1 |
| Not Run | 2 |
| Defects not in `Closed` | 3 |
| Execution rate | `(3 + 1) / 6 × 100 = 66.7%` |
| Pass rate | `3 / (3 + 1) × 100 = 75.0%` |

This example is a regression fixture for the current endpoint. Do not silently change the legacy metric's denominator when adding `Blocked` and `Skipped` outcomes for interactive test executions; the new run-level metric below has a separate name and definition.

## 3. Test-run and execution metrics — PLN-17

The following definitions apply to interactive `TestRun` / `TestExecution` records described by PLN-17. The related implementation is in an open pull request and must be treated as pending integration until merged and migration sequencing is resolved.

| Metric | Formal definition | Formula | Notes / source |
|---|---|---|---|
| Planned executions | Number of execution rows created for the selected test run. | `COUNT(test_executions)` | Newly created rows begin as `Not Run`. |
| Execution completion rate | Percentage of planned execution rows that have a recorded terminal result. | `(Passed + Failed + Blocked + Skipped) / all execution rows × 100` | `Not Run` remains in the denominator but not in the numerator. |
| Passed count | Number of execution rows with status `Passed`. | `COUNT(status = 'Passed')` | Display as an absolute count. |
| Failed count | Number of execution rows with status `Failed`. | `COUNT(status = 'Failed')` | Failed executions may be linked to one or more defects. |
| Blocked count | Number of execution rows with status `Blocked`. | `COUNT(status = 'Blocked')` | A blocked case is completed as an attempt, but is not a pass. |
| Skipped count | Number of execution rows with status `Skipped`. | `COUNT(status = 'Skipped')` | A skipped case is completed as an attempt, but is not a pass. |
| Run pass rate | Percentage of decisive executions that passed. | `Passed / (Passed + Failed) × 100` | `Blocked`, `Skipped`, and `Not Run` are excluded from this denominator. Display the four result counts alongside the percentage to avoid hiding blocked/skipped work. |

`TestExecution.executed_at` is the event timestamp for an execution result. If no `Passed` or `Failed` rows exist, run pass rate is `0.0%` and the report should display the denominator as zero.

## 4. Requirement and release metrics — PLN-18 / PLN-24

| Metric | Formal definition | Formula | Scope / notes | Status |
|---|---|---|---|---|
| Requirement coverage (`actual_req_coverage`) | Percentage of requirements in the selected release's project that are linked to at least one test case. | `requirements with ≥1 linked test case / all project requirements × 100` | The current schema associates requirements with projects, not directly with releases; the release gate uses the release's project as its requirement population. | Defined by PLN-18 PR; pending integration |
| Release pass rate (`actual_pass_rate`) | Pass rate for the selected release's project/run population, using the run pass-rate denominator. | `Passed / (Passed + Failed) × 100` | Blocked and skipped results are shown separately and do not count as passes or failures. The exact selected-run aggregation must be kept consistent across API and dashboard. | Defined by PLN-18 PR; pending integration |
| Open Critical defects (`actual_open_critical`) | Number of Critical defects not in `Closed` status in the release's project scope. | `COUNT(severity = 'Critical' AND status != 'Closed')` | Includes `Open`, `In Progress`, and `Resolved`. | Defined by PLN-18 PR; pending integration |
| Release gate (`gate_passed`) | Boolean result indicating whether all configured release criteria are met. | `pass_rate ≥ min_pass_rate AND open_critical ≤ max_open_critical AND requirement_coverage ≥ min_req_coverage` | A recorded waiver is a governance override for the release status transition; it does not change the measured values or make the underlying metric pass. | Defined by PLN-18 PR; pending integration |

The PLN-18 proposal stores the configurable criteria on `releases`: `min_pass_rate` (percentage), `max_open_critical` (count), and `min_req_coverage` (percentage). Initial defaults in that PR are 80.0%, 0 Critical defects, and 80.0%, respectively. They are defaults in an open PR, not an approved permanent policy until the team accepts them.

## 5. Defect trend and time metrics — PLN-24 / dashboard proposal

These metrics are defined for the planned metrics API and dashboard. They must not be presented as live measurements until their required event data and queries are integrated and tested.

| Metric | Formal definition | Formula / event rule | Data requirement |
|---|---|---|---|
| Reopen rate | Percentage of defects created in the selected period that were reopened at least once. | `distinct defects with a history transition from Resolved/Closed to Open / defects first created in the period × 100` | `defect_history` creation and transition events. Count each defect once in the numerator even if reopened multiple times. |
| Mean open-defect age | Average elapsed time from the first `Open` history event to the report's as-of time for defects not currently `Closed`. | `AVG(as_of_time − first_open_at)` | Requires a stable first history timestamp for every defect. Report the as-of time. |
| Mean time to first resolution | Average elapsed time from the initial `Open` event to the first `Resolved` event for defects with a resolution event. | `AVG(first_resolved_at − first_open_at)` | Reopened defects remain measured against their first resolution in this definition; a separate cycle-time definition would be needed for repeated reopen cycles. |
| Defect burn-up | Cumulative defects created compared with cumulative defects first resolved over time. | Daily cumulative count of first `Open` events and first `Resolved` events. | `defect_history.at`; use the same date range and timezone for both series. |
| Severity distribution | Distribution of defects by severity at report time. | Count of defects per severity; dashboard default is active defects (`status != Closed`). | Current defect severity and status. Label whether closed defects are excluded. |
| Pass-rate trend | Run pass rate ordered by run creation/execution time. | One pass-rate point per run, using the run pass-rate formula in Section 3. | Stable run ordering and execution timestamps. |

If the source model does not provide a required timestamp or relationship, the metric must be shown as unavailable rather than estimated from unrelated fields.

## 6. Acceptance checks for metric calculations

| Check ID | Test data / action | Expected result |
|---|---|---|
| MET-01 | Current six-case seed data: 3 Passed, 1 Failed, 2 Not Run; three non-Closed defects. | `total_tests=6`, `execution_rate=66.7`, `pass_rate=75.0`, `open_defects=3`. |
| MET-02 | All test cases are `Not Run`. | Current legacy endpoint returns execution rate `0.0` and pass rate `0.0`; denominator behavior is explicit. |
| MET-03 | No test cases exist. | Current legacy endpoint returns total `0`, execution rate `0.0`, and pass rate `0.0`. |
| MET-04 | Close one non-Closed defect, then reopen it. | `open_defects` decreases by one after close and returns to its previous value after reopen. |
| MET-05 | Run has 2 Passed, 1 Failed, 1 Blocked, 1 Skipped, and 1 Not Run execution. | Completion rate is `5/6 = 83.3%`; pass rate is `2/(2+1) = 66.7%`; all five outcome counts are displayed. |
| MET-06 | Release has pass rate 75%, no Critical open defects, and 62.5% requirement coverage; defaults are 80%, 0, and 80%. | Gate fails on pass rate and requirement coverage, even though the Critical-defect criterion passes. |

## 7. Reporting requirements and limitations

Every dashboard card or report should include a clear label, a value and unit, the selected project/release/run, and the as-of date or run interval. Percentages must show their denominator or link to the detailed counts. A waiver must be shown separately from the metric outcome.

This catalogue is a PLN-25 documentation deliverable. It defines calculations and acceptance checks; it does not claim that the PLN-24 SQL aggregation API, all time-series metrics, or the complete dashboard are already integrated. Related code is tracked in the team's plan and pull requests.
