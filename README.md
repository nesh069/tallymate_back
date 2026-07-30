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
- `paid_by` is optional and defaults to the authenticated user.
- For `unequal`, each participant needs `"amount"`; for `percentage`, each needs `"percentage"`.

Responses: `201` with the created expense, `400` invalid payload/split math, `403` not a
group member, `404` group not found.

### `GET /api/groups/<group_id>/expenses`

List all expenses for a group, newest first. `200` on success, `403` if not a member.

### `GET /api/expenses/<expense_id>`

Get a single expense's details, including its per-user shares. `404` if not found.

### `PUT /api/expenses/<expense_id>`

Edit an expense (full replace — send the complete payload as in `POST`). Only the user
who paid (`paid_by`) may edit. `403` otherwise, `400` for invalid payloads.

### `GET /api/groups/<group_id>/members`

Read-only helper returning `[{"id", "name", "email"}]` for the group's members, used to
populate the paid-by/split-participant pickers in the Add Expense form. Temporary home
for this data pending Member 2's Groups feature. `403` if not a member.

### `DELETE /api/expenses/<expense_id>`

Delete an expense. Only the user who paid may delete. Returns `204` on success.

### Example expense object

```json
{
  "id": 1,
  "group_id": 1,
  "paid_by": 3,
  "amount": "90.00",
  "description": "Dinner",
  "split_type": "equal",
  "date": "2026-07-29T12:00:00+00:00",
  "shares": [
    {"user_id": 1, "amount": "30.00", "percentage": null},
    {"user_id": 2, "amount": "30.00", "percentage": null},
    {"user_id": 3, "amount": "30.00", "percentage": null}
  ]
}
```

## Running tests

```bash
pip install -r requirements.txt
pytest
```

## Manual testing without real login

Member 1's login/signup flow doesn't exist yet, so to try the Expenses UI/API by hand:

```bash
flask --app run.py seed-demo
```

This creates a demo group with 3 members and prints a group ID and a JWT for one of
them. Use the JWT as a Bearer token (or paste it into the frontend's `localStorage`
under the `token` key) to authenticate requests.
