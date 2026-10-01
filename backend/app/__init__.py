from flask import Flask
from flask_cors import CORS

from .models import db


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///callback.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="dev only key, replace before any real deployment",
    )
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)

    CORS(app, supports_credentials=True, origins=["http://localhost:5173"])

    from .enrollment import enrollment_bp
    app.register_blueprint(enrollment_bp)

    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
