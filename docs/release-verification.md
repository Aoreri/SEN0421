# PLN-36 — Esra Kaya: v1.0 candidate verification

Target: 26.11.2026 · ISO/IEC/IEEE 12207 Configuration Management / Release Management.

Caner/Aoreri's [PR #40](https://github.com/Aoreri/SEN0421/pull/40) supplies the
Test Summary Report generator and publication workflow. This contribution
provides executable candidate acceptance checks and checksum/manifest creation.
It targets `main` independently; it does not copy or replace that PR's publisher.

## What this verifies

`scripts/verify_release.py` checks:

- Stable version syntax and a full candidate commit SHA.
- FastAPI, frontend package and both frontend lockfile version fields agree.
- Required Test Summary Report PDF, HTML, JSON and release notes exist as
  nonempty regular files, with no symbolic links.
- Report and notes identify the expected version/commit; report totals and
  percentages are valid and internally consistent, and the exit gate passed.
- Two actual locally built backend/frontend image IDs and versioned tags.
- SHA-256 digests for every asset. A successful verification writes
  `release-manifest.json` and `SHA256SUMS` only after all checks pass.

Use a fresh output directory: existing manifest/checksum files are rejected,
so a failed rerun cannot silently relabel an earlier manifest.

The manifest identifies local Docker image IDs, not registry manifest digests.
PDF signature/EOF checks do not prove visual layout. A report from an isolated
seed database is not evidence that the real release's tests passed. Candidate
verification is necessary preparation, not authorization to release.

## Use after both contributions merge

Run **Actions → Release readiness (PLN-36) → Run workflow**, version `v1.0.0`.
The manual candidate job checks out the repository's actual `main`, validates
its metadata, invokes Caner's generator in its isolated temporary database,
builds both production Dockerfiles locally and verifies the resulting bundle.
It has `contents: read` only. It neither creates tags/releases nor logs in to
or pushes images to a registry. A failed check fails the candidate job; no
`verified-release-candidate` artifact is uploaded.

PR/feature-branch runs exercise the validator with explicitly synthetic unit
fixtures. They do not attest readiness of the repository's current main.
For a local already-built candidate:

```sh
python scripts/verify_release.py --root /path/to/candidate \
  --bundle /path/to/report-output --images /path/to/built-images.json \
  --version v1.0.0 --commit FULL_40_CHARACTER_SHA --output /path/to/report-output
```

The image JSON is a list with `component`, `tag` and `image_id`; the workflow
creates it from `docker image inspect`, never by guessing a digest.
Copy all four assets plus the manifest and SHA256SUMS into one directory before
running `sha256sum --check SHA256SUMS`. Keep the original verified files intact.

## Publication handoff

1. Merge the approved PLN-36 contributions into `main`. Resolve conflicts with
   other release dependencies there; never target another feature PR's branch.
2. Check CI, E2E, performance/security evidence and migrations on the actual
   chosen commit. Do not substitute an unrelated earlier green run.
3. Run candidate verification on main. If any check fails, fix the responsible
   contribution and repeat. Never change report values just to pass this check.
4. With the responsible team member's release approval, tag that exact main
   commit `v1.0.0` and run the publisher from #40. Confirm both registry images
   and the PDF/HTML/JSON report assets and release notes are present.
5. If the publisher regenerates reports or rebuilds images, run this verifier
   again on those actual files and image records immediately before uploading.
   Report generation timestamps and rebuilt image IDs can differ; never reuse
   an earlier manifest for changed bytes. Attach the resulting manifest and
   checksums beside those exact assets and verify the published downloads.
   This verification
   workflow is separate from #40 and is not automatically enforced by its
   publisher; the release operator must check it before creating the tag.
6. Record the actual GitHub Release URL and tag commit as delivery evidence.
   Do not describe the release as published before this happens.

The tag is created only after the final candidate is chosen. Never move or
force-push an already published tag; correct an erroneous publication through
an agreed new patch version. Never delete a shared database to create a report.

## Current integration observations (24.11.2026)

At reviewed PR #40 commit `2f2725614597baecd15fc0bd4c35881a987509cd`,
`frontend/package.json` is changed to 1.0.0 but its package-lock version fields
are not updated. The validator correctly treats this as a blocker. The report
producer was run locally in its real isolated database. Its report shows
75% pass rate against an 80% minimum, and 62.5% requirement coverage against
an 80% minimum; `gate_passed` is false. These are demo-seed results, not the
project CI test results. They must not be edited or described as release-ready. The current upstream main remains 0.1.0 and
contains no report generator, so it is not yet a v1.0 release candidate.
These observations do not modify Caner's branch or claim a release exists.
