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
    """Sign up a new user
    ---
    tags: [Auth]
    summary: Create an account and get an access token
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name, email, password]
            properties:
              name: {type: string, example: Ada}
              email: {type: string, example: ada@example.com}
              password: {type: string, minLength: 8}
    responses:
      201:
        description: User created with access token
      400: {description: Missing or invalid fields}
      409: {description: Email already registered}
    """
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
    """Log in
    ---
    tags: [Auth]
    summary: Exchange credentials for access and refresh tokens
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [email, password]
            properties:
              email: {type: string, example: ada@example.com}
              password: {type: string, example: password123}
    responses:
      200:
        description: User with access and refresh tokens
      401: {description: Invalid email or password}
    """
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
    """Get current user
    ---
    tags: [Auth]
    summary: Return the authenticated user's profile
    security:
      - BearerAuth: []
    responses:
      200:
        description: Current user
      404: {description: User no longer exists}
    """
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User no longer exists."), 404
    return jsonify(user=user.to_dict())


@auth_bp.patch("/me")
@jwt_required()
def update_me():
    """Update current user
    ---
    tags: [Auth]
    summary: Update profile fields (e.g. currency)
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              currency: {type: string, enum: [USD, KSH], example: KSH}
    responses:
      200:
        description: Updated user
      400: {description: Invalid currency}
      404: {description: User no longer exists}
    """
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify(error="User no longer exists."), 404

    data = json_body()
    if data is None:
        return jsonify(error="Request body must be a JSON object."), 400

    currency = data.get("currency")
    if currency is not None:
        currency = str(currency).upper()
        if currency not in ("USD", "KSH"):
            return jsonify(error="currency must be 'USD' or 'KSH'."), 400
        user.currency = currency

    db.session.commit()
    return jsonify(user=user.to_dict())
