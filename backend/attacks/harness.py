"""What every attack gets: a fresh copy of the real app on a throwaway
database, a way to build a family, and a way to read the audit log.

An attack is a function that tries to do something it should not be able to
do. It returns None if the system stopped it, Breach(...) if the attack
worked and should not have, or Gap(...) if it worked but that is a known
limit of the design that is written up in the report.
"""
from dataclasses import dataclass

import pyotp

from app import create_app
from app.limiter import limiter
from app.models import AuditEvent, Invite, User, VerificationRequest, db, _utcnow
from app.tests.conftest import FakeClock

PASSWORD = "correct horse battery"
KEYS = ["money", "secrecy", "urgency", "sensitive_info", "unfamiliarity", "unusual_contact"]


@dataclass
class Breach:
    note: str


@dataclass
class Gap:
    note: str


ATTACKS = []


def attack(id, kind, title, *, limited=False, logs=None):
    """Register an attack. kind is "bypass" or "compromise". logs is the
    audit event type (and outcome) that a good defense should leave behind.
    """

    def wrap(fn):
        ATTACKS.append({"id": id, "kind": kind, "title": title, "fn": fn, "limited": limited, "logs": logs})
        return fn

    return wrap


class Person:
    def __init__(self, ctx, email, name, client, user=None):
        self.ctx, self.email, self.name, self.client, self.user = ctx, email, name, client, user

    @property
    def id(self):
        return self.user["id"] if self.user else None

    def secret(self):
        with self.ctx.app.app_context():
            return User.query.filter_by(email=self.email).first().totp_secret

    def code(self, steps=0):
        """A code from this person's authenticator app. Moves the fake clock
        on 30 seconds first so it is never one that was already used.
        steps shifts it into the past (negative) or future (positive).
        """
        self.ctx.app.clock.advance(30)
        t = self.ctx.app.clock() + steps * 30
        return pyotp.TOTP(self.secret()).at(t)


class Family:
    def __init__(self, ctx, prefix, verifiers):
        self.ctx = ctx
        app = ctx.app
        c = app.test_client()
        res = c.post("/api/elders", json={"name": f"{prefix} elder", "email": f"{prefix}-elder@example.com", "password": PASSWORD})
        assert res.status_code == 201, res.get_json()
        self.elder = Person(ctx, f"{prefix}-elder@example.com", f"{prefix} elder", c, res.get_json())
        assert c.post("/api/login", json={"email": self.elder.email, "password": PASSWORD}).status_code == 200
        self.vs = []
        for i in range(verifiers):
            self.vs.append(self.add_verifier(f"{prefix}-v{i}@example.com", f"{prefix} v{i}"))

    def invite(self):
        res = self.elder.client.post(f"/api/elders/{self.elder.id}/invites", json={})
        assert res.status_code == 201
        return res.get_json()["token"]

    def add_verifier(self, email, name, setup=True):
        c = self.ctx.app.test_client()
        res = c.post("/api/verifiers", json={"invite_token": self.invite(), "name": name, "email": email, "password": PASSWORD})
        assert res.status_code == 201, res.get_json()
        assert c.post("/api/login", json={"email": email, "password": PASSWORD}).status_code == 200
        person = Person(self.ctx, email, name, c, res.get_json())
        if setup:
            c.get("/api/verifier/totp")
            assert c.post("/api/verifier/totp/confirm", json={"code": person.code()}).status_code == 200
        return person

    def answers(self, **overrides):
        base = {k: False for k in KEYS}
        base.update(overrides)
        return base

    def open(self, money=False):
        """Opens a check. money=True makes it a two-person check."""
        res = self.elder.client.post("/api/requests", json={"answers": self.answers(money=money)})
        assert res.status_code == 201, res.get_json()
        return res.get_json()["id"]

    def approve(self, i, rid, code="fresh"):
        who = self.vs[i]
        body = {"decision": "approve", "code": who.code() if code == "fresh" else code}
        return who.client.post(f"/api/requests/{rid}/respond", json=body)

    def decline(self, i, rid):
        return self.vs[i].client.post(f"/api/requests/{rid}/respond", json={"decision": "decline"})

    def status(self, rid):
        with self.ctx.app.app_context():
            return db.session.get(VerificationRequest, rid).status.value


class Ctx:
    def __init__(self, limited):
        self.clock = FakeClock()
        self.app = create_app({
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "RATELIMIT_ENABLED": limited,
            "TOTP_NOW": self.clock,
            # Real behavior: a server error comes back as a 500 response
            # instead of stopping the script, so a crash counts as a finding.
            "TESTING": False,
            "PROPAGATE_EXCEPTIONS": False,
        })
        self.app.clock = self.clock
        if limited:
            limiter.reset()

    def family(self, prefix="fam", verifiers=2):
        return Family(self, prefix, verifiers)

    def anon(self):
        return self.app.test_client()

    def events(self, event_type=None, outcome=None):
        with self.app.app_context():
            q = AuditEvent.query
            if event_type:
                q = q.filter_by(event_type=event_type)
            if outcome:
                q = q.filter_by(outcome=outcome)
            return [e.to_dict() for e in q.order_by(AuditEvent.id).all()]

    def expire_request(self, rid):
        from datetime import timedelta
        with self.app.app_context():
            r = db.session.get(VerificationRequest, rid)
            r.expires_at = _utcnow() - timedelta(seconds=1)
            db.session.commit()

    def expire_invite(self, token):
        from datetime import timedelta
        with self.app.app_context():
            i = Invite.query.filter_by(token=token).first()
            i.expires_at = _utcnow() - timedelta(seconds=1)
            db.session.commit()

    def teardown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()


def crashed(res):
    return res.status_code >= 500
