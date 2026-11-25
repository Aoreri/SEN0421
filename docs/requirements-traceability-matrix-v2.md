# SDS-06 — Requirements Traceability Matrix (RTM) v2

**Plan item:** PLN-37  
**Version:** 2.0 — Baseline candidate  
**Prepared:** 22 November 2026  
**Companion documents:** `srs.md`, `software-design-description.md`, `test-plan.md`, `test-case-specification-workflow.md`, `metric-definitions.md`

## 1. Purpose and rules

This RTM maps each project-level functional/non-functional requirement to its responsible software module and verification test or measurement. It supplements rather than replaces the course's original R1–R8 identifiers.

**Status meanings:**
- **Integrated:** implementation and referenced tests are present on `main`.
- **In review:** implementation is on an open PR branch; it is not yet an integrated baseline feature.
- **Gap:** the requirement is understood but the feature or evidence is missing.
- **Needs source confirmation:** the original approved requirement text is unavailable; only a provisional project-area mapping is shown.

Test names below are repository test function identifiers unless explicitly described as a planned measurement. A passing test verifies the behavior covered by that test; it does not by itself establish complete standards conformance.

## 2. Course-level R1–R8 matrix (provisional)

| Requirement | Provisional area inferred from the plan/seed | Module / data | Verification evidence | Status |
|---|---|---|---|---|
| R1 | Test Plan / test-document control. PLN-26 explicitly associates Test Plan with R1 and R3. | `app/test_plans.py`, `test_plans`, `test_plan_snapshots`, Jinja2 renderer. | `test_test_plan_crud_and_workflow`; `test_test_plan_snapshots_and_html_pdf_export`. | Integrated on `main`; exact original R1 wording still needs confirmation. |
| R2 | Test suite/case management, traceability, and execution. PLN-16/17/19/20. | `app/projects.py`, `app/runs.py`, `test_suites`, `test_cases`, `test_case_requirements`, `test_runs`, `test_executions`. | `test_test_suite_crud`; `test_test_case_crud_and_specification_fields`; `test_test_case_and_suite_validation_and_conflicts`; `test_test_run_and_execution_lifecycle`. | Integrated; original R2 wording needs confirmation. |
| R3 | Test documentation generation. PLN-26, PLN-30, PLN-39. | Test Plan service now integrated; incident/log and summary-report services are in open PRs. | `test_test_plan_snapshots_and_html_pdf_export`; PR #37 and PR #38 focused report tests. | Test Plan integrated; Incident/Log and Test Summary Report in review; original R3 wording needs confirmation. |
| R4 | Defect lifecycle and verification before closure. PLN-17/20/39. | `main.py`, `runs.py`, `defects`, `defect_history`, `test_executions`, `execution_defects`. | `test_defect_lifecycle_and_history`; `test_defect_close_requires_passed_verification_execution`; `test_all_lifecycle_transitions_and_history`; `test_postgresql_history_is_append_only`. | Core lifecycle and gate integrated; Incident Report is in review; original R4 wording needs confirmation. |
| R5 | Metrics and monitoring. PLN-21/24 and related coverage work. | `metrics.py`, dashboard components, `coverage_imports.py`, metric definitions. | `test_seed_and_metrics`; `test_release_aggregates_no_fanout_and_first_resolution`; `test_period_cohort_and_exclusive_end`; `test_empty_and_legacy_contract`; `test_import_persists_metadata_and_linked_junit_evidence`. | Core metrics/dashboard/coverage integrated; sprint-specific filtering is in PR #34; original R5 wording needs confirmation. |
| R6 | Automated test-result and coverage import. PLN-22/23. | `junit.py`, `junit_imports.py`, `cobertura.py`, `coverage_imports.py`, import snapshot tables. | `test_import_persists_metadata_mapping_outcomes_and_unmatched_report`; `test_other_project_cases_are_reported_unmatched_and_reads_are_scoped`; `test_bad_report_rejects_every_result_atomically`; `test_counters_are_computed_from_lines_and_method_lines_are_not_double_counted`; `test_import_persists_metadata_and_linked_junit_evidence`. | Integrated; original R6 wording needs confirmation. |
| R7 | Release management and exit criteria. PLN-18/21/30. | `projects.py`, `Release`, `release_gate_out`, metrics dashboard, pending Test Summary Report. | `test_release_exit_gate_criteria_waiver_and_status`; `test_release_gate_isolates_projects`; PR #38 summary-report test. | Release gate integrated; summary report in review; original R7 wording needs confirmation. |
| R8 | Original requirement text not present in the inspected migration/SRS source. Security and integrity are documented as separate SRS requirements. | `auth.py`, `access.py` project membership (PLN-40), protected route dependencies, `defect_history` PostgreSQL trigger. | `test_project_members.py` (PLN-40); `test_login_rejects_bad_credentials`; `test_bad_tokens_are_rejected`; `test_mutations_require_login_and_role`; `test_postgresql_history_is_append_only`; PR #39 security checks. | Needs original R8 wording; do not claim exact R8 coverage until confirmed. |

