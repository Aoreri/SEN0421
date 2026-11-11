# SDS-06 — Definition of Done (DoD)

**Work package:** PLN-02  
**Version:** 0.1 — Draft for team review  
**Prepared:** 11 November 2026

A work item may be marked **Done** only when all applicable checks below are satisfied and the evidence is linked from its issue or pull request. A check may be marked Not Applicable only with a short reason.

## 1. Requirements and design

- [ ] The change is linked to an approved requirement (`R1`–`R8` or a new SRS ID) and a plan item/work package (`PLN-xx` / `WP-xx`).
- [ ] The requirement is clear, testable, and consistent with the SRS.
- [ ] The relevant test case or verification method is identified.
- [ ] Architecture, data model, or API documentation is updated when the change affects those areas.
- [ ] Any tailoring, limitation, or unimplemented behavior is explicitly recorded.

## 2. Implementation quality

- [ ] The change is implemented in the appropriate backend, frontend, or documentation area.
- [ ] Input validation and expected error responses are present for affected API operations.
- [ ] Server-side authorization is applied to protected operations; UI-only hiding is not treated as security.
- [ ] Existing defect transition rules and append-only history behavior remain intact.
- [ ] Any database schema change is accompanied by a new Alembic migration.
- [ ] No credentials, tokens, `.env` files, personal data, or generated coverage outputs are committed.

## 3. Verification

- [ ] Focused tests cover the changed behavior, including relevant negative/authorization cases.
- [ ] Backend checks pass: `ruff check .`, `mypy app`, and `python -m pytest -q` (or the equivalent CI commands).
- [ ] PostgreSQL-specific behavior is tested against a disposable PostgreSQL database when applicable.
- [ ] Frontend checks pass: `npm run lint`, `npm run typecheck`, and `npm run build` when frontend files are affected.
- [ ] The relevant GitHub Actions CI workflow completes successfully.
- [ ] Performance, portability, or data-integrity targets are supported by measured/test evidence when the change claims to satisfy them.

## 4. Review and repository process

- [ ] Work is committed to a plan-specific branch; `main` is not modified directly.
- [ ] Pull request title includes the plan item ID.
- [ ] Pull request description completes every section in `.github/pull_request_template.md` and includes the required `Agent:` line.
- [ ] At least one appropriate team review is received before merge, following the repository contribution rules.
- [ ] Review comments are resolved or explicitly accepted by the reviewer.
- [ ] The final diff is limited to the stated plan item; unrelated work is not mixed into the PR.

## 5. Documentation and handover

- [ ] README instructions remain accurate after the change.
- [ ] New endpoints, configuration variables, migration steps, test commands, and known limitations are documented where relevant.
- [ ] The PR provides verification evidence and identifies database/deployment impact (or states `None`).
- [ ] The work item, SRS, test plan, traceability, and risk register are updated when the change affects them.

## 6. Documentation-only work

For documentation-only plan items, code tests may be Not Applicable. The reviewer must still confirm that the document matches the progress report, current repository behavior, and cited sources; that draft assumptions and open verification items are visible; and that no unverified standards clause or conformance claim has been introduced.
