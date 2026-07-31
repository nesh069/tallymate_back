import json

from app.extensions import db
from app.models.expense import Expense
from tests.conftest import auth_headers


def _post_expense(client, token, group_id, payload):
    return client.post(
        f"/api/groups/{group_id}/expenses",
        data=json.dumps(payload),
        content_type="application/json",
        headers=auth_headers(token),
    )


def test_add_expense_equal_split(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "90.00",
        "description": "Dinner",
        "split_type": "equal",
        "participants": [{"user_id": g["alice"]}, {"user_id": g["bob"]}, {"user_id": g["carol"]}],
    }

    resp = _post_expense(client, g["alice_token"], g["group_id"], payload)

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["amount"] == "90.00"
    assert body["paid_by"] == g["alice"]
    assert body["split_type"] == "equal"
    shares = {s["user_id"]: s["amount"] for s in body["shares"]}
    assert shares == {g["alice"]: "30.00", g["bob"]: "30.00", g["carol"]: "30.00"}


def test_add_expense_defaults_paid_by_to_current_user(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "20.00",
        "split_type": "equal",
        "participants": [{"user_id": g["bob"]}],
    }

    resp = _post_expense(client, g["bob_token"], g["group_id"], payload)

    assert resp.status_code == 201
    assert resp.get_json()["paid_by"] == g["bob"]


def test_add_expense_unequal_split(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "100.00",
        "split_type": "unequal",
        "participants": [
            {"user_id": g["alice"], "amount": "60.00"},
            {"user_id": g["bob"], "amount": "40.00"},
        ],
    }

    resp = _post_expense(client, g["alice_token"], g["group_id"], payload)

    assert resp.status_code == 201
    shares = {s["user_id"]: s["amount"] for s in resp.get_json()["shares"]}
    assert shares == {g["alice"]: "60.00", g["bob"]: "40.00"}


def test_add_expense_unequal_split_must_sum_to_total(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "100.00",
        "split_type": "unequal",
        "participants": [
            {"user_id": g["alice"], "amount": "60.00"},
            {"user_id": g["bob"], "amount": "30.00"},
        ],
    }

    resp = _post_expense(client, g["alice_token"], g["group_id"], payload)

    assert resp.status_code == 400


def test_add_expense_percentage_split(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "200.00",
        "split_type": "percentage",
        "participants": [
            {"user_id": g["alice"], "percentage": "25"},
            {"user_id": g["bob"], "percentage": "75"},
        ],
    }

    resp = _post_expense(client, g["alice_token"], g["group_id"], payload)

    assert resp.status_code == 201
    body = resp.get_json()
    shares = {s["user_id"]: (s["amount"], s["percentage"]) for s in body["shares"]}
    assert shares == {g["alice"]: ("50.00", "25.00"), g["bob"]: ("150.00", "75.00")}


def test_add_expense_percentage_split_must_sum_to_100(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "200.00",
        "split_type": "percentage",
        "participants": [
            {"user_id": g["alice"], "percentage": "25"},
            {"user_id": g["bob"], "percentage": "50"},
        ],
    }

    resp = _post_expense(client, g["alice_token"], g["group_id"], payload)

    assert resp.status_code == 400


def test_add_expense_rejects_non_member_participant(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "50.00",
        "split_type": "equal",
        "participants": [{"user_id": g["alice"]}, {"user_id": g["dave"]}],
    }

    resp = _post_expense(client, g["alice_token"], g["group_id"], payload)

    assert resp.status_code == 400


def test_non_member_cannot_add_expense(client, group_with_members):
    g = group_with_members
    payload = {
        "amount": "50.00",
        "split_type": "equal",
        "participants": [{"user_id": g["alice"]}],
    }

    resp = _post_expense(client, g["dave_token"], g["group_id"], payload)

    assert resp.status_code == 403


