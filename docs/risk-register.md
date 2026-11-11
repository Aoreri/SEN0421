# SDS-06 — Risk Register

**Work package:** PLN-02  
**Version:** 0.1 — Draft for team review  
**Prepared:** 11 November 2026  
**Basis:** Risks RSK-01 to RSK-08 from Bi-Weekly Progress Report #1.

The impact ratings and detection/mitigation statements below reproduce the progress report. The report does not specify numerical probability values or named risk owners for each risk, so those fields are intentionally not invented. Status reflects the evidence visible in the repository on 11 November 2026 and should be confirmed by the team.

| ID | Risk / cause | Impact stated in report | Detection / trigger | Response / mitigation from report | Current note / status |
|---|---|---|---|---|---|
| RSK-01 | Scope is too broad (test management, defect tracking, and document generation in one product); dashboard or documents may remain incomplete. | High | Assignment and scope analysis. | Deliver vertical slices per sprint; if scope must be reduced, prioritize in the stated order: Test Log → design specifications → flaky-test detection. | Open scope-control risk; continue using prioritized vertical slices. |
| RSK-02 | Incorrect interpretation of the IEEE 829 to ISO/IEC/IEEE 29119 relationship could reduce standards-alignment quality. | Medium | Review of standards catalogues. | Retain the course-facing IEEE 829 document labels where needed, provide a purpose-level mapping to the current 29119 framework, and confirm the approach with the instructor. | PLN-01 mapping document is merged; instructor confirmation and full-text checks remain open. |
| RSK-03 | Standards mapping and the 12207 edition information may be wrong if not checked against the standard texts. | Medium | Cross-check of official sources and standard text. | Verify editions using official ISO/IEEE catalogues and check licensed full texts where available. | Catalogue status is recorded in PLN-01; exact clause/template validation and instructor decision on 12207 edition remain open. |
| RSK-04 | Uneven distribution of team contributions may reduce the work-allocation score. | Medium | Work-package and PR/issue history review. | Assign a named owner to each work package; use pull-request review and retain issue history in later reports. | Named assignments and PR history are present; continue reporting actual effort and unresolved review work. |
| RSK-05 | Incorrect or slow metric calculation may make the dashboard misleading. | Medium | Review metric definitions and SQL tests using seed data. | Define each metric formally; test SQL queries with seed data; use aggregated views when needed. | Current `/api/metrics` computes execution rate, pass rate, and non-closed defects; performance target remains to be measured. |
| RSK-06 | CI results may be mapped unreliably to test cases, leaving unmatched results. | Medium | Design review. | Use stable test-case keys in test names/labels; list unmatched results in an import report. | CI checks and test IDs exist; application-level JUnit/Cobertura import is still planned, so this risk remains open. |
| RSK-07 | PDF-generation dependencies may fail during a Windows demo. | Medium | Technology-stack evaluation and demo rehearsal. | Run document generation inside a Docker image and retain HTML export as a fallback. | Report generation is not in the current implemented baseline; containerized PDF/HTML generation and fallback need verification when implemented. |
| RSK-08 | The initial in-memory demo could lose data on restart and be mistaken for a real production product. | Low | Demo review. | Display a DEMO/TEMPLATE warning and plan PostgreSQL persistence. | PostgreSQL persistence and migrations are now present in the repository; keep the demo/template and non-production warning because credentials/configuration remain development-only. |

## Review cadence

Review this register at each bi-weekly progress checkpoint, when a risk trigger occurs, and before a project demonstration or release decision. Update status only when there is concrete evidence (merged PR, test result, instructor decision, or documented mitigation). Record residual risk when a mitigation reduces but does not eliminate the risk.
