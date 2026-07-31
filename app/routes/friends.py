from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import and_, or_, select

from app.extensions import db
from app.models.friend import FriendContact
from app.models.user import User

friends_bp = Blueprint("friends", __name__, url_prefix="/friends")


def current_user_id():
    return int(get_jwt_identity())


@friends_bp.post("/add")
@jwt_required()
def add_friend():
    """Send a friend request
    ---
    tags: [Friends]
    summary: Send a friend request to a user by email
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [email]
            properties:
              email: {type: string, example: grace@example.com}
    responses:
      201:
        description: Friend request sent
      400: {description: Missing email or adding yourself}
      404: {description: User not found}
      409: {description: Request or friendship already exists}
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not str(data.get("email", "")).strip():
        return jsonify(error="email is required."), 400
    email, user_id = str(data["email"]).strip().lower(), current_user_id()
    friend = db.session.scalar(select(User).where(User.email == email))
    if not friend:
        return jsonify(error="User not found."), 404
    if friend.id == user_id:
        return jsonify(error="You cannot add yourself as a friend."), 400
    existing = db.session.scalar(select(FriendContact).where(or_(and_(FriendContact.user_id == user_id, FriendContact.friend_id == friend.id), and_(FriendContact.user_id == friend.id, FriendContact.friend_id == user_id))))
    if existing:
        return jsonify(error="A friend request or friendship already exists."), 409
    contact = FriendContact(user_id=user_id, friend_id=friend.id, status="pending")
    db.session.add(contact)
    db.session.commit()
    request_data = {"id": contact.id, "user_id": contact.user_id, "friend_id": contact.friend_id, "status": contact.status, "created_at": contact.created_at.isoformat()}
    return jsonify(message="Friend request sent.", friend_request=request_data), 201


@friends_bp.post("/accept/<int:request_id>")
@jwt_required()
def accept_friend(request_id):
    """Accept a friend request
    ---
    tags: [Friends]
    summary: Accept a pending request received by the current user
    security:
      - BearerAuth: []
    parameters:
      - name: request_id
        in: path
        required: true
        schema: {type: integer}
    responses:
      200:
        description: Friend request accepted
      403: {description: Not your request}
      404: {description: Request not found}
      409: {description: Already accepted}
    """
    contact = db.session.get(FriendContact, request_id)
    if not contact:
        return jsonify(error="Friend request not found."), 404
    if contact.friend_id != current_user_id():
        return jsonify(error="You cannot accept this friend request."), 403
    if contact.status != "pending":
        return jsonify(error="Friend request has already been accepted."), 409
    contact.status = "accepted"
    db.session.commit()
    return jsonify(message="Friend request accepted.", friend=contact.user.to_dict())


@friends_bp.get("")
@jwt_required()
def list_friends():
    """List friends
    ---
    tags: [Friends]
    summary: List the current user's accepted friends
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of friends
    """
    user_id = current_user_id()
    contacts = db.session.scalars(select(FriendContact).where(FriendContact.status == "accepted", or_(FriendContact.user_id == user_id, FriendContact.friend_id == user_id)).order_by(FriendContact.created_at.desc())).all()
    friends = [contact.friend if contact.user_id == user_id else contact.user for contact in contacts]
    return jsonify(friends=[friend.to_dict() for friend in friends])


@friends_bp.delete("/<int:friend_id>")
@jwt_required()
def remove_friend(friend_id):
    """Remove a friend
    ---
    tags: [Friends]
    summary: Remove an accepted friendship
    security:
      - BearerAuth: []
    parameters:
      - name: friend_id
        in: path
        required: true
        schema: {type: integer}
    responses:
      204: {description: Removed}
      404: {description: Accepted friendship not found}
    """
    user_id = current_user_id()
    contact = db.session.scalar(select(FriendContact).where(FriendContact.status == "accepted", or_(and_(FriendContact.user_id == user_id, FriendContact.friend_id == friend_id), and_(FriendContact.user_id == friend_id, FriendContact.friend_id == user_id))))
    if not contact:
        return jsonify(error="Accepted friendship not found."), 404
    db.session.delete(contact)
    db.session.commit()
    return "", 204

@friends_bp.get("/search")
@jwt_required()
def search_users():
    """Search users by email
    ---
    tags: [Friends]
    summary: Search users whose email contains the query (max 10)
    security:
      - BearerAuth: []
    parameters:
      - name: q
        in: query
        required: true
        schema: {type: string, example: grace}
    responses:
      200:
        description: Matching users
    """
    q = request.args.get("q", "").strip().lower()
    if not q:
        return jsonify(users=[])
    users = db.session.scalars(
        select(User).where(User.email.ilike(f"%{q}%")).limit(10)
    ).all()
    return jsonify(users=[u.to_dict() for u in users])