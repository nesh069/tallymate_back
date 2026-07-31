from flask import Flask, jsonify

from app.config import Config
from app.extensions import db, jwt, migrate


def create_app(config_object=Config):
    """Create and configure the TallyMate API application."""
    app = Flask(__name__)
    app.config.from_object(config_object)
    if not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("JWT_SECRET_KEY must be set in the environment.")
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    from app.routes.auth import auth_bp
    from app.routes.friends import friends_bp
    from app.routes.groups import groups_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(friends_bp)
    app.register_blueprint(groups_bp)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app