# PLN-23 — Cobertura import and CI dogfooding

Owner: Esra Kaya · target: 19 November 2026 · R5, R6.
Standards: ISO/IEC/IEEE 29119-2 — Test Monitoring and Control;
ISO/IEC/IEEE 12207 — Configuration Management.

## API contract

- `POST /api/projects/{project_id}/coverage/import`: raw `application/xml` or
  `text/xml`; returns 201 with the persisted summary and per-file counters.
- `GET /api/projects/{project_id}/coverage/imports?limit=50&offset=0`: newest first;
  limit 1–100; returns summaries without the file list.
- `GET /api/projects/{project_id}/coverage/imports/{id}`: full saved evidence.

Admin, Test Lead and Tester may import; every authenticated role may read.
Optional `commit` (7–64 hex characters), `branch` (nonblank, ≤255 characters) and
`junit_import_id` metadata are supported. A linked JUnit import must belong to the
same project; commit/branch are inherited, and conflicting metadata is rejected.
Snapshots do not overwrite test-case states, interactive executions or existing metrics.
There is no public deletion endpoint. Projects containing coverage evidence cannot
be deleted. No source file is ever read using the XML's source paths.

Example:

```bash
curl -X POST 'http://localhost:8000/api/projects/1/coverage/import?junit_import_id=1' \
  -H 'Authorization: Bearer <TOKEN>' -H 'Content-Type: application/xml' \
  --data-binary @coverage.xml
```

`summary` and each `files` entry contain `lines_valid`, `lines_covered`,
`branches_valid`, `branches_covered`, `line_coverage` and `branch_coverage`.
Percentages use one decimal place; no instrumented lines/branches gives 0.0%,
with the zero denominator retained. File entries additionally contain `filename`.

## Evidence and validation

The bounded parser accepts coverage.py's Cobertura format, including its standard
DOCTYPE declaration, without downloading the DTD. Entity declarations and external
entity references are rejected. Limits: 4 MiB, 5,000 files and 50,000 class-level
line records. File names must be relative labels without parent traversal.

Counters are recomputed from class-level `lines/line` records. Method-level line
records are redundant and are not counted twice. A line is covered if hits > 0;
branch counts use the `condition-coverage` fraction. Duplicate file/line records,
negative/nonfinite counters, unsupported hidden line structures, and inconsistent
root totals/rates are rejected with 422 before any write. A standard empty report
is accepted with zero counts. Over-limit uploads return 413; wrong media type 415.
This deliberately rejects producer variants that cannot be reconciled reliably;
it does not claim universal compatibility with every coverage XML dialect.

## CI dogfooding

The SQLite CI job produces **actual** `junit.xml` and `coverage.xml`. After a passing
test run, `backend/scripts/dogfood_ci.py` creates an isolated temporary SDS-06 SQLite
instance, applies real migrations, logs in as its seeded demo Tester, submits both
reports through the production ASGI routes, links coverage to the JUnit import,
and reads both records back through separate API requests. It uses the PR head
commit and branch as metadata. XML remains unchanged; unknown JUnit test-case keys
are retained as unmatched results. CI does not guess mappings or pretend they matched. The R6 integration test
records its explicit `test_case_id=TC-005` JUnit property; all other unmapped tests
remain visible as unmatched.

`ci-import-evidence` contains the original JUnit XML and `dogfood-report.json` with
the persisted API reports; artifacts are retained for 14 days. Existing SQLite and
PostgreSQL coverage artifacts remain unchanged. Failing tests do not publish a
successful import. A failed import fails the dogfooding step. No live deployment
is configured or modified, no deployment credentials are needed, and inherited
`DATABASE_URL` is overridden before importing application modules. The temporary
instance is discarded after exporting evidence. This is repeatable dogfooding,
not a claim of persistent publishing into the team's running deployment.

Reproduce from `backend/`, with dependencies from `requirements-dev.txt`:

```bash
python -m pytest -q --junitxml=junit.xml -o junit_family=legacy --cov=app --cov-report=xml:coverage.xml
python scripts/dogfood_ci.py --junit junit.xml --coverage coverage.xml \
  --commit <HEAD_SHA> --branch <BRANCH_NAME> --output dogfood-report.json
```

## Persistence and integration

Migration `0010_pln23_coverage` (`revision = "0010"`, `down_revision = "0009"`) adds only `coverage_imports`.
Apply `alembic upgrade head`; rollback removes coverage snapshots only. Earlier
migrations are unchanged.
The tests run on disposable SQLite and PostgreSQL databases.
