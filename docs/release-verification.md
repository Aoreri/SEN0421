# PLN-36 — shared v1.0 release preparation

Esra Kaya / Caner Serbest · target 26.11.2026 · ISO/IEC/IEEE 12207
Configuration Management and Release Management.

This branch integrates Caner's original PR #40 with its authorship intact,
then completes Esra's verification/publication handoff. Its PR base is main.
It does not create a tag, publish a Release, change live project data or
close anyone else's PR.

## Corrections in the shared candidate

- FastAPI, frontend package and both lockfile version fields now agree on
  1.0.0. This is candidate metadata, not a claim that v1.0.0 was published.
- The original generator's demo-project preview remains available without
  evidence arguments. Its migrated demo statuses are unchanged. At original
  #40 commit 2f2725614597baecd15fc0bd4c35881a987509cd its gate was false:
  75% pass rate and 62.5% requirement coverage against 80% minima.
- The publication path now uses the application's **actual PostgreSQL pytest
  JUnit/Cobertura output**, not that demo preview. A full candidate SHA and
  SHA-256 hashes bind the inputs in test-evidence.json. Changed files or
  mismatched commit claims are rejected. The workflow creates this record
  immediately after successfully testing its own checkout; arbitrary old
  downloaded artifacts are not used as publication inputs.
- No failed/skipped result is converted to Passed. Unmapped tests contribute
  to totals but not requirement coverage. Named executed acceptance witnesses
  define requirement coverage separately from code coverage.

## Report population and acceptance witnesses

The new report explicitly describes SDS-06's own verification suite. It does
not certify a real user's open Critical defects or use demo database statuses
as proof of product quality. R1–R8 associations below are explicit project-plan
acceptance mappings, not deductions from the seed migration's incomplete TC
links. Full names are in backend/scripts/release_evidence.py.

| Requirement area | Executed witness |
| --- | --- |
| R1 Test Plan control | test_test_plan_crud_and_workflow |
| R2 Cases / execution | test_test_case_crud_and_specification_fields; test_test_run_and_execution_lifecycle |
| R3 Documents | test_test_plan_snapshots_and_html_pdf_export |
| R4 Defect workflow | test_defect_lifecycle_and_history; test_defect_close_requires_passed_verification_execution |
| R5 Metrics | test_release_aggregates_no_fanout_and_first_resolution |
| R6 JUnit import | test_import_persists_metadata_mapping_outcomes_and_unmatched_report |
| R7 Exit criteria | test_release_exit_gate_criteria_waiver_and_status |
| R8 Access / immutable history | test_mutations_require_login_and_role; test_postgresql_history_is_append_only |

A requirement is verified only if every named witness exists and all its
reported parameter variants passed. Missing or skipped witnesses remain
unverified. Thresholds: no failed tests, at least one passed test, ≥80% of
requirements verified, and ≥80% code line **and** branch coverage. The pytest
command must also exit successfully. This is a release-verification assessment;
it never alters a project's configured release gate or defect history.

The HTML/PDF/JSON report includes scope, candidate, full counters, per-requirement
witnesses/missing tests, nonpassing results, separate code coverage and explicit
exit criteria. WeasyPrint must render a real PDF in the publication path;
render failure fails the job. The preview retains Caner's existing fallback.

## Run a complete dry run before merging/publishing

Use **Actions → Release v1.0 → Run workflow**, select the prepared
`feature/pln-36-release-verification` branch and version `v1.0.0`.
Manual runs and this feature branch's code pushes run only the candidate job.
The publish job is skipped. The candidate:

1. Validates source versions; runs ruff/mypy and all backend tests on a
   disposable PostgreSQL 16 service with real JUnit/Cobertura output.
2. Runs frontend npm ci, lint, typecheck and build.
3. Generates the evidence-backed Test Summary Report and release notes.
4. Builds backend/frontend production Dockerfiles, captures their actual local
   image IDs and versioned tags, and saves both images in one compressed tar.
5. Verifies source metadata, report provenance/percentages/exit gate, attachment
   signatures and image identities. Creates release-manifest.json/SHA256SUMS.
6. Uploads the exact bundle and image archive as verified-release-package
   (14-day retention). It does not push to a registry or publish a Release.

The separate Release verifier tests workflow tests synthetic valid/invalid
contracts only; it is not proof that the actual candidate passed a dry run.

## Publish only after approved integration into main

After the necessary approved PRs merge, rerun the complete candidate checks on
that exact final main commit, including the team's E2E/security/performance
requirements. With the responsible release owner's approval, create v1.0.0
on that commit. Never move/force-push a published tag.

Tag-triggered publication verifies the tagged commit is an ancestor of main.
Its candidate job runs again on that exact tagged checkout. The dependent
publish job downloads the already verified package, rechecks every checksum,
loads and pushes those exact saved images, and attaches those exact report
bytes plus evidence/manifest/checksums to GitHub Release. It never regenerates
the report or rebuilds images after verification. Publication permissions are
restricted to that tag-only job. No latest tag is moved by this workflow.

If tests, metadata, renderer, build or integrity checks fail, the candidate
fails and publication cannot run. A dry run is not publication authorization.
No tag or Release has been created as part of this implementation task.

## Local generation and independent integrity checks

From backend, after actual pytest --junitxml=junit.xml --cov=app
--cov-report=xml:coverage.xml, create test-evidence.json with exactly commit,
junit_sha256 and coverage_sha256 (the workflow shows the reproducible command).
Then:

```sh
python scripts/generate_release_report.py --version v1.0.0 --commit FULL_CANDIDATE_SHA \
  --junit junit.xml --coverage coverage.xml --evidence test-evidence.json \
  --output-dir ../release-bundle
cp junit.xml coverage.xml test-evidence.json ../release-bundle/
```

Use repository-root scripts/verify_release.py with --root, --bundle, --images,
--version, --commit and a fresh --output directory. Image JSON must be captured
from docker image inspect, never guessed. Existing manifest/checksum outputs
are rejected. The manifest identifies local image IDs, not registry manifest
digests. PDF signature checks do not establish visual/typographical equivalence.

No .env or deployment data is read. PostgreSQL test fixtures reset only the
job's disposable database. Generated PDF/release bundles are artifacts, not
committed course reports. Original demo preview output is diagnostic only.
