from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from app.extensions import db
from app.models.group import Group
from app.models.expense import Expense
from app.models.settlement import Settlement

balances_bp = Blueprint("balances", __name__)


def _compute_gross_balances(group):
    """Day 1: raw amounts — who paid what, who owes what per expense, no netting."""
    members = group.members  # assumes Group.members relationship exists
    balances = {m.id: 0.0 for m in members}

    for expense in group.expenses:
        n = len(members)
        share = expense.amount / n
        for member in members:
            if member.id == expense.paid_by:
                balances[member.id] += expense.amount - share
            else:
                balances[member.id] -= share

    return balances


def _apply_settlements(group, balances):
    """Adjust balances for recorded settlements."""
    for s in group.settlements:
        balances[s.payer_id] += s.amount   # payer's debt reduced
        balances[s.payee_id] -= s.amount   # payee is owed less now
    return balances


def _simplify_debts(balances):
    """Day 2 stretch: convert net balances into a minimal set of payments."""
    debtors = [(uid, -amt) for uid, amt in balances.items() if amt < -0.01]
    creditors = [(uid, amt) for uid, amt in balances.items() if amt > 0.01]
    debtors.sort(key=lambda x: -x[1])
    creditors.sort(key=lambda x: -x[1])

    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]
        amount = min(debt, credit)
        transactions.append({"from": debtor_id, "to": creditor_id, "amount": round(amount, 2)})

        debtors[i] = (debtor_id, debt - amount)
        creditors[j] = (creditor_id, credit - amount)

        if debtors[i][1] <= 0.01:
            i += 1
        if creditors[j][1] <= 0.01:
            j += 1

    return transactions


@balances_bp.route("/api/groups/<int:group_id>/balances", methods=["GET"])
@jwt_required()
def get_gross_balances(group_id):
    group = Group.query.get_or_404(group_id)
    balances = _compute_gross_balances(group)
    balances = _apply_settlements(group, balances)
    return jsonify({uid: round(amt, 2) for uid, amt in balances.items()})


@balances_bp.route("/api/groups/<int:group_id>/balances/net", methods=["GET"])
@jwt_required()
def get_net_balances(group_id):
    group = Group.query.get_or_404(group_id)
    balances = _compute_gross_balances(group)
    balances = _apply_settlements(group, balances)
    simplified = _simplify_debts(balances)
    return jsonify({"balances": balances, "simplified_transactions": simplified})


@balances_bp.route("/api/groups/<int:group_id>/settlements", methods=["POST"])
@jwt_required()
def record_settlement(group_id):
    data = request.get_json()
    payer_id = data.get("payer_id")
    payee_id = data.get("payee_id")
    amount = data.get("amount")

    if not all([payer_id, payee_id, amount]) or amount <= 0:
        return jsonify({"error": "payer_id, payee_id, and a positive amount are required"}), 400

    settlement = Settlement(group_id=group_id, payer_id=payer_id, payee_id=payee_id, amount=amount)
    db.session.add(settlement)
    db.session.commit()
    return jsonify(settlement.to_dict()), 201


@balances_bp.route("/api/groups/<int:group_id>/activity", methods=["GET"])
@jwt_required()
def get_activity(group_id):
    group = Group.query.get_or_404(group_id)
    expenses = [{"type": "expense", **e.to_dict()} for e in group.expenses]
    settlements = [{"type": "settlement", **s.to_dict()} for s in group.settlements]
    activity = sorted(expenses + settlements, key=lambda x: x["created_at"], reverse=True)
    return jsonify(activity)