## 3. Functional requirement traceability

| SRS requirement | Responsible module / design element | Verification ID / exact test evidence | Status / gap |
|---|---|---|---|
| FR-AUTH-01 | `app/auth.py`, `users`, login page | `test_login_and_me`; `test_login_rejects_bad_credentials` | Integrated. |
| FR-AUTH-02 | `app/auth.py`, JWT validation | `test_login_and_me`; `test_bad_tokens_are_rejected` | Integrated. |
| FR-AUTH-03 | `auth.py` role dependencies; transition rules | `test_mutations_require_login_and_role`; `test_transition_roles`; `test_catalog_writes_are_role_guarded` | Protected operations integrated; read-endpoint hardening in PR #39. |
| FR-CAT-01 | `projects.py`, `Project` | `test_project_crud`; `test_delete_with_dependents_is_rejected` | Integrated. |
| FR-CAT-02 | `projects.py`, `Release` | `test_release_crud`; `test_duplicate_release_version_conflicts` | Integrated. |
| FR-CAT-03 | `projects.py`, `Requirement` | `test_requirement_crud`; `test_invalid_writes` | Integrated. |
| FR-CASE-01 | `projects.py`, `TestSuite` | `test_test_suite_crud`; `test_test_case_and_suite_validation_and_conflicts` | Integrated. |
| FR-CASE-02 | `projects.py`, `TestCase` | `test_test_case_crud_and_specification_fields`; `test_test_case_and_suite_validation_and_conflicts` | Integrated. |
| FR-TRACE-01 | `test_case_requirements` M:N relation | `test_traceability_is_many_to_many_and_replaceable`; `test_seed_traceability_matches_test_case_requirement` | Integrated. |
| FR-TRACE-02 | relationship validation in `projects.py` | `test_traceability_rejects_bad_input`; `test_test_case_and_suite_validation_and_conflicts` | Integrated. |
| FR-REQ-01 | `resolve_case_relations` in `projects.py` | `test_test_case_and_suite_validation_and_conflicts` (empty-link create/update returns 422) | Integrated. |
| FR-REQ-02 | Proposed release-specific traceability report | No matching API/test in integrated `main` | Gap; requires implementation and performance measurement. |
| FR-RUN-01 | `runs.py`, `TestRun`, `TestExecution` | `test_test_run_and_execution_lifecycle`; `test_test_run_validation_and_roles` | Integrated. |
| FR-RUN-02 | `runs.py` execution result endpoint | `test_test_run_and_execution_lifecycle` | Integrated. |
| FR-RUN-03 | `execution_defects` and execution defect route | `test_test_run_and_execution_lifecycle`; `test_defect_close_requires_passed_verification_execution` | Integrated. |
| FR-DEF-01 | Defect creation in `main.py` | `test_defect_lifecycle_and_history`; `test_validation` | Integrated. |
| FR-DEF-02 | `DefectTransition`, role rules | `test_transition_roles`; `test_denied_transitions_write_no_history`; `test_unknown_status_is_rejected_without_history_change` | Integrated. |
| FR-DEF-03 | PostgreSQL-protected `defect_history` | `test_defect_lifecycle_and_history`; `test_postgresql_history_is_append_only` | Integrated. |
| FR-DEF-04 | Verification gate in defect transition flow | `test_defect_close_requires_passed_verification_execution` | Integrated. |
| FR-MET-01 | `main.py` `/api/metrics` | `test_seed_and_metrics`; `test_metrics_handle_unexecuted_tests`; `test_metrics_handle_no_test_cases` | Integrated. |
| FR-MET-02 | `metrics.py` `/api/metrics/expanded` | `test_release_aggregates_no_fanout_and_first_resolution`; `test_period_cohort_and_exclusive_end`; `test_project_and_release_membership_are_distinct`; `test_reopen_day_is_visible_without_double_counting_active_defects` | Integrated. |
| FR-REL-01/02/03 | `projects.py`, `Release`, release gate | `test_release_exit_gate_criteria_waiver_and_status`; `test_release_gate_isolates_projects` | Integrated. |
| FR-IMP-01 | `junit.py`, `junit_imports.py` | `test_import_persists_metadata_mapping_outcomes_and_unmatched_report`; `test_bad_report_rejects_every_result_atomically`; `test_repeated_case_keys_and_repeated_imports_are_not_silently_dropped` | Integrated. |
| FR-IMP-02 | `cobertura.py`, `coverage_imports.py` | `test_counters_are_computed_from_lines_and_method_lines_are_not_double_counted`; `test_invalid_or_inconsistent_reports_are_rejected`; `test_import_persists_metadata_and_linked_junit_evidence` | Integrated. |
| FR-PLAN-01 | `test_plans.py`, `TestPlan` | `test_test_plan_crud_and_workflow`; `test_test_plan_validation_and_dependents` | Integrated. |
| FR-PLAN-02 | `TestPlanSnapshot` | `test_test_plan_snapshots_and_html_pdf_export`; `test_test_plan_snapshot_isolates_projects` | Integrated. |
| FR-PLAN-03 | Jinja2 Test Plan renderer and export route | `test_test_plan_snapshots_and_html_pdf_export` | API response implemented; target-container WeasyPrint rendering/visual quality still requires evidence. |
| FR-DOC-01 | `test_reports.py`, incident/log templates | PR #37 focused tests: `test_incident_report_snapshots_and_html_pdf_export`; `test_test_log_snapshots_and_html_pdf_export` | In review; not integrated on `main`. |
| FR-DOC-02 | `summary_reports.py`, summary template | PR #38 focused `summary_report` test | In review; not integrated on `main`. |
| FR-SPR-01 | `Sprint` model, sprint CRUD, metrics filter | PR #34 PLN-28 | In review; not integrated on `main`. |
| FR-REL-04 | `.github/workflows/release.yml`, release bundle generator | PR #40 PLN-36 | In review; no v1.0.0 release published yet. |

