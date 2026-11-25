# Authentication API (PLN-05)

Send the token on protected requests as `Authorization: Bearer <access_token>`.
Tokens expire after 8 hours; on `401`, send the user back to login.

Roles (exact strings): `Admin`, `Test Lead`, `Tester`, `Developer`.

## `POST /api/auth/login`

Request:

```json
{ "username": "tester", "password": "demo1234" }
```

`200`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": { "id": 3, "username": "tester", "role": "Tester" }
}
```

`401` on a wrong username or password, with the same message for both.

## `GET /api/auth/me`

`200`: `{ "id": 3, "username": "tester", "role": "Tester" }`

`401` if the token is missing, invalid, or expired.

## Errors

Errors use FastAPI's format: `{ "detail": "<message>" }`.
`401` means not logged in; `403` means logged in with the wrong role.

## Protected endpoints

| Endpoint | Allowed |
| --- | --- |
| `GET /api/health`, `POST /api/auth/login` | Public |
| All other `GET` read endpoints (`/api/defects`, `/api/defects/{id}/history`, `/api/metrics`, `/api/metrics/expanded`, `/api/projects*`, `/api/releases*`, `/api/requirements*`, `/api/test-suites*`, `/api/test-cases*`, `/api/test-runs*`, `/api/test-plans*`) | Any authenticated role (`Admin`, `Test Lead`, `Tester`, `Developer`) |
| `POST /api/defects` | `Admin`, `Test Lead`, `Tester` |
| `GET /api/users`, `GET /api/projects/{id}/members`, `PUT`/`DELETE /api/projects/{id}/members/{user_id}` | `Admin`, `Test Lead` |
| `POST /api/defects/{id}/transition` | depends on the transition, see below |
| `POST`, `PUT`, `DELETE` on `/api/projects`, `/api/releases`, `/api/sprints`, `/api/requirements`, `/api/test-suites` | `Admin`, `Test Lead` |
| `PUT /api/releases/{id}/criteria`, `POST`/`DELETE /api/releases/{id}/waiver`, `PUT /api/releases/{id}/status` | `Admin`, `Test Lead` |
| `POST`, `PUT`, `DELETE` on `/api/test-cases` | `Admin`, `Test Lead`, `Tester` |
| `PUT /api/requirements/{id}/test-cases`, `PUT /api/test-cases/{id}/requirements` | `Admin`, `Test Lead`, `Tester` |
| `POST /api/test-runs`, `POST`/`PUT /api/test-runs/{id}/executions/{exec_id}`, `POST /api/test-runs/{id}/executions/{exec_id}/defects` | `Admin`, `Test Lead`, `Tester` |
| `POST`, `PUT`, `DELETE` on `/api/test-plans`, `PUT /api/test-plans/{id}/status` | `Admin`, `Test Lead` |
| `POST /api/test-plans/{id}/snapshots` | `Admin`, `Test Lead`, `Tester` |
| `POST /api/defects/{id}/incident-report/snapshots`, `POST /api/test-runs/{id}/test-log/snapshots` | `Admin`, `Test Lead`, `Tester` |
| `POST /api/releases/{id}/summary-report/snapshots` | `Admin`, `Test Lead`, `Tester` |

All read (`GET`) endpoints except `/api/health` require a valid bearer token (PLN-29); missing, invalid, or expired tokens receive `401`.

## Defect transitions

Rules are stored in the `defect_transitions` table. The seeded rules are:

| From | To | Allowed |
| --- | --- | --- |
| `Open` | `In Progress` | `Developer`, `Admin` |
| `In Progress` | `Resolved` | `Developer`, `Admin` |
| `Resolved` | `Closed` | `Tester`, `Test Lead`, `Admin` |
| `Resolved` | `Open` (Reopen) | `Tester`, `Test Lead`, `Admin` |
| `Closed` | `Open` (Reopen) | `Tester`, `Test Lead`, `Admin` |

`POST /api/defects/{id}/transition` with `{ "to": "<status>" }` returns `409` if no rule exists for
that move and `403` if the rule exists but excludes the caller's role.

A defect's `allowed` field lists only the moves the current token may make, and is `[]` without a
token. Offer exactly these moves in the UI.

## Project membership (PLN-40)

Roles decide what a user may do; project membership decides where. `Admin` and `Test Lead` see
every project. `Tester` and `Developer` see and change only the records of projects they are
members of: lists leave other projects out, and reading or changing one of their records returns
`404`, so a non-member cannot tell whether it exists. A test case belongs to the projects of its
requirements and suite; a defect belongs to the projects of its test case and linked runs. A
defect with no test case and no run belongs to no project and stays visible to everyone.

`PUT /api/projects/{id}/members/{user_id}` adds a member and is idempotent;
`DELETE` removes one. Both return the project's member list. Adding an `Admin` or `Test Lead`
returns `422`, because those roles already see every project. Migration `0012_pln40` made every
existing Tester and Developer a member of every existing project, so no access was lost.

## Server configuration

`JWT_SECRET` signs the tokens. If unset, the server generates a random secret at startup, so tokens
stop working after a restart. Set it when running more than one worker.

## Demo users

`admin` (Admin), `testlead` (Test Lead), `tester` (Tester), `developer` (Developer).
The password for all of them is `demo1234`.
