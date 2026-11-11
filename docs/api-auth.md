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
| `POST /api/defects` | `Admin`, `Test Lead`, `Tester` |
| `POST /api/defects/{id}/transition` | depends on the transition, see below |
| `POST`, `PUT`, `DELETE` on `/api/projects`, `/api/releases`, `/api/requirements` | `Admin`, `Test Lead` |
| `PUT /api/requirements/{id}/test-cases` | `Admin`, `Test Lead`, `Tester` |

`GET` endpoints stay public. A token is optional on them, but an invalid or expired one gets `401`.

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

## Server configuration

`JWT_SECRET` signs the tokens. If unset, the server generates a random secret at startup, so tokens
stop working after a restart. Set it when running more than one worker.

## Demo users

`admin` (Admin), `testlead` (Test Lead), `tester` (Tester), `developer` (Developer).
The password for all of them is `demo1234`.
