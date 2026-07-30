from flask import Flask
from app.config import Config
from app.extensions import db, migrate, jwt, cors

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    from app.models.user import User
    from app.models.group import Group
    from app.models.expense import Expense
    from app.models.settlement import Settlement

    from app.routes.balances import balances_bp
    app.register_blueprint(balances_bp)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    return app
