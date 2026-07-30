from flask import Flask

from app.config import Config
from app.extensions import cors, db, jwt, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    from app import models  # noqa: F401  (registers models with SQLAlchemy metadata)

    from app.routes.expenses import expenses_bp

    app.register_blueprint(expenses_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command("seed-demo")
    def seed_demo():
        """Create a demo group with 3 members and print a JWT + group id,
        for manually testing the Expenses UI before real login exists."""
        from datetime import timedelta

        from flask_jwt_extended import create_access_token

        from app.models.group import Group
        from app.models.user import User

        db.create_all()

        alice = User.query.filter_by(email="alice@demo.com").first()
        if alice is None:
            alice = User(name="Alice", email="alice@demo.com", password_hash="demo")
            bob = User(name="Bob", email="bob@demo.com", password_hash="demo")
            carol = User(name="Carol", email="carol@demo.com", password_hash="demo")
            db.session.add_all([alice, bob, carol])
            db.session.commit()

            group = Group(name="Demo Trip", created_by=alice.id, members=[alice, bob, carol])
            db.session.add(group)
            db.session.commit()
        else:
            group = alice.groups[0]

        token = create_access_token(identity=str(alice.id), expires_delta=timedelta(days=1))
        print(f"Group ID: {group.id}")
        print(f"Logged in as: {alice.name} ({alice.email})")
        print(f"JWT: {token}")
