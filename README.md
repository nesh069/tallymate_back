## README
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
