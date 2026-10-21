"""Small helpers shared by the Chunk 2 and Chunk 3 tests."""
import pyotp

from app import create_app
from app.models import User
from app.risk import FACTOR_KEYS

PASSWORD = "correct horse battery"


def answers(**overrides):
    """All six answers 'no', with any overrides applied."""
    base = {k: False for k in FACTOR_KEYS}
    base.update(overrides)
    return base


def register_elder(client, email="grandma@example.com", name="Grandma"):
    res = client.post("/api/elders", json={"name": name, "email": email, "password": PASSWORD})
    assert res.status_code == 201
    return res.get_json()


def enroll_verifier(app, elder, email, name="Aunt Jane"):
    """The elder (logged in on their own client) issues an invite and a
    verifier redeems it. Uses the real enrollment endpoints, so a verifier
    here is a real enrolled one.
    """
    elder_client = app.test_client()
    login(elder_client, elder["email"])
    invite = elder_client.post(f"/api/elders/{elder['id']}/invites", json={}).get_json()
    res = app.test_client().post(
        "/api/verifiers",
        json={"invite_token": invite["token"], "name": name, "email": email, "password": PASSWORD},
    )
    assert res.status_code == 201
    return res.get_json()


def login(client, email):
    res = client.post("/api/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200
    return res.get_json()


def next_code(app, email):
    """A fresh, valid code for this family member. Moves the fake clock on
    one step first, so the code is never one that was already used.
    """
    app.clock.advance(30)
    with app.app_context():
        secret = User.query.filter_by(email=email).first().totp_secret
    return pyotp.TOTP(secret).at(app.clock())


def confirm_totp(app, client, email):
    """Finish a family member's authenticator setup, as the app does."""
    setup = client.get("/api/verifier/totp").get_json()
    assert setup["confirmed"] is False
    res = client.post("/api/verifier/totp/confirm", json={"code": next_code(app, email)})
    assert res.status_code == 200, res.get_json()


def new_client(app):
    """A separate browser: its own cookie jar, same app and database."""
    return app.test_client()


class Family:
    """An elder with N enrolled verifiers, each with their own logged in
    client. The usual starting point for a verification test.
    """

    def __init__(self, app, verifiers=2):
        self.app = app
        setup = app.test_client()
        self.elder = register_elder(setup)
        self.elder_client = app.test_client()
        login(self.elder_client, "grandma@example.com")

        self.verifiers = []
        self.verifier_clients = []
        for i in range(verifiers):
            email = f"verifier{i}@example.com"
            v = enroll_verifier(app, self.elder, email, name=f"Verifier {i}")
            c = app.test_client()
            login(c, email)
            confirm_totp(app, c, email)
            self.verifiers.append(v)
            self.verifier_clients.append(c)

    def open_request(self, **overrides):
        res = self.elder_client.post("/api/requests", json={"answers": answers(**overrides)})
        assert res.status_code == 201, res.get_json()
        return res.get_json()

    def respond(self, verifier_index, request_id, decision, code="auto"):
        """Approving sends a fresh valid code unless one is given."""
        body = {"decision": decision}
        if decision == "approve" and code == "auto":
            code = next_code(self.app, self.verifiers[verifier_index]["email"])
        if code is not None and code != "auto":
            body["code"] = code
        return self.verifier_clients[verifier_index].post(f"/api/requests/{request_id}/respond", json=body)

    def status(self, request_id):
        return self.elder_client.get(f"/api/requests/{request_id}").get_json()