## 4. Non-functional requirement traceability

| SRS requirement | Module / quality control | Verification evidence | Status |
|---|---|---|---|
| NFR-REQ-01 | Traceability query/report and performance test harness | Required dataset: 200 requirements, 1,000 test cases; repeated timing with p95 calculation | Target only; no measured report result. |
| NFR-REQ-02 | `docker-compose.yml`, service health checks, user guide | Clean-machine run of `docker compose up --build -d --wait`; elapsed time and manual steps recorded | Target only; demo timing not recorded. |
| NFR-SEC-01 | bcrypt, HS256 JWT, role dependencies, restricted operations | `test_login_rejects_bad_credentials`; `test_bad_tokens_are_rejected`; `test_mutations_require_login_and_role`; PR #39 Bandit/npm audit checks | Core control integrated; GET endpoint hardening/security scan PR remains in review. |
| NFR-REL-01 | `DefectHistory`, PostgreSQL trigger | `test_postgresql_history_is_append_only`; lifecycle/history integration tests | Integrated. |
| NFR-MAINT-01 | Layered modules, Ruff, mypy, pytest, frontend checks | CI jobs and PR checks | Checks reported successful; integrated release baseline must be re-run after final merges. |
| NFR-TRACE-01 | `test_case_requirements`, API validation | `test_traceability_is_many_to_many_and_replaceable`; `test_traceability_rejects_bad_input`; `test_test_case_and_suite_validation_and_conflicts` | Integrated. |
| NFR-OBS-01 | Metrics and report payloads | Metric API tests; Test Plan snapshot/export tests; report PR tests | Partial; report modules still in review. |

## 5. Coverage gaps and closure actions

1. Obtain the original approved R1–R8 wording, update the R1–R8 mapping, and obtain course-owner confirmation.
2. Implement FR-REQ-02 and add API, integration, and performance tests.
3. Measure NFR-REQ-01 using the required 200/1,000 dataset and report the repeated sample and p95 calculation.
4. Measure NFR-REQ-02 on a clean machine and attach elapsed-time evidence.
5. Merge report/security/sprint/release PRs only after review; then rerun integrated checks and verify the full Alembic chain from revision `0010`.
6. Verify target-container PDF output and manually inspect multi-page files before claiming report-format acceptance.
