from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.group import Group
from app.models.expense import Expense
from app.models.settlement import Settlement
from app.models.notification import Notification

balances_bp = Blueprint("balances", __name__)


def _compute_gross_balances(group):
    members = list(group.members)
    balances = {m.id: 0.0 for m in members}

    for expense in group.expenses:
        amount = float(expense.amount)
        if expense.shares:
            share_by_user = {s.user_id: float(s.amount) for s in expense.shares}
        else:
            share_by_user = {m.id: amount / len(members) for m in members}

        payer_share = share_by_user.get(expense.paid_by, 0.0)
        balances[expense.paid_by] += amount - payer_share
        for user_id, share in share_by_user.items():
            if user_id != expense.paid_by:
                balances[user_id] -= share

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


@balances_bp.route("/api/groups/<int:group_id>/activity", methods=["GET"])
@jwt_required()
def get_activity(group_id):
    group = Group.query.get_or_404(group_id)
    expenses = [
        {"type": "expense", "timestamp": e.date, **e.to_dict()}
        for e in group.expenses
    ]
    settlements = [
        {"type": "settlement", "timestamp": s.created_at, **s.to_dict()}
        for s in group.settlements
    ]
    activity = sorted(
        expenses + settlements,
        key=lambda x: x["timestamp"],
        reverse=True,
    )
    return jsonify(activity)


@balances_bp.route("/api/groups/<int:group_id>/settlements", methods=["POST"])
@jwt_required()
def record_settlement(group_id):
    data = request.get_json()
    payer_id = data.get("payer_id")
    payee_id = data.get("payee_id")
    amount = data.get("amount")

    if not all([payer_id, payee_id, amount]) or amount <= 0:
        return jsonify({"error": "payer_id, payee_id, and a positive amount are required"}), 400
    if payer_id == payee_id:
        return jsonify({"error": "payer and payee must be different"}), 400

    group = Group.query.get_or_404(group_id)
    member_ids = {m.id for m in group.members}
    if payer_id not in member_ids or payee_id not in member_ids:
        return jsonify({"error": "both users must be members of the group"}), 400

    settlement = Settlement(group_id=group_id, payer_id=payer_id, payee_id=payee_id, amount=amount)
    db.session.add(settlement)
    for member in group.members:
        if member.id != payer_id:
            db.session.add(Notification(
                user_id=member.id,
                group_id=group.id,
                message=f"A settlement of {amount} was recorded in {group.name}",
            ))
    db.session.commit()
    return jsonify(settlement.to_dict()), 201


@balances_bp.route("/api/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    user_id = int(get_jwt_identity())
    notes = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notes])


@balances_bp.route("/api/notifications/<int:notification_id>/read", methods=["PATCH"])
@jwt_required()
def mark_notification_read(notification_id):
    user_id = int(get_jwt_identity())
    note = Notification.query.get_or_404(notification_id)
    if note.user_id != user_id:
        return jsonify({"error": "you can only mark your own notifications as read"}), 403
    note.is_read = True
    db.session.commit()
    return jsonify(note.to_dict())


@balances_bp.route("/api/groups/<int:group_id>/summary", methods=["GET"])
@jwt_required()
def get_summary(group_id):
    group = Group.query.get_or_404(group_id)
    expenses = group.expenses
    members = list(group.members)

    total_spent = sum(float(e.amount) for e in expenses)
    # Participants are the users with shares on each expense (mirrors the
    # participant-based balance math); members who never took part in any
    # expense must not dilute the average.
    participant_ids = {s.user_id for e in expenses for s in e.shares}
    per_person = total_spent / len(participant_ids) if participant_ids else 0

    spend_by_payer = {}
    for e in expenses:
        spend_by_payer[e.paid_by] = spend_by_payer.get(e.paid_by, 0) + float(e.amount)
    top_spender = max(spend_by_payer, key=spend_by_payer.get) if spend_by_payer else None

    return jsonify({
        "total_spent": round(total_spent, 2),
        "average_per_person": round(per_person, 2),
        "spend_by_payer": {uid: round(amt, 2) for uid, amt in spend_by_payer.items()},
        "top_spender_id": top_spender,
        "expense_count": len(expenses),
    })
