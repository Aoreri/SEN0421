# SDS-06 agent rules

SDS-06 is the Agile Test and Defect Tracking System for the Software
Development with Standards course (Istanbul Kültür University). It follows the
ISO/IEC/IEEE 12207 life-cycle process model and produces IEEE 829 documents
mapped to ISO/IEC/IEEE 29119-2 (test processes) and 29119-3 (test
documentation). Read the root README before changing code.

Treat these rules as good defaults; the developer's explicit instructions
override them. If a rule fights the task in front of you, say so and get
sign-off before breaking it. Prefer the smallest change that makes the correct
behavior unsurprising: no speculative abstractions, no scope creep.

## Layout

- `backend/`: FastAPI REST API. SQLAlchemy models in `app/models.py`, Alembic
  migrations in `alembic/versions/`, tests in `tests/`.
- `frontend/`: React + TypeScript (Vite). All API calls go through
  `src/api.ts`.
- `docker-compose.yml`: local PostgreSQL for development.

## Standards traceability

Every change must be traceable to the plan in the bi-weekly progress report.
This is how the project's ISO/IEC/IEEE 12207 work products are graded.

- Name the plan item (`PLN-xx`) or work package (`WP-xx`) in the branch name,
  the PR title, and the PR description. If a change fits none, ask before
  starting it.
- State the standard and clause the change serves, as the report does, for
  example "ISO/IEC/IEEE 12207 - Implementation" or "29119-2 - Test Incident
  Reporting".
- Requirements are `R1`-`R8`. Test cases reference their requirement; keep that
  link intact when changing test-case data or schemas.

## Domain rules

These are requirements from the research report, not implementation details.

- **Defect life cycle (WP-04).** `Open → In Progress → Resolved → Closed`, with
  Reopen from `Resolved` or `Closed`. The server rejects every other
  transition; the frontend only offers what the API returns in `allowed`.
- **Immutable history.** `defect_history` is append-only, enforced by a
  PostgreSQL trigger. Never add UPDATE or DELETE paths, and record every status
  change, including creation.
- **Schema changes ship with an Alembic migration.** Never edit a migration
  that has been merged to `main`; add a new one.
- **IEEE 829 terms.** Use the standard names (Test Plan, Test Case
  Specification, Test Incident Report, Test Summary Report) in code, UI, and
  docs, and keep the 29119-3 mapping in mind when adding a document type.

## Ways to hurt yourself

1. **Killing by pattern.** Never `Stop-Process -Name`, `taskkill /IM`, or
   `pkill -f`. Stop only a PID you captured when you started the process.
2. **Touching real data.** Run tests and migrations against throwaway
   databases only. Never read, print, or commit `.env` files or secrets.
3. **Committing reports.** The progress and research reports (`*.docx`,
   `*.pdf`) stay out of the repository.

## Cover every surface

Before calling work done, walk this list and say which entries applied:

- **Contracts.** An API change must be followed through `frontend/src/api.ts`,
  its callers, and the tests.
- **Schema.** A model change needs a migration and a passing
  `alembic upgrade head` on PostgreSQL, not only SQLite.
- **Reverse states.** If you added a way in, add the way out and the way to see
  it.
- **Docs.** Check whether the change makes the README inaccurate and fix it.

## Keep context small

- For open-ended asks, first reply with a numbered list (`file:line`, one line
  each) and stop until the developer picks.
- Start diffs with `git diff --stat`, skip lockfiles, and pipe long test or
  build output through `tail -n 60`.
- Do not `sleep`, poll, or write `until` loops for CI, containers, or a person.
  Run long jobs in the background and act on the completion event.

## Checks

Run before every push:

```sh
cd backend && ruff check . && mypy app && python -m pytest -q
cd frontend && npm run lint && npm run typecheck && npm run build
```

CI runs the same commands (`.github/workflows/ci.yml`). Tests default to a
temporary SQLite database; set `DATABASE_URL=postgresql+psycopg://...` to run
them on PostgreSQL after a schema change.

- Backend behavior changes ship with focused tests for that behavior.
- Test observable behavior, not wiring. Never wait on `sleep` in tests.
- Do not verify with a browser unless the developer agrees.

## Branches and pull requests

`main` is protected: every change goes through a pull request with one
approving review. Never push directly to `main`.

- Branch names: `feature/pln-04-postgres`, `fix/pln-07-transition-roles`.
- PR titles in plain English with the plan item: `PLN-04: move demo data to
  PostgreSQL`.
- PR body: fill every section of `.github/pull_request_template.md`. The
  `PR description` CI check rejects missing or empty sections and a missing
  `Agent:` line.
- End the body with `Agent: <model> via <harness>` (for example
  `Agent: Claude Opus 5.5 via Claude Code`), or `Agent: none` if no agent was
  used.
- One concern per PR. If the description says "also", split it.
- Do not commit plans, research notes, or agent scratch files.

## Skills

Project skills live in `.agents/skills/`; `.claude/skills` is a symlink to it
so Claude Code and Codex share them, and `CLAUDE.md` is a symlink to this file.
On Windows, enable Developer Mode and clone with `git config core.symlinks
true`, or git writes the links as text files. To repair a checkout: set the
option, delete the two links, and run `git checkout -- CLAUDE.md
.claude/skills`.

- `leaving-pr-comments`: format for every comment an agent posts on GitHub on
  a developer's behalf.

## Documentation

- Document decisions and traps that are hard to discover from the source.
  Explain local behavior in a code comment instead.
- When a documented decision changes, rewrite the old text rather than
  appending a second account.
