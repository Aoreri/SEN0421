# PLN-34 — Playwright acceptance tests

Esra Kaya · target 23.11.2026 · ISO/IEC/IEEE 12207 Verification and
29119-2 Test Execution.

The Chromium suite checks:

- Rejected credentials, successful login, session persistence and logout.
- Creating a test run in the UI, recording a failed execution, creating its
  linked defect, Open → In Progress → Resolved → Closed → Open, rejected
  closure before a successful verification, persisted execution links and
  append-only history after reload.
- HTML export and a browser PDF attachment download from a saved Test Plan
  snapshot, including the original version after the live plan changes.

Test Plan management has no UI on the current base. The document scenario
sets up a plan through its existing API and tests the real browser export;
it does not claim coverage of a future document management screen or of
PLN-30/PLN-39 report types. Successful verification setup uses the existing
Test Execution API; failed-result entry and defect creation use the UI.

## Run on a disposable stack

From the repository root (Docker Compose v2, Node 22):

```sh
docker compose -p sds06-e2e-local -f frontend/e2e/compose.yml up --build -d --wait --wait-timeout 180
cd frontend
npm ci
npx playwright install --with-deps chromium
E2E_DISPOSABLE=1 npm run test:e2e
E2E_DISPOSABLE=1 REPORT_COMMIT="$(git rev-parse HEAD)" REPORT_BRANCH="$(git branch --show-current)" npm run test:e2e:report
cd ..
docker compose -p sds06-e2e-local -f frontend/e2e/compose.yml down --volumes --remove-orphans
```

Always run the final cleanup, including after failure. This stack exposes only
`127.0.0.1:5173`; PostgreSQL and the backend are internal. Its project-scoped
`e2e_pgdata` volume is separate from the development `pgdata` volume. Never
run this against shared or production data. The explicit `E2E_DISPOSABLE=1`
opt-in acknowledges that tests create records. Demo accounts are seeded by
the normal migrations, with the documented `demo1234` password.

`E2E_BASE_URL` can point to another **disposable** instance (default:
`http://127.0.0.1:5173`). For an installed local Chromium, set
`PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`; CI uses the pinned Playwright browser.
The suite starts no development server implicitly and does not mock API
responses or use preview-store records. POST responses and independent GETs
verify persistence. There are no fixed sleeps or automatic retries.

## CI evidence and dogfooding

The `Playwright E2E (Docker Compose)` job builds the production Dockerfiles,
waits for health checks, runs Chromium, imports the **unmodified** JUnit XML
into that same running application, then reads the import back and checks
its project, all three case mappings, commit and branch. The setup creates
unique case IDs in a dedicated project and attaches those IDs to Playwright
JUnit properties. The import is also attempted after a browser test failure;
the failed test step still makes CI fail. Missing reports or wrong mappings
fail the importer rather than reporting false success.

Download `playwright-e2e-evidence` from the Actions run (14-day retention):
`junit.xml`, `import-evidence.json`, the token-free fixture manifest, HTML
report, failure screenshots/traces, and Compose logs. Browser traces may
contain disposable demo-session tokens; do not reuse real credentials here.
CI always removes only its own uniquely named stack and volume.

The normal frontend lint/typecheck checks include the E2E sources. No
application schema, merged migration or production endpoint is changed.

Exports use the UI session JWT through fetch, including PDF blob downloads,
so they remain compatible with authenticated read endpoints. CI records the
actual checkout commit (including a PR merge commit), not an untested PR head.
