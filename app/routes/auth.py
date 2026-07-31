from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from sqlalchemy import select

from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


@auth_bp.post("/signup")
def signup():
    data = json_body()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")
    if not name or not email or not isinstance(password, str) or len(password) < 8:
        return jsonify(error="name, email, and a password of at least 8 characters are required."), 400
    if db.session.scalar(select(User).where(User.email == email)):
        return jsonify(error="An account with that email already exists."), 409
    user = User(name=name, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user=user.to_dict(), access_token=create_access_token(identity=str(user.id))), 201


@auth_bp.post("/login")
def login():
    data = json_body()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password")
    user = db.session.scalar(select(User).where(User.email == email))
    if not user or not isinstance(password, str) or not user.check_password(password):
        return jsonify(error="Invalid email or password."), 401
    return jsonify(user=user.to_dict(), access_token=create_access_token(identity=str(user.id)), refresh_token=create_refresh_token(identity=str(user.id)))


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User no longer exists."), 404
    return jsonify(user=user.to_dict())
