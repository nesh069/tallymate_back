import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models.group import Group
from app.models.user import User


@pytest.fixture
def app():
    flask_app = create_app(TestConfig)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _make_user(name, email):
    user = User(name=name, email=email, password_hash="not-a-real-hash")
    db.session.add(user)
    db.session.commit()
    return user


def _token_for(user):
    return create_access_token(identity=str(user.id))


@pytest.fixture
def group_with_members(app):
    """A group with three members (Alice, Bob, Carol) plus an outsider (Dave)
    who does not belong to the group, along with JWT tokens for each."""
    alice = _make_user("Alice", "alice@test.com")
    bob = _make_user("Bob", "bob@test.com")
    carol = _make_user("Carol", "carol@test.com")
    dave = _make_user("Dave", "dave@test.com")

    group = Group(name="Trip", created_by=alice.id, members=[alice, bob, carol])
    db.session.add(group)
    db.session.commit()

    return {
        "group_id": group.id,
        "alice": alice.id,
        "bob": bob.id,
        "carol": carol.id,
        "dave": dave.id,
        "alice_token": _token_for(alice),
        "bob_token": _token_for(bob),
        "carol_token": _token_for(carol),
        "dave_token": _token_for(dave),
    }


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
