# PLN-35 — reproducible performance and unit coverage

Owner: Esra Kaya · target: 24.11.2026. ISO/IEC/IEEE 12207 Verification and
Measurement; ISO/IEC 25010 performance efficiency and testability.

## Performance

Use an **empty, disposable** PostgreSQL 16 database named
`sds06_pln35_benchmark`. The seeder refuses any other name prefix and refuses
an existing schema. It never drops a database or deletes application data.
Ports 8000 and 5175 must be free. From the repository root:

```sh
python -m pip install -r backend/requirements-dev.txt
npm ci --prefix frontend
npm run build --prefix frontend
npm ci --prefix quality
cd quality
npx playwright install --with-deps chromium
PLN35_DISPOSABLE=1 DATABASE_URL=postgresql+psycopg://sds06:sds06@localhost:5432/sds06_pln35_benchmark npm run measure
```

Only use the public demo credentials in a disposable environment. The runner
owns and stops its Uvicorn and Vite preview child processes. The CI service
container is removed by the GitHub runner. Local database/container cleanup
remains the operator's responsibility. No `.env` file is read.

The deterministic population adds 100 cases, 100 runs, exactly **10,000
interactive TestExecution rows** (7,000 Passed / 1,000 Failed / 1,000 Blocked /
1,000 Skipped), 100 defects with append-only creation/lifecycle history, and
explicit execution/defect and case/requirement links. It retains migrated
seed data. The selected release contains all 10,000 executions. An empty
control release verifies that changing the selector still changes the real
metric population and switching back restores 10,000.

The production frontend bundle is served by Vite preview and proxies to the
real FastAPI process. This is a single-user reference measurement, not a
production-network, load/concurrency or Docker image benchmark. Chromium
uses 1280×800, DPR 1. Each of 10 navigations gets a fresh browser context
with an authenticated demo session. Login is outside the timer; restoring
that session, navigation, all eight real dashboard responses, metric/chart
DOM checks and two animation frames are inside. The first sample includes
cold application-query/template caches; all raw samples are retained.
No request is mocked, retried or discarded. Every initial dashboard data
request must occur exactly once. Preview fallback cannot pass the API and
10,000-execution checks.

Live Test Plan HTML export, live PDF generation and snapshot generation each
have 5 measurements, including their first invocation. Timers include the
HTTP response body. Content types, document content/PDF signature and saved
snapshot identity are validated. The current main branch provides Test Plan
exports; unmerged Test Summary / Incident / Log reports are not claimed as
measured. PDF timing measures the existing endpoint's WeasyPrint/fallback
implementation; it does not prove typography or visual equivalence.

Every sample must be strictly below its threshold: panel **2,000 ms**, each
document operation **10,000 ms**. Mean/median/p95 never hide a failed maximum.
`results/performance.json` contains exact samples, first/min/median/p95/max,
hardware/runtime metadata, fixture counts, request diagnostics and the tested
commit. It is uploaded as `pln35-performance` for 14 days. The CI workflow runs
on relevant PRs, PLN-35 feature-branch pushes and manual dispatch. Shared-runner
measurements describe that recorded environment, not a guarantee for all hosts.

`PYTHON` can select an installed Python, and
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` can select installed Chromium for local
runs. `PLN35_SAMPLES` permits shorter local diagnostics; CI requires at least
10. An isolated SQLite file whose name starts with `sds06_pln35_` is accepted
for local diagnostics, but PostgreSQL is the acceptance reference.

## Database-free unit coverage

From `backend/`:

```sh
COVERAGE_FILE=.coverage-unit python -m pytest -q -m unit --cov=app.main --cov=app.runs --cov=app.metrics --cov-report=term-missing --cov-report=json:unit-coverage.json --cov-report=xml:unit-coverage.xml
python scripts/check_unit_coverage.py unit-coverage.json
```

The gate independently requires **80% line and 80% branch coverage in each**
of `app/main.py` (defect workflow and legacy metrics), `app/runs.py` (run and
execution workflow), and `app/metrics.py` (SQL metrics response/scoping).
Session doubles never connect to a database. They check status/role and
verification decisions, missing records, immutable history creation, link
preservation, deduplication and numerical/time/serialization boundaries.
SQL query execution and PostgreSQL trigger correctness remain covered by
the separately run integration suite; its coverage is not counted as unit
coverage. No source line is excluded to reach the threshold.

The normal CI backend job enforces this gate and uploads JSON/Cobertura as
`workflow-metrics-unit-coverage`. Final measured numbers and the ISO/IEC
25010 table input are in [the measurement report](../docs/pln35-quality-measurements.md).

The benchmark count is scoped to the 100 runs it creates. If a future seed
migration adds executions to the selected release, `panel_executions` and
`panel_pass_rate` explicitly describe that retained population. Such records
are preserved; they are not counted as benchmark-created executions. Logout
also verifies that the anonymous dashboard clears data without protected API
requests. CI evidence identifies the exact checked-out tree.