def test_add_expense_requires_auth(client, group_with_members):
    g = group_with_members
    resp = client.post(
        f"/api/groups/{g['group_id']}/expenses",
        data=json.dumps({"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}]}),
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_add_expense_rejects_unknown_group(client, group_with_members):
    g = group_with_members
    resp = _post_expense(
        client,
        g["alice_token"],
        999999,
        {"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}]},
    )
    assert resp.status_code == 404


def test_add_expense_rejects_invalid_amount(client, group_with_members):
    g = group_with_members
    resp = _post_expense(
        client,
        g["alice_token"],
        g["group_id"],
        {"amount": "-10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}]},
    )
    assert resp.status_code == 400


def test_list_expenses_for_group(client, group_with_members):
    g = group_with_members
    _post_expense(
        client,
        g["alice_token"],
        g["group_id"],
        {"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}, {"user_id": g["bob"]}]},
    )
    _post_expense(
        client,
        g["bob_token"],
        g["group_id"],
        {"amount": "20.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}, {"user_id": g["bob"]}]},
    )

    resp = client.get(f"/api/groups/{g['group_id']}/expenses", headers=auth_headers(g["alice_token"]))

    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 2


def test_list_expenses_forbidden_for_non_member(client, group_with_members):
    g = group_with_members
    resp = client.get(f"/api/groups/{g['group_id']}/expenses", headers=auth_headers(g["dave_token"]))
    assert resp.status_code == 403


def test_get_single_expense(client, group_with_members):
    g = group_with_members
    create_resp = _post_expense(
        client,
        g["alice_token"],
        g["group_id"],
        {"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}]},
    )
    expense_id = create_resp.get_json()["id"]

    resp = client.get(f"/api/expenses/{expense_id}", headers=auth_headers(g["bob_token"]))

    assert resp.status_code == 200
    assert resp.get_json()["id"] == expense_id


def test_get_expense_not_found(client, group_with_members):
    resp = client.get("/api/expenses/999999", headers=auth_headers(group_with_members["alice_token"]))
    assert resp.status_code == 404


def test_edit_expense_by_payer(client, group_with_members):
    g = group_with_members
    create_resp = _post_expense(
        client,
        g["alice_token"],
        g["group_id"],
        {"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}, {"user_id": g["bob"]}]},
    )
    expense_id = create_resp.get_json()["id"]

    update_payload = {
        "amount": "50.00",
        "description": "Updated dinner",
        "split_type": "equal",
        "participants": [{"user_id": g["alice"]}, {"user_id": g["bob"]}, {"user_id": g["carol"]}],
    }
    resp = client.put(
        f"/api/expenses/{expense_id}",
        data=json.dumps(update_payload),
        content_type="application/json",
        headers=auth_headers(g["alice_token"]),
    )

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["amount"] == "50.00"
    assert body["description"] == "Updated dinner"
    assert len(body["shares"]) == 3


def test_edit_expense_forbidden_for_non_payer(client, group_with_members):
    g = group_with_members
    create_resp = _post_expense(
        client,
        g["alice_token"],
        g["group_id"],
        {"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}]},
    )
    expense_id = create_resp.get_json()["id"]

    resp = client.put(
        f"/api/expenses/{expense_id}",
        data=json.dumps(
            {"amount": "50.00", "split_type": "equal", "participants": [{"user_id": g["bob"]}]}
        ),
        content_type="application/json",
        headers=auth_headers(g["bob_token"]),
    )

    assert resp.status_code == 403


def test_delete_expense_by_payer(client, group_with_members, app):
    g = group_with_members
    create_resp = _post_expense(
        client,
        g["alice_token"],
        g["group_id"],
        {"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}]},
    )
    expense_id = create_resp.get_json()["id"]

    resp = client.delete(f"/api/expenses/{expense_id}", headers=auth_headers(g["alice_token"]))

    assert resp.status_code == 204
    with app.app_context():
        assert db.session.get(Expense, expense_id) is None


def test_list_group_members(client, group_with_members):
    g = group_with_members
    resp = client.get(f"/api/groups/{g['group_id']}/members", headers=auth_headers(g["alice_token"]))

    assert resp.status_code == 200
    ids = {m["id"] for m in resp.get_json()}
    assert ids == {g["alice"], g["bob"], g["carol"]}


def test_list_group_members_forbidden_for_non_member(client, group_with_members):
    g = group_with_members
    resp = client.get(f"/api/groups/{g['group_id']}/members", headers=auth_headers(g["dave_token"]))
    assert resp.status_code == 403


def test_delete_expense_forbidden_for_non_payer(client, group_with_members):
    g = group_with_members
    create_resp = _post_expense(
        client,
        g["alice_token"],
        g["group_id"],
        {"amount": "10.00", "split_type": "equal", "participants": [{"user_id": g["alice"]}]},
    )
    expense_id = create_resp.get_json()["id"]

    resp = client.delete(f"/api/expenses/{expense_id}", headers=auth_headers(g["bob_token"]))

    assert resp.status_code == 403
