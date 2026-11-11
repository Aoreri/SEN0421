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
| `POST /api/defects/{id}/transition` | any logged-in user |

`GET` endpoints stay public.

## Server configuration

`JWT_SECRET` signs the tokens. If unset, the server generates a random secret at startup, so tokens
stop working after a restart. Set it when running more than one worker.

## Demo users

`admin` (Admin), `testlead` (Test Lead), `tester` (Tester), `developer` (Developer).
The password for all of them is `demo1234`.
