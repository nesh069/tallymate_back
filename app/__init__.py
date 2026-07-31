from flask import Flask, jsonify
from flasgger import Swagger

from app.config import Config
from app.extensions import db, jwt, migrate, cors

SWAGGER_TEMPLATE = {
    "openapi": "3.0.3",
    "info": {
        "title": "TallyMate API",
        "description": (
            "REST API for TallyMate — group expenses, balances, settlements, "
            "friends, and notifications. All protected endpoints require an "
            "`Authorization: Bearer <access_token>` header."
        ),
        "version": "1.0.0",
    },
    "components": {
        "securitySchemes": {
            "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        }
    },
}


def create_app(config_object=Config):
    """Create and configure the TallyMate API application."""
    app = Flask(__name__)
    app.config.from_object(config_object)
    if not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("JWT_SECRET_KEY must be set in the environment.")

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    from app.models.user import User
    from app.models.group import Group
    from app.models.expense import Expense, ExpenseShare
    from app.models.settlement import Settlement
    from app.models.notification import Notification

    from app.routes.auth import auth_bp
    from app.routes.friends import friends_bp
    from app.routes.groups import groups_bp
    from app.routes.expenses import expenses_bp
    from app.routes.balances import balances_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(friends_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(balances_bp)

    swagger = Swagger(app, template=SWAGGER_TEMPLATE)

    @app.get("/health")
    def health():
        """Health check
        ---
        tags: [Meta]
        summary: Liveness probe
        responses:
          200:
            description: Service is healthy
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    status: {type: string, example: ok}
        """
        return jsonify(status="ok")

    with app.app_context():
        db.create_all()

    return app
