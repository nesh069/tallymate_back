from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError

from app.extensions import db
from app.models.expense import Expense, ExpenseShare
from app.models.group import Group
from app.schemas.expense import ExpenseSchema
from app.services.splitting import SplitError, compute_shares

expenses_bp = Blueprint("expenses", __name__, url_prefix="/api")

expense_schema = ExpenseSchema()


def _current_user_id():
    return int(get_jwt_identity())


def _get_group_or_404(group_id):
    group = db.session.get(Group, group_id)
    if group is None:
        return None, (jsonify({"error": "Group not found."}), 404)
    return group, None


def _require_membership(group, user_id):
    if not group.has_member(user_id):
        return jsonify({"error": "You are not a member of this group."}), 403
    return None


def _participants_map(split_type, participants):
    if split_type == "equal":
        return {p["user_id"]: None for p in participants}
    if split_type == "unequal":
        return {p["user_id"]: p["amount"] for p in participants}
    return {p["user_id"]: p["percentage"] for p in participants}


def _build_shares(expense, split_type, amount, participants, group):
    for p in participants:
        if not group.has_member(p["user_id"]):
            raise SplitError(f"User {p['user_id']} is not a member of this group.")

    participants_map = _participants_map(split_type, participants)
    amounts, percentages = compute_shares(split_type, amount, participants_map)

    expense.shares = [
        ExpenseShare(
            user_id=uid,
            amount=amounts[uid],
            percentage=(percentages or {}).get(uid),
        )
        for uid in amounts
    ]


@expenses_bp.route("/groups/<int:group_id>/expenses", methods=["POST"])
@jwt_required()
def add_expense(group_id):
    group, error = _get_group_or_404(group_id)
    if error:
        return error

    user_id = _current_user_id()
    membership_error = _require_membership(group, user_id)
    if membership_error:
        return membership_error

    try:
        data = expense_schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid request.", "details": err.messages}), 400

    paid_by = data.get("paid_by", user_id)
    if not group.has_member(paid_by):
        return jsonify({"error": "paid_by must be a member of this group."}), 400

    expense = Expense(
        group_id=group.id,
        paid_by=paid_by,
        amount=data["amount"],
        description=data.get("description"),
        split_type=data["split_type"],
    )

    try:
        _build_shares(expense, data["split_type"], data["amount"], data["participants"], group)
    except SplitError as err:
        return jsonify({"error": str(err)}), 400

    db.session.add(expense)
    db.session.commit()

    return jsonify(expense.to_dict()), 201


@expenses_bp.route("/groups/<int:group_id>/expenses", methods=["GET"])
@jwt_required()
def list_expenses(group_id):
    group, error = _get_group_or_404(group_id)
    if error:
        return error

    membership_error = _require_membership(group, _current_user_id())
    if membership_error:
        return membership_error

    expenses = (
        Expense.query.filter_by(group_id=group_id).order_by(Expense.date.desc()).all()
    )
    return jsonify([e.to_dict() for e in expenses]), 200


@expenses_bp.route("/expenses/<int:expense_id>", methods=["GET"])
@jwt_required()
def get_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        return jsonify({"error": "Expense not found."}), 404

    membership_error = _require_membership(expense.group, _current_user_id())
    if membership_error:
        return membership_error

    return jsonify(expense.to_dict()), 200


@expenses_bp.route("/expenses/<int:expense_id>", methods=["PUT"])
@jwt_required()
def update_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        return jsonify({"error": "Expense not found."}), 404

    user_id = _current_user_id()
    if expense.paid_by != user_id:
        return jsonify({"error": "Only the person who paid can edit this expense."}), 403

    try:
        data = expense_schema.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid request.", "details": err.messages}), 400

    group = expense.group
    paid_by = data.get("paid_by", expense.paid_by)
    if not group.has_member(paid_by):
        return jsonify({"error": "paid_by must be a member of this group."}), 400

    expense.amount = data["amount"]
    expense.description = data.get("description")
    expense.split_type = data["split_type"]
    expense.paid_by = paid_by

    try:
        _build_shares(expense, data["split_type"], data["amount"], data["participants"], group)
    except SplitError as err:
        return jsonify({"error": str(err)}), 400

    db.session.commit()

    return jsonify(expense.to_dict()), 200


@expenses_bp.route("/groups/<int:group_id>/members", methods=["GET"])
@jwt_required()
def list_group_members(group_id):
    """Read-only helper for the expense split UI (who paid / who owes).
    Temporary home pending Member 2's Groups feature absorbing this into groups.py."""
    group, error = _get_group_or_404(group_id)
    if error:
        return error

    membership_error = _require_membership(group, _current_user_id())
    if membership_error:
        return membership_error

    members = [{"id": m.id, "name": m.name, "email": m.email} for m in group.members]
    return jsonify(members), 200


@expenses_bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@jwt_required()
def delete_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        return jsonify({"error": "Expense not found."}), 404

    if expense.paid_by != _current_user_id():
        return jsonify({"error": "Only the person who paid can delete this expense."}), 403

    db.session.delete(expense)
    db.session.commit()

    return "", 204
