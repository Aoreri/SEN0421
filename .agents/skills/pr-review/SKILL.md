---
name: pr-review
description: Review a teammate's pull request against the SDS-06 plan and standards, then approve or request changes. Use only when the developer asks to review a PR.
---

# PR review

Review a pull request for what CI cannot see, then post one review. Post only
after the developer has seen the preview, unless they said to post directly.

## 1. Gather

```sh
gh pr view <n> --json title,body,author,isCrossRepository,headRefOid,files,mergeable
gh pr checks <n>
git fetch origin pull/<n>/head:pr<n>      # works for fork PRs too; branch names do not
git diff --stat main...pr<n>
git diff main...pr<n> -- . ':!frontend/package-lock.json'
```

On Git Bash, set `MSYS_NO_PATHCONV=1` before `git show <rev>:<path>`.

## 2. CI

Do not rerun lint, tests, or build by hand when CI ran on the PR head and
passed. If CI did not run in this repository (fork PRs may run only in the
fork), check the fork's run for the same `headRefOid` with
`gh api repos/<owner>/<repo>/actions/runs`, or run the commands from
AGENTS.md > Checks in a worktree under the scratchpad, never in the main
checkout. Say which of the two you did.

## 3. Review

Read the changed code and the code it calls. Check, in this order:

1. **Conflicts with other open PRs.** For every open PR, run
   `git merge-tree --write-tree --name-only pr<n> pr<m>`. Name the conflicting
   files and propose a merge order.
2. **Plan.** The change matches the `PLN-xx` / `WP-xx` in the body and the
   owner in the progress report. Flag work that belongs to another plan item.
3. **Domain rules** from AGENTS.md: schema changes have a new Alembic
   migration, merged migrations are untouched, defect transitions are still
   rejected server-side, `defect_history` gets no UPDATE/DELETE path, and
   requirement links on test cases survive.
4. **Correctness.** Bugs, missing error handling at the API boundary, tests
   that assert wiring instead of behavior, missing tests for new behavior.
5. **Surfaces.** API changes reach `frontend/src/api.ts`; README still true.

Every finding needs a file and line and a concrete failure. Drop anything you
cannot tie to one. Style preferences the linters accept are nits at most.

## 4. Decide

- **Approve** when nothing blocks merging; list nits inline and say they do
  not block.
- **Request changes** only for a concrete bug, a broken domain rule, a missing
  migration, or a conflict that needs the author's action.
- Never push commits to the author's branch; leave the fix to them.

## 5. Post

Write in English and use the `leaving-pr-comments` format on the review body
and on every inline comment. Body: verdict first, then what was verified
(CI or local commands with results), then merge order if it matters. Inline
comments go on the exact `RIGHT`-side line; check line numbers with
`git show pr<n>:<path> | sed -n '<line>p'`.

Build the review as JSON in the scratchpad and post it in one call:

```sh
gh api -X POST repos/<owner>/<repo>/pulls/<n>/reviews --input review.json
```

`review.json` holds `event` (`APPROVE` or `REQUEST_CHANGES`), `body`, and
`comments` (`path`, `line`, `side`, `body`). Report the returned review URL.
