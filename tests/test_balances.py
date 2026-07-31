import pytest
from app.extensions import db
from app.models.user import User
from app.models.group import Group
from app.models.expense import Expense, ExpenseShare
from app.models.settlement import Settlement
from app.routes.balances import _compute_gross_balances, _apply_settlements, _simplify_debts


def _make_user(name, email):
    user = User(name=name, email=email, password_hash="x")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_group(app):
    u1 = _make_user("Alice", "alice@test.com")
    u2 = _make_user("Bob", "bob@test.com")
    u3 = _make_user("Cathy", "cathy@test.com")

    group = Group(name="Trip", created_by=u1.id, members=[u1, u2, u3])
    db.session.add(group)
    db.session.commit()

    e1 = Expense(description="Dinner", amount=90, paid_by=u1.id, group_id=group.id)
    db.session.add(e1)
    db.session.commit()

    return group, u1, u2, u3


@pytest.fixture
def group_with_participant_expense(app):
    u1 = _make_user("Alice", "alice_p@test.com")
    u2 = _make_user("Bob", "bob_p@test.com")
    u3 = _make_user("Cathy", "cathy_p@test.com")

    group = Group(name="Dinner", created_by=u1.id, members=[u1, u2, u3])
    db.session.add(group)
    db.session.commit()

    e1 = Expense(description="Pizza", amount=60, paid_by=u1.id, group_id=group.id)
    e1.shares = [
        ExpenseShare(user_id=u1.id, amount=30),
        ExpenseShare(user_id=u2.id, amount=30),
    ]
    db.session.add(e1)
    db.session.commit()

    return group, u1, u2, u3


@pytest.fixture
def group_with_payer_not_participant(app):
    u1 = _make_user("Alice", "alice_pnp@test.com")
    u2 = _make_user("Bob", "bob_pnp@test.com")
    u3 = _make_user("Cathy", "cathy_pnp@test.com")

    group = Group(name="Treat", created_by=u1.id, members=[u1, u2, u3])
    db.session.add(group)
    db.session.commit()

    e1 = Expense(description="Ice cream", amount=30, paid_by=u1.id, group_id=group.id)
    e1.shares = [
        ExpenseShare(user_id=u2.id, amount=15),
        ExpenseShare(user_id=u3.id, amount=15),
    ]
    db.session.add(e1)
    db.session.commit()

    return group, u1, u2, u3


def test_gross_balances_equal_split(sample_group):
    group, u1, u2, u3 = sample_group
    balances = _compute_gross_balances(group)
    assert round(balances[u1.id], 2) == 60.0
    assert round(balances[u2.id], 2) == -30.0
    assert round(balances[u3.id], 2) == -30.0


def test_gross_balances_participant_split(group_with_participant_expense):
    group, u1, u2, u3 = group_with_participant_expense
    balances = _compute_gross_balances(group)
    # u1 paid 60, split 2 ways (u1, u2) → share=30
    # u1: +60 - 30 = +30, u2: -30, u3 (non-participant): 0
    assert round(balances[u1.id], 2) == 30.0
    assert round(balances[u2.id], 2) == -30.0
    assert round(balances[u3.id], 2) == 0.0


def test_gross_balances_payer_not_participant(group_with_payer_not_participant):
    group, u1, u2, u3 = group_with_payer_not_participant
    balances = _compute_gross_balances(group)
    # u1 paid 30, participants are u2, u3 → share=15 each
    # u1 (payer, not participant): +30 (full credit)
    # u2: -15, u3: -15
    assert round(balances[u1.id], 2) == 30.0
    assert round(balances[u2.id], 2) == -15.0
    assert round(balances[u3.id], 2) == -15.0


def test_settlement_adjusts_balances(sample_group):
    group, u1, u2, u3 = sample_group
    balances = _compute_gross_balances(group)

    settlement = Settlement(group_id=group.id, payer_id=u2.id, payee_id=u1.id, amount=30)
    db.session.add(settlement)
    db.session.commit()
    group.settlements = [settlement]

    balances = _apply_settlements(group, balances)
    assert round(balances[u2.id], 2) == 0.0
    assert round(balances[u1.id], 2) == 30.0


def test_simplify_debts_produces_minimal_transactions(sample_group):
    group, u1, u2, u3 = sample_group
    balances = _compute_gross_balances(group)
    transactions = _simplify_debts(balances)

    assert len(transactions) == 2
    total_paid = sum(t["amount"] for t in transactions)
    assert round(total_paid, 2) == 60.0


def test_settlement_rejects_zero_or_negative_amount(client, token_headers, sample_group):
    group, u1, u2, u3 = sample_group
    resp = client.post(
        f"/api/groups/{group.id}/settlements",
        json={"payer_id": u2.id, "payee_id": u1.id, "amount": 0},
        headers=token_headers,
    )
    assert resp.status_code == 400


def test_participant_split_fallback_to_all_members(sample_group):
    group, u1, u2, u3 = sample_group
    balances = _compute_gross_balances(group)
    assert round(balances[u1.id], 2) == 60.0
    assert round(balances[u2.id], 2) == -30.0
    assert round(balances[u3.id], 2) == -30.0
