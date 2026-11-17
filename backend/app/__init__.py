import os
import secrets
from pathlib import Path

from flask import Flask
from flask_cors import CORS

from .limiter import limiter, too_many
from .models import db


def _secret_key(app) -> str:
    """The key that signs login cookies and the audit log. It is never in
    the source code, because the code is public.

    Order: the CALLBACK_SECRET_KEY environment variable; a throwaway key for
    tests and in memory databases; otherwise a random key created once and
    kept in the instance folder, so it survives restarts.
    """
    from_env = os.environ.get("CALLBACK_SECRET_KEY")
    if from_env:
        return from_env
    if app.config.get("TESTING") or ":memory:" in app.config["SQLALCHEMY_DATABASE_URI"]:
        return secrets.token_hex(32)
    path = Path(app.instance_path) / "secret.key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    return path.read_text().strip()


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///callback.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # How long a verification request stays open before it ends as
        # Unable to Verify.
        REQUEST_TTL_SECONDS=300,
    )
    if config_overrides:
        app.config.update(config_overrides)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = _secret_key(app)

    db.init_app(app)
    limiter.init_app(app)
    app.register_error_handler(429, too_many)

    CORS(
        app,
        supports_credentials=True,
        origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    )

    from .activity import activity_bp
    from .auth import auth_bp
    from .enrollment import enrollment_bp
    from .totp import totp_bp
    from .verification import verification_bp

    app.register_blueprint(enrollment_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(verification_bp)
    app.register_blueprint(totp_bp)
    app.register_blueprint(activity_bp)

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
