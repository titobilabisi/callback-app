import pytest

from app import create_app
from app.limiter import limiter
from app.models import db


class FakeClock:
    """The clock the TOTP checks use in tests. Each code the helpers make
    moves it forward one 30 second step, so every code is a fresh one.
    """

    def __init__(self, start=1_800_000_000.0):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


def make_app(rate_limits=False):
    clock = FakeClock()
    app = create_app({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "RATELIMIT_ENABLED": rate_limits,
        "TOTP_NOW": clock,
    })
    app.clock = clock
    if rate_limits:
        limiter.reset()
    return app


@pytest.fixture()
def app():
    app = make_app()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def limited_app():
    """Same app with rate limiting switched on, for the tests that check it."""
    app = make_app(rate_limits=True)
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
