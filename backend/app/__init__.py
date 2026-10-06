from flask import Flask
from flask_cors import CORS

from .models import db


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///callback.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="dev only key, replace before any real deployment",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # How long a verification request stays open before it ends as
        # Unable to Verify.
        REQUEST_TTL_SECONDS=300,
    )
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)

    CORS(
        app,
        supports_credentials=True,
        origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    )

    from .auth import auth_bp
    from .enrollment import enrollment_bp
    from .verification import verification_bp

    app.register_blueprint(enrollment_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(verification_bp)

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
