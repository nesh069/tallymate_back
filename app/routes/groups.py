from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import select

from app.extensions import db
from app.models.group import Group
from app.models.user import User

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def current_user():
    return db.session.get(User, int(get_jwt_identity()))


# Create Group

@groups_bp.post("")
@jwt_required()
def create_group():
    user = current_user()
    if not user:
        return jsonify(error="User not found."), 404

    data = json_body()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400

    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify(error="Group name is required."), 400

    group = Group(name=name, created_by=user.id)
    group.members.append(user)
    db.session.add(group)
    db.session.commit()

    return jsonify(group=group.to_dict()), 201


# List My Groups

@groups_bp.get("")
@jwt_required()
def list_groups():
    user = current_user()
    if not user:
        return jsonify(error="User not found."), 404

    groups = user.groups.order_by(Group.created_at.desc()).all()
    return jsonify(groups=[g.to_dict() for g in groups])


# Get Group Detail

@groups_bp.get("/<int:group_id>")
@jwt_required()
def get_group(group_id):
    user = current_user()
    if not user:
        return jsonify(error="User not found."), 404

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify(error="Group not found."), 404

    if user not in group.members:
        return jsonify(error="You are not a member of this group."), 403

    return jsonify(group=group.to_dict())


# Add Member

@groups_bp.post("/<int:group_id>/members")
@jwt_required()
def add_member(group_id):
    user = current_user()
    if not user:
        return jsonify(error="User not found."), 404

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify(error="Group not found."), 404

    if group.created_by != user.id:
        return jsonify(error="Only the group owner can add members."), 403

    data = json_body()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400

    user_id = data.get("user_id")
    if not isinstance(user_id, int) or user_id < 1:
        return jsonify(error="A valid user_id is required."), 400

    new_member = db.session.get(User, user_id)
    if not new_member:
        return jsonify(error="User not found."), 404

    if new_member in group.members:
        return jsonify(error="User is already a member of this group."), 409

    group.members.append(new_member)
    db.session.commit()

    return jsonify(group=group.to_dict())


# Remove Member  

@groups_bp.delete("/<int:group_id>/members/<int:user_id>")
@jwt_required()
def remove_member(group_id, user_id):
    user = current_user()
    if not user:
        return jsonify(error="User not found."), 404

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify(error="Group not found."), 404

    if group.created_by != user.id:
        return jsonify(error="Only the group owner can remove members."), 403

    if user_id == user.id:
        return jsonify(error="You cannot remove yourself. Transfer ownership or delete the group."), 400

    member = db.session.get(User, user_id)
    if not member:
        return jsonify(error="User not found."), 404

    if member not in group.members:
        return jsonify(error="User is not a member of this group."), 404

    group.members.remove(member)
    db.session.commit()

    return jsonify(group=group.to_dict())

# Delete Group
 
@groups_bp.delete("/<int:group_id>")
@jwt_required()
def delete_group(group_id):
    user = current_user()
    if not user:
        return jsonify(error="User not found."), 404

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify(error="Group not found."), 404

    if group.created_by != user.id:
        return jsonify(error="Only the group owner can delete the group."), 403

    db.session.delete(group)
    db.session.commit()

    return jsonify(message="Group deleted.")


# Leave Group

@groups_bp.delete("/<int:group_id>/leave")
@jwt_required()
def leave_group(group_id):
    user = current_user()
    if not user:
        return jsonify(error="User not found."), 404

    group = db.session.get(Group, group_id)
    if not group:
        return jsonify(error="Group not found."), 404

    if group.created_by == user.id:
        return jsonify(error="Owner cannot leave the group. Transfer ownership or delete it."), 400

    if user not in group.members:
        return jsonify(error="You are not a member of this group."), 404

    group.members.remove(user)
    db.session.commit()

    return jsonify(message="You have left the group.")