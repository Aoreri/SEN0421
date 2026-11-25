# PLN-39 — IEEE 829 Test Incident Report and Test Log Template Content Mapping

**Contributor responsibility:** Emirhan Ulutürk — report template content  
**Shared implementation:** Caner Serbest — API endpoints and snapshot persistence  
**Prepared:** 22 November 2026  
**Implementation PR:** [PLN-39 PR #37](https://github.com/Aoreri/SEN0421/pull/37)

## 1. Purpose and scope

This note records the content design of the two report templates introduced in PLN-39. The HTML template files and rendering/API implementation are included in the shared PLN-39 pull request:

- `backend/app/templates/test_incident_report.html.j2`
- `backend/app/templates/test_log.html.j2`
- Rendering, snapshot and export routes: `backend/app/test_reports.py`

Caner's shared implementation provides the endpoints and snapshot persistence. The report content is designed to give an evaluator a defect-oriented Test Incident Report and a run-oriented Test Log. The mapping is purpose-based and does not claim that every normative information item in IEEE 829 or ISO/IEC/IEEE 29119-3 has been independently certified.

## 2. Test Incident Report content map

| Template section | Required information shown | Source data / purpose |
|---|---|---|
| Header and identifier | Report ID, defect ID, title, severity, current status, generator, generation time. | Identifies one incident report and its point-in-time context. |
| 1. Identifier and summary | Incident identifier, defect title, standards mapping. | Gives the evaluator a concise incident summary. |
| 2. Incident description | Linked test case, suite, priority, automation flag, requirement links, test steps, expected result, associated executions, actual result, notes/evidence, executor and time. | Describes the test context and observable anomaly evidence. |
| 3. Impact and verification | Severity, current lifecycle status, and whether the latest relevant verification execution satisfies the `Resolved → Closed` gate. | Communicates impact and the evidence needed before closure. |
| 4. Immutable incident history | Ordered status transitions with previous/new status and timestamp. | Preserves the defect's audit trail. |

**Content acceptance checks:**

- The report remains identifiable even when no test case is directly linked to the defect.
- If a test case exists, the report shows its stable ID, title, expected result, steps, and requirement links.
- Linked execution rows distinguish `Passed`, `Failed`, `Blocked`, `Skipped`, and other supported outcomes and include actual result/notes where present.
- Missing optional data is rendered explicitly (for example, `-` or a no-record message), not silently omitted in a way that changes meaning.
- History is chronological and is read from the append-only defect history source.
- The closure-verification summary does not mark a defect safe to close when the latest relevant verification is not `Passed`.

## 3. Test Log content map

| Template section | Required information shown | Source data / purpose |
|---|---|---|
| Header and identifier | Test Log ID, run ID/name, project, release, suite, run creator/time, report generation time. | Identifies the execution session. |
| 1. Identifier and scope | Test Log identity and scope statement. | States which test run the log records. |
| 2. Execution summary | Planned/executed count, completion rate, Passed, Failed, Blocked, Skipped, Not Run, and decisive pass rate. | Summarizes the run without hiding blocked/skipped/not-run results. |
| 3. Chronological execution records | Execution ID, test-case ID/title, requirement links, status, expected and actual result, notes, executor/time, linked defect IDs. | Provides one auditable row per execution. |
| 4. Anomalies and incidents | Defect ID/title/severity/status and related test case. | Connects failures and other anomalous results to incident records. |

**Content acceptance checks:**

- The log identifies the exact run, project, optional release, and optional suite.
- Every execution row retains the stable test-case ID and all requirement links.
- `Not Run` rows remain visible and are not counted as executed results.
- The summary distinguishes execution completion from pass rate; blocked and skipped results are shown separately.
- Defects are limited to those linked to executions in the selected run.
- A run with no execution or no linked defect displays an explicit empty-state message.

## 4. Rendering, snapshots and export boundary

The shared PLN-39 API implementation builds an HTML representation and a structured payload, stores both in a point-in-time snapshot, and exposes list/detail and HTML/PDF export routes. The snapshot metadata records the generator identity and timestamp. PDF rendering attempts WeasyPrint and has a PDF fallback path (RSK-07).

| Artefact | Endpoint family in the shared PR | Expected behavior |
|---|---|---|
| Incident snapshot creation | `POST /api/defects/{defect_id}/incident-report/snapshots` | Creates and stores a point-in-time incident report. |
| Incident snapshot list/detail | `GET /api/defects/{defect_id}/incident-report/snapshots...` | Returns snapshot metadata or stored HTML/payload. |
| Incident export | `GET /api/defects/{defect_id}/incident-report/export?format=html|pdf` | Exports live or selected snapshot content. |
| Test Log snapshot creation | `POST /api/test-runs/{run_id}/test-log/snapshots` | Creates and stores a point-in-time run log. |
| Test Log snapshot list/detail | `GET /api/test-runs/{run_id}/test-log/snapshots...` | Returns snapshot metadata or stored HTML/payload. |
| Test Log export | `GET /api/test-runs/{run_id}/test-log/export?format=html|pdf` | Exports live or selected snapshot content. |

A successful PDF content type/signature is not by itself proof of visual fidelity. The final integrated build must generate multi-page reports in the supported container, open the PDFs, and check that the expected sections and records are present.

## 5. Verification evidence in PLN-39 PR #37

The shared PR description reports the focused API tests below as passing on SQLite and PostgreSQL 16:

- `test_incident_report_snapshots_and_html_pdf_export`
- `test_test_log_snapshots_and_html_pdf_export`

The PR also reports successful Ruff, mypy, and frontend lint/typecheck/build checks. These are branch-level results while PR #37 is open; repeat verification after migration integration and merge.

## 6. Standards mapping

- **IEEE 829 artefact terminology:** Test Incident Report and Test Log.
- **ISO/IEC/IEEE 29119-2:2021:** test incident reporting and test execution/logging process evidence.
- **ISO/IEC/IEEE 29119-3:2021:** documented information items, identifiers, content, timestamps, and stored report snapshots.

This is an artefact-purpose mapping, not a claim that the project has completed a full normative conformance assessment.
