import pytest
from flask_jwt_extended import create_access_token
from app import create_app
from app.config import TestConfig
from app.extensions import db


@pytest.fixture()
def app():
    application = create_app(TestConfig)
    ctx = application.app_context()
    ctx.push()
    db.drop_all()
    db.create_all()
    yield application
    db.session.remove()
    db.drop_all()
    ctx.pop()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        token = create_access_token(identity=str(1))
    return {"Authorization": f"Bearer {token}"}
