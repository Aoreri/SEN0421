# SDS-06 — Verification and Validation Results

**Plan item:** PLN-38  
**Reference:** IEEE 1012-2024 — System, Software, and Hardware Verification and Validation  
**Prepared:** 22 November 2026  
**Status:** Interim evidence register; final integrated V&V must be repeated after the remaining PRs merge.

## 1. Purpose and method

This record summarizes available verification and validation evidence for SDS-06. It distinguishes automated checks, API/database behavior tests, static analysis, environment measurements, and user demonstration. The evidence is reported at the scope actually tested; it is not a declaration that all IEEE 1012 process requirements have been independently fulfilled.

IEEE 1012-2024 is the active edition identified by IEEE SA. Its V&V scope includes evaluation, review, inspection, assessment, and testing of development products and their interfaces. The project tailors these activities to an academic web application.

## 2. Verification evidence register

| ID | Verification item | Method / evidence | Result | Limitation / next action |
|---|---|---|---|---|
| V-01 | Requirements baseline | Cross-check SRS v1.0, original R1–R8 seed mapping, project plan, and RTM v2. | **Partial pass.** Project FR/NFR IDs have module and test links. | Obtain approved original R1–R8 wording; FR-REQ-02 remains a gap. |
| V-02 | Architecture and data design | Review SDD context, composition, deployment, information, interface, and control-flow views against current `main`. | **Pass for documented baseline.** | Re-review after report, security, sprint, and release PR integration. |
| V-03 | Backend static quality | Ruff and mypy in CI/PR checks. PR descriptions report successful results for PLN-28, PLN-29, PLN-30, PLN-36, and PLN-39 branches. | **Pass on the individual PR branches as reported.** | Run the same checks on the final integrated `main` after merge. |
| V-04 | Backend API/integration behavior | Disposable SQLite pytest suite; focused tests for projects, traceability, runs, defects, imports, metrics, and Test Plans. | **Pass for the covered test cases.** | Do not add test counts from overlapping PR branches into one total; repeat on the integrated baseline. |
| V-05 | PostgreSQL-specific integrity | PostgreSQL 16 CI/service tests, including append-only `defect_history`; focused PostgreSQL reports in PLN-28/PLN-39 PR descriptions. | **Individual branch evidence reported as passed.** | Run `alembic upgrade head` and the complete database suite after all migration PRs are sequenced. |
| V-06 | Frontend static/build verification | ESLint, TypeScript typecheck, and Vite production build in CI. | **Pass on the reported PR branches.** | Repeat after the final set of UI/report changes merges. |
| V-07 | JUnit/Cobertura input validation | Parser, bounds, mapping, unmatched result, line/branch counter, atomic import and project-scope tests. | **Pass for current parser/import tests on `main`.** | Run the integrated CI job after later report/security changes. |
| V-08 | Test Plan lifecycle/snapshot/export | CRUD, transition, role, duplicate version, snapshot immutability, HTML/PDF response tests. | **Pass for API behavior.** | PDF signature/EOF checks do not prove layout, page completeness, or WeasyPrint availability in target Docker. Perform visual container verification. |
| V-09 | Test Incident Report and Test Log | PLN-39 PR #37: snapshot/detail/export tests; description reports 9 focused tests passing on SQLite and PostgreSQL 16. | **Pass reported on PR branch.** | PR #37 is still open; verify merged API/templates, content, PDF pages, and migration chain. |
| V-10 | Test Summary Report | PLN-30 PR #38: focused summary-report test; description reports SQLite and PostgreSQL focused test success. | **Pass reported on PR branch.** | PR #38 is still open; run report generation with integrated release data and inspect generated outputs. |
| V-11 | Security verification | PLN-29 PR #39 reports Bandit with 0 High/0 Medium and npm audit with 0 vulnerabilities. | **Pass reported on PR branch.** | PR #39 is open; integrated `main` still needs read-endpoint auth review and the reported checks after merge. |
| V-12 | Release automation | PLN-36 PR #40 adds release workflow and report generator; its PR checks are reported successful. | **Code/checks present on PR branch.** | No v1.0.0 GitHub Release is claimed; execute tag workflow and inspect images/artifacts after merge. |
| V-13 | Performance | Benchmark 200 requirements and 1,000 test cases; calculate p95. | **Not executed / no result found.** | Run and publish a reproducible measurement report. |
| V-14 | Clean-machine installability | Time a fresh machine running the Compose startup command. | **Not executed / no timing evidence found.** | Record OS/Docker prerequisites, elapsed time, and any manual intervention. |
| V-15 | End-to-end demonstration | Record login, catalogue, traceability, run, defect lifecycle, metrics, and document export. | **Pass: video recorded and published on the demo site.** | None. |

## 3. Focused test names in the integrated baseline

The following test functions are present in the current `main` test tree and are useful verification anchors:

| Area | Test identifiers |
|---|---|
| Authentication | `test_login_and_me`, `test_login_rejects_bad_credentials`, `test_bad_tokens_are_rejected`, `test_mutations_require_login_and_role` |
| Defect lifecycle | `test_defect_lifecycle_and_history`, `test_transition_roles`, `test_denied_transitions_write_no_history`, `test_postgresql_history_is_append_only` |
| Catalogue / traceability | `test_project_crud`, `test_release_crud`, `test_requirement_crud`, `test_traceability_is_many_to_many_and_replaceable`, `test_traceability_rejects_bad_input`, `test_test_case_and_suite_validation_and_conflicts` |
| Execution | `test_test_run_and_execution_lifecycle`, `test_test_run_validation_and_roles`, `test_defect_close_requires_passed_verification_execution` |
| Metrics / release gate | `test_seed_and_metrics`, `test_release_exit_gate_criteria_waiver_and_status`, `test_release_aggregates_no_fanout_and_first_resolution`, `test_project_and_release_membership_are_distinct` |
| JUnit / Cobertura | `test_import_persists_metadata_mapping_outcomes_and_unmatched_report`, `test_bad_report_rejects_every_result_atomically`, `test_counters_are_computed_from_lines_and_method_lines_are_not_double_counted` |
| Test Plan | `test_test_plan_crud_and_workflow`, `test_test_plan_validation_and_dependents`, `test_test_plan_role_checks`, `test_test_plan_snapshots_and_html_pdf_export`, `test_test_plan_snapshot_isolates_projects` |

PLN-39 and PLN-30 focused test names are in their respective open PR branches and should be checked again after integration.

## 4. Overall V&V conclusion

The integrated baseline has meaningful verification evidence for authentication, catalogues, requirement links, test execution, defect transitions/history, metrics, imports, release criteria, and Test Plan API behavior. Individual open PR branches report successful CI for the next report/security/release increments.

The project is **not yet ready for an unconditional final acceptance statement**. The migration stack must be verified as one chain, report PDFs need target-container inspection, the performance and clean-machine targets need measurements, and the demonstration video must be recorded. The missing FR-REQ-02 report and the original R1–R8 wording also remain traceability actions.

## 5. Standard reference

IEEE SA lists IEEE 1012-2024 as the active *IEEE Standard for System, Software, and Hardware Verification and Validation*, published 22 August 2025 and superseding IEEE 1012-2016. [Official IEEE SA record](https://standards.ieee.org/ieee/1012/7324/).
