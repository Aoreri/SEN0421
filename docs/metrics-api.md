# PLN-24 — SQL metrics API

Owner: Esra Kaya · target: 19 November 2026 · R5.
Standards: ISO/IEC/IEEE 29119-2 — Test Monitoring and Control;
ISO/IEC/IEEE 12207 — Measurement.

## Dependency and boundary

This change builds on PLN-17 PR #25 (`2a664a6`) for `TestRun`, `TestExecution`
and `execution_defects`. It does not implement or alter that teammate's models,
migrations, execution writes, verification gate, or release policy. Review the
PLN-24-only diff against `feature/pln-17-test-runs-executions`, then integrate after
PLN-17. It adds no schema migration. Existing `GET /api/metrics` is preserved.

The metric definitions follow the PLN-25 catalogue in PR #28: decisive-result pass
rate, project catalogue requirement coverage, a created-defect cohort for reopen
rate, and time to **first** resolution. The catalogue remains its author's work;
this PR does not edit it. The pending PLN-21 dashboard's `expandedMetrics(releaseId)`
contract is supported. Time metrics are nullable when no observations exist; the
UI must display “unavailable” for null, rather than claiming a measured zero.

## Request and scope

`GET /api/metrics/expanded` requires authentication (any valid bearer token, PLN-29).
Optional query parameters:

- `project_id`: positive existing project ID.
- `release_id`: positive existing release ID; implies its project. A conflicting
  project filter returns 422. Unknown resources return 404.
- `start_at`, `end_at`: ISO-8601 timezone-aware timestamps, with inclusive start
  and exclusive end. Values are normalized to UTC. Start must precede end.

Use the real sprint's known date bounds to obtain a period report, for example
`?release_id=1&start_at=2026-11-05T00:00:00Z&end_at=2026-11-19T00:00:00Z`.
There is no Sprint entity or sprint-membership relationship in main or PLN-17.
An explicit `sprint_id` therefore returns 422 with this explanation instead of
inventing membership. Stored sprint-ID reporting remains unavailable until that
model and its links are provided by the team.

Run scope uses `TestRun.created_at`; result counts use the current execution
snapshots for those runs. They are not a historical reconstruction of execution
edits, because the source model has no execution audit history. Every execution
row counts once, including repeated cases in separate runs. Imported JUnit
snapshots are separate evidence and are excluded from interactive-run metrics.

Defect scope:

- Global: all defects with an initial creation event.
- Project: defects linked through project requirements/test cases or explicit
  execution-defect links to the project's runs.
- Release: **only** explicit execution-defect links to that release's runs.
  Same-project case membership alone does not establish a defect's release.

Defects are selected by their first creation event in the same `[start,end)`
period; all qualifying history up to the report's as-of time is then considered.
As-of is the earlier of current UTC and end. History events at end are excluded.
Latest history state is determined by timestamp, then ID, avoiding ambiguity when
multiple events have the same timestamp. A defect is counted once even if linked
to several executions/cases or reopened several times. Missing creation history
is excluded from defect rates/times and counted explicitly under `denominators`.

Requirement coverage is current project catalogue traceability (or global
catalogue without filters), including requirements with no tests. Requirements
have no release or historical linkage, so release selection uses its project
population and the response labels this limitation. It is not code coverage or
proof that every requirement was successfully executed.

## Response and definitions

| Key | Calculation / meaning |
| --- | --- |
| `total_tests` | Number of planned interactive execution rows in selected runs. |
| `execution_rate` | `(Passed + Failed + Blocked + Skipped) / planned × 100`. |
| `pass_rate` | `Passed / (Passed + Failed) × 100`. |
| `requirement_coverage` | Distinct requirements with ≥1 linked case / all scoped requirements × 100. |
| `open_defects` | Created-cohort defects whose latest history status is not Closed. Resolved remains active. |
| `reopen_rate` | Distinct cohort defects with Resolved/Closed → Open / created cohort × 100. |
| `avg_defect_age_hours` | Mean hours from initial creation to as-of, for non-Closed cohort defects. |
| `avg_resolution_hours` | Mean hours from initial creation to first Resolved, excluding missing or invalid negative durations. |
| `run_series` | Per-run five-status counts and decisive pass rate, ordered by creation time then ID. `executed_at` is the legacy dashboard field name for run creation time, serialized with an explicit UTC offset on SQLite and PostgreSQL. |
| `defect_burnup` | UTC event-day cumulative first-created (`opened`), first-resolved (`resolved`), first-closed (`closed`) totals. `open_remaining` additionally accounts for subsequent close/reopen transitions and reflects active cohort inventory. Both Resolved → Open and Closed → Open add their event day. Resolved is already active, so its reopen adds zero to active inventory; reopening Closed adds one. First-resolution totals remain cumulative. Days without events are omitted. |
| `severity_distribution` | Cohort count per severity, including separate open/closed counts. |
| `scope` | Effective filters, as-of, data sources, run count, and truncation/sprint-availability flags. |
| `denominators` | Raw planned/decisive executions, total/covered requirements, created/reopened defects and age/resolution sample counts, plus missing-creation-history count. |

Percentages use one decimal place; zero denominator gives 0.0 with raw denominator
retained. No observed durations gives null, not zero. Genuine zero-hour durations
remain 0.0. Run-series detail is limited to the newest 1,000 runs, with a truncation
flag; aggregate totals still include the full scoped population.

SQL `COUNT`, conditional `SUM`, `AVG`, grouped subqueries/CTEs and window functions
perform the calculation. Joins use EXISTS/IN and deduplicated histories to avoid
fan-out. Only already aggregated series are formatted in Python. Duration SQL
uses PostgreSQL interval/epoch or SQLite julianday, with the same hour unit.
No test/defect statuses or append-only history records are modified by reporting.

## Verification

Seeded integration fixtures include two releases, six outcomes with every status,
a requirement linked through multiple cases, defects linked through multiple
executions, multiple reopens, first versus later resolution, project-only defects,
UTC period boundaries, missing data and empty populations. The same assertions run
on disposable SQLite and PostgreSQL. The legacy six-case seed endpoint remains
6 cases / 66.7% execution / 75% pass / 3 active defects.
