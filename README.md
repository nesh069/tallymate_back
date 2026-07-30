# TallyMate — Member 4: Balances & Settlement

## Data Models (5 schemas)

| Model | Table | Key fields | Relationships |
|---|---|---|---|
| **User** | `users` | id, name, email, password_hash | belongs to many Groups (via `group_members`); participant in many Expenses (via `expense_participants`) |
| **Group** | `groups` | id, name | has many Members (M2M via `group_members`); has many Expenses; has many Settlements |
| **Expense** | `expenses` | id, description, amount, paid_by, group_id, created_at | belongs to a Group; has many Participants (M2M via `expense_participants`, **defaults to all group members if empty**); payer may be outside the participant list |
| **Settlement** | `settlements` | id, group_id, payer_id, payee_id, amount, created_at | belongs to a Group; payer and payee reference Users |
| **Notification** | `notifications` | id, user_id, group_id, message, is_read, created_at | belongs to a User and a Group |

**Expense participant-splitting:** An expense splits its amount equally across `expense.participants`. If no participants are explicitly recorded (M2M table empty), it falls back to splitting across all `group.members`. The payer is always credited the full amount they paid, even if they are not listed as a participant (e.g. paying on someone else's behalf).

---

## Balances & Settlements — Endpoints

All endpoints require a valid JWT `Authorization: Bearer <token>` header.

| Method | Path | Description |
|---|---|---|
| GET | `/api/groups/<group_id>/balances` | Gross balances per member (who paid what, who owes what), adjusted for settlements. |
| GET | `/api/groups/<group_id>/balances/net` | Net balances + simplified settle-up suggestions (minimal transactions via greedy algorithm). |
| POST | `/api/groups/<group_id>/settlements` | Record a settlement. Body: `{ "payer_id", "payee_id", "amount" }`. Validates positive amount, payer != payee, both are members. Creates a Notification for other group members. |
| GET | `/api/groups/<group_id>/activity` | Combined chronological history of expenses and settlements (most recent first). |
| GET | `/api/groups/<group_id>/summary` | Total spent, average per person, spend breakdown by payer, top spender ID, expense count. |
| GET | `/api/notifications` | Current user's notifications (most recent first). |
| PATCH | `/api/notifications/<id>/read` | Mark a single notification as read. Only the owner may do this; returns 403 otherwise. |

---

## Frontend

- **Protected route:** `/groups/:groupId/balances`
- The Balances page shows net balances, suggested settle-up transactions, an activity feed, and a spending summary pie chart (recharts).
- "Settle Up" modal lets the user select payer/payee from a member dropdown (fetched from `/api/groups/:id`) and records the settlement.
- `NotificationBell` component in the navbar polls `/api/notifications` every 15 seconds, shows an unread badge, and marks notifications read on click.

---

## Local Development with Docker

```bash
# From the project root (where docker-compose.yml lives):
docker compose up --build
```

| Service | Port | Notes |
|---|---|---|
| **db** | `5432` | PostgreSQL 16, user/pass/db all `tallymate` |
| **backend** | `5000` | Flask + Gunicorn, connects to `db` via `DATABASE_URL` |
| **frontend** | `5173` → `80` (container) | Nginx serves the Vite production build |

Environment variables (`SECRET_KEY`, `JWT_SECRET_KEY`) are read from the shell or use dev defaults. Set them before running:

```bash
export SECRET_KEY=your-secret
export JWT_SECRET_KEY=your-jwt-secret
docker compose up --build
```

> ⚠️ The Dockerfiles in `tallymate_back/Dockerfile` and `tallymate_front/Dockerfile` are **placeholders** — Members 1 and 3 should replace them with production-ready versions.

---

## Running tests

```bash
cd tallymate_back
source venv/bin/activate
FLASK_APP=app:create_app python -m pytest tests/ -v
```
