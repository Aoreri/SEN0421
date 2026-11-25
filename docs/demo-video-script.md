# SDS-06 — Final Demonstration Video Script

**Plan item:** PLN-38  
**Prepared:** 22 November 2026  
**Target length:** 7–9 minutes  
**Recording status:** Script and shot list prepared; an actual recording and shareable URL must still be added.

> **Video URL:** TO BE ADDED AFTER RECORDING. Do not treat this document as proof that a demo video has been recorded.

## 1. Recording preparation

1. Use the integrated `main` baseline after the required PRs have been merged and the final Compose stack has passed verification.
2. Start the stack with `docker compose up --build -d --wait` and confirm the API health endpoint.
3. Use only disposable demo data and sample accounts. Do not show private tokens, secrets, personal data, or environment files.
4. Keep the browser zoom and screen resolution readable. Close unrelated tabs and notifications.
5. Prepare a simple test case with a linked requirement, a test run, one failed execution, a related defect, and a subsequent passing verification execution.
6. If the Test Plan UI or report UI is not merged, demonstrate the available API endpoint through Swagger and explicitly say that the UI/report PR is pending; do not imply it is integrated.

## 2. Timed storyboard and narration

| Time | Screen / action | Narration points |
|---|---|---|
| 00:00–00:40 | Title slide and dashboard | Introduce SDS-06 as an academic Agile Test and Defect Tracking System. State the scope: requirements, test design, execution, defects, metrics, and test documentation. |
| 00:40–01:30 | Login page and role selection | Explain Admin, Test Lead, Tester, and Developer roles. Sign in with a sample account and explain that backend authorization enforces permissions. |
| 01:30–02:20 | Projects & Requirements | Show a project, release, requirement list, and the project/requirement relationship. |
| 02:20–03:20 | Test Cases & Matrix | Show a test suite, stable test-case ID, priority, automation flag, steps, expected result, and requirement links. Demonstrate the traceability matrix. |
| 03:20–04:25 | Test Runs | Create/open a run, show `Not Run` execution rows, record `Failed` with actual result/notes, and create a defect from the failed execution. |
| 04:25–05:25 | Defect detail | Show the `Open → In Progress → Resolved` lifecycle, history entries, and explain why closure is blocked until a `Passed` verification execution exists. Then show the passing verification and permitted close action. |
| 05:25–06:20 | Dashboard / release gate | Explain execution/pass metrics, trends, requirement coverage, defect measures, and the configured release criteria/waiver distinction. |
| 06:20–07:25 | Test Plan and reports | Demonstrate Test Plan lifecycle and snapshot/HTML/PDF export if the UI/report path is integrated. Otherwise use `/docs` and label the API/PR status accurately. |
| 07:25–08:10 | CI / standards / close | Show the GitHub Actions checks and summarize 12207, 29119-2/-3, IEEE 1016, 29148, 1012 and 25010 work products. State known limitations honestly. |

## 3. Suggested closing statement

“SDS-06 connects requirements to test cases, executes test runs, records and verifies defects, and provides project/release metrics and test documentation. The team has used automated API, PostgreSQL, frontend, and CI checks. Remaining acceptance items are the integrated migration chain, final PDF rendering inspection, performance/clean-machine measurements, and any work still in open pull requests.”

## 4. Upload and evidence steps

- Record the walkthrough using the course-accepted screen recorder.
- Export at a readable resolution with audio narration.
- Upload to the team/instructor-approved storage or course portal.
- Verify the link opens for the instructor/team (appropriate permissions, not a private local path).
- Replace the URL placeholder at the top of this file and in `final-deliverable-report.md`.
- Add the recording date, duration, and commit/tag demonstrated.
