"""Small helpers shared by the Chunk 2 and Chunk 3 tests."""
from app import create_app
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
            self.verifiers.append(v)
            self.verifier_clients.append(c)

    def open_request(self, **overrides):
        res = self.elder_client.post("/api/requests", json={"answers": answers(**overrides)})
        assert res.status_code == 201, res.get_json()
        return res.get_json()

    def respond(self, verifier_index, request_id, decision):
        return self.verifier_clients[verifier_index].post(
            f"/api/requests/{request_id}/respond", json={"decision": decision}
        )

    def status(self, request_id):
        return self.elder_client.get(f"/api/requests/{request_id}").get_json()
