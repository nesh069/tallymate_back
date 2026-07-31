## README

# TallyMate Accounts & Friends API

Flask backend for account authentication and user friendships. It uses SQLAlchemy, JWT access tokens, and `bcrypt` password hashing.

## Run locally

Create a virtual environment, install dependencies, and set a real secret before starting the service:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET_KEY='replace-with-a-long-random-secret'
flask --app app run
```

`DATABASE_URL` is optional and defaults to `sqlite:///tallymate.db`. For PostgreSQL, set it to a SQLAlchemy PostgreSQL URL. The app factory is `app.create_app`.

## API contract

Interactive API documentation (Swagger UI) is served at `/apidocs` in every
environment — including the deployed Render service. All request bodies are
JSON. Protected endpoints require `Authorization: Bearer <access_token>`.
Timestamps are ISO 8601 strings. Errors use `{ "error": "..." }`.

### Authentication

| Method | Path | Auth | Request body | Success response |
| --- | --- | --- | --- | --- |
| POST | `/auth/signup` | No | `{ "name": "Ada", "email": "ada@example.com", "password": "password123" }` | `201 { "user": User, "access_token": "..." }` |
| POST | `/auth/login` | No | `{ "email": "ada@example.com", "password": "password123" }` | `200 { "user": User, "access_token": "...", "refresh_token": "..." }` |
| GET | `/auth/me` | Yes | none | `200 { "user": User }` |

`User` has this shape:

```json
{
  "id": 1,
  "name": "Ada",
  "email": "ada@example.com",
  "created_at": "2026-07-30T10:15:00+00:00"
}
```

Signup rejects invalid input with `400` and duplicate emails with `409`. Login returns `401` for an unknown email or bad password. A missing or invalid JWT on protected routes returns `401`.

### Friends

| Method | Path | Auth | Request body | Success response |
| --- | --- | --- | --- | --- |
| POST | `/friends/add` | Yes | `{ "email": "grace@example.com" }` | `201 { "message": "Friend request sent.", "friend_request": FriendRequest }` |
| POST | `/friends/accept/<request_id>` | Yes | none | `200 { "message": "Friend request accepted.", "friend": User }` |
| GET | `/friends` | Yes | none | `200 { "friends": [User] }` |
| DELETE | `/friends/<friend_user_id>` | Yes | none | `204` with no body |

`FriendRequest` is directional: `user_id` sent the request and `friend_id` received it. Its status is either `pending` or `accepted`.

```json
{
  "id": 7,
  "user_id": 1,
  "friend_id": 2,
  "status": "pending",
  "created_at": "2026-07-30T10:20:00+00:00"
}
```

Only the recipient can accept a pending request. Sending a request to yourself is `400`; a nonexistent email or request is `404`; a duplicate/reversed request or repeat acceptance is `409`; accepting someone else's request is `403`. Removing a friend uses the other user's id and returns `404` unless an accepted friendship exists.

## Tests

```bash
pytest
```

The suite covers each endpoint's main success path plus invalid credentials, duplicate emails/requests, authorization failures, invalid friend operations, acceptance ownership, and removal failures.

# TallyMate Backend

Flask REST API for TallyMate. This section documents the **Expenses** feature (Member 3).
Other sections (Accounts & Friends, Groups, Balances & Settle Up) are owned by other
team members and will be documented separately. The `User` and `Group` models here are
minimal placeholders (just the fields Expenses depends on) pending those features.

## Expenses API

All endpoints require a JWT in the `Authorization: Bearer <token>` header, and the
caller must be a member of the relevant group.

### Split types

- `equal` — amount divided evenly across `participants` (any leftover cents go to the
  lowest user IDs so shares always add up exactly to the total).
- `unequal` — each participant supplies an `amount`; all amounts must sum to the total.
- `percentage` — each participant supplies a `percentage`; all percentages must sum to 100.

### `POST /api/groups/<group_id>/expenses`

Add an expense to a group.

Request body:
```json
{
  "amount": "90.00",
  "description": "Dinner",
  "split_type": "equal",
  "paid_by": 3,
  "participants": [
    {"user_id": 1},
    {"user_id": 2},
    {"user_id": 3}
  ]
}
```

Response: the created expense including its computed `shares`.

---

## Member 4: Balances & Settlement

## Data Models

| Model | Table | Key fields | Relationships |
|---|---|---|---|
| **User** | `users` | id, name, email, password_hash | belongs to many Groups (via `group_members`); participant in many Expenses (via `expense_shares`) |
| **Group** | `groups` | id, name, created_by, created_at | has many Members (M2M via `group_members`); has many Expenses; has many Settlements |
| **Expense** | `expenses` | id, description, amount, paid_by, group_id, date, split_type | belongs to a Group; has many Shares (per-participant amounts) |
| **Settlement** | `settlements` | id, group_id, payer_id, payee_id, amount, created_at | belongs to a Group; payer and payee reference Users |
| **Notification** | `notifications` | id, user_id, group_id, message, is_read, created_at | belongs to a User and a Group |

**Expense participant-splitting:** An expense splits its amount across `expense.shares`
(one share per participant). If no shares are recorded, balances fall back to splitting
equally across all `group.members`. The payer is always credited the full amount they
paid, even if they are not listed as a participant (e.g. paying on someone else's behalf).

---

## Balances & Settlements — Endpoints

All endpoints require a valid JWT `Authorization: Bearer <token>` header.

| Method | Path | Description |
|---|---|---|
| GET | `/api/groups/<group_id>/balances` | Per-user gross balances after settlements |
| GET | `/api/groups/<group_id>/balances/net` | Balances + minimal payment plan (`simplified_transactions`) |
| GET | `/api/groups/<group_id>/activity` | Chronological expense + settlement feed |
| POST | `/api/groups/<group_id>/settlements` | Record a settlement `{payer_id, payee_id, amount}` |
| GET | `/api/groups/<group_id>/summary` | Totals, per-payer spend, top spender |
| GET | `/api/notifications` | Current user's notifications |
| PATCH | `/api/notifications/<id>/read` | Mark a notification read (owner only) |

### Example

```bash
# Record a settlement (Bob pays Alice $30)
curl -X POST http://localhost:5000/api/groups/1/settlements \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"payer_id": 2, "payee_id": 1, "amount": 30}'
```

## Local Development

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py            # SQLite by default; override with DATABASE_URL
python -m pytest tests/  # run the test suite
```

## Docker

```bash
docker build -t tallymate-back .
docker run -p 5000:5000 tallymate-back
```

## Deployment (Render)

The backend runs on Render as a plain Python web service (the Docker image is for local
use; `start.sh` replicates its entrypoint on Render):

1. Create a **Web Service** on Render connected to the `tallymate_back` GitHub repo.
   Use branch `dev` for testing; switch to `main` once a release branch exists.
2. Settings:
   - Runtime: `Python 3`
   - Build command: `pip install -r requirements.txt`
   - Start command: `sh start.sh`
   - Health check path: `/health`
3. Environment variables:
   - `DATABASE_URL` — Render Postgres **internal** URL in SQLAlchemy format (e.g. `postgresql://...`)
   - `JWT_SECRET_KEY` — generate with `openssl rand -hex 32` (never reuse the dev secret)
4. `start.sh` runs the same schema initialization as `docker-entrypoint.sh`
   (`db.create_all()`), then starts gunicorn on `$PORT`.

The resulting service URL is the target of the frontend's `/api` proxy in `vercel.json`.
