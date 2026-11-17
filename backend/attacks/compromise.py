"""Compromise attacks: the attacker already holds something real (a
password, a session, a phone, an account) and tries to get more than that
one thing should give them.

DEFENDED means the extra step was stopped. GAP means the attack worked
because of a known limit of the design, written up in the report.
"""
import pyotp
from flask import Flask
from flask.sessions import SecureCookieSessionInterface
from sqlalchemy import text

from app.models import AuditEvent, db

from .harness import Breach, Gap, PASSWORD, attack, crashed

# The signing key written in the public source code before it was made
# configurable. Anyone who can read the repository knows it.
PUBLISHED_DEV_KEY = "dev only key, replace before any real deployment"


# --- one stolen password -------------------------------------------------------

@attack("C01", "compromise", "Stolen password of a family member who has not finished authenticator setup")
def c01(ctx):
    fam = ctx.family("c01", verifiers=0)
    victim = fam.add_verifier("c01-v@example.com", "c01 victim", setup=False)
    rid = fam.open()
    c = victim.client  # the attacker is logged in with the stolen password
    info = c.get("/api/verifier/totp").get_json()
    if "secret" not in info:
        return None
    code = pyotp.TOTP(info["secret"]).at(ctx.clock())
    if c.post("/api/verifier/totp/confirm", json={"code": code}).status_code != 200:
        return None
    ctx.clock.advance(30)
    res = c.post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": pyotp.TOTP(info["secret"]).at(ctx.clock())})
    if res.status_code == 200 and fam.status(rid) == "verified":
        return Gap("with only the password, the attacker took over the unfinished authenticator setup and approved. Only possible before the real person finishes setup")


@attack("C02", "compromise", "Stolen password of a set up family member: guess the approval code", limited=True, logs=("rate_limited", "rejected"))
def c02(ctx):
    fam = ctx.family("c02", verifiers=1)
    rid = fam.open()
    evaluated = 0
    locked = False
    for guess in range(2000):
        res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": f"{guess:06d}"})
        if res.status_code == 429:
            locked = True
            break
        evaluated += 1
        if res.status_code == 200:
            return Breach(f"a guessed code was accepted after {evaluated} tries")
    if not locked:
        return Breach("no limit on code guessing")
    if evaluated > 5:
        return Breach(f"{evaluated} guesses were allowed before the lock")


@attack("C03", "compromise", "Use a stolen password to lock the real family member out of approving", limited=True)
def c03(ctx):
    fam = ctx.family("c03", verifiers=1)
    rid = fam.open()
    for _ in range(6):
        fam.vs[0].client.post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": "000000"})
    res = fam.approve(0, rid)
    if res.status_code == 429:
        return Gap("wrong guesses lock the account's approvals for about 15 minutes, which also blocks the real person. Accepted trade-off for stopping code guessing")


@attack("C04", "compromise", "One family member fully compromised (password and phone) on a two-person check", logs=("response_rejected", "rejected"))
def c04(ctx):
    fam = ctx.family("c04", verifiers=3)
    rid = fam.open(money=True)
    assert fam.approve(0, rid).status_code == 200
    again = fam.approve(0, rid)
    if again.status_code == 200 or fam.status(rid) == "verified":
        return Breach("one compromised person was enough for a two-person check")


@attack("C05", "compromise", "Compromised family member tries elder only actions", logs=("access_denied", "rejected"))
def c05(ctx):
    fam = ctx.family("c05", verifiers=2)
    c = fam.vs[0].client
    tries = [
        ("post", "/api/requests", {"answers": fam.answers()}),
        ("post", f"/api/elders/{fam.elder.id}/invites", {}),
        ("get", f"/api/elders/{fam.elder.id}/verifiers", None),
    ]
    for method, path, body in tries:
        res = getattr(c, method)(path, **({"json": body} if body is not None else {}))
        if res.status_code < 400:
            return Breach(f"{method.upper()} {path} worked for a family member")


@attack("C06", "compromise", "Compromised family member reads the activity log", logs=("access_denied", "rejected"))
def c06(ctx):
    fam = ctx.family("c06", verifiers=1)
    for path in ("/api/audit", "/api/audit/verify"):
        res = fam.vs[0].client.get(path)
        if res.status_code == 200:
            return Breach(f"{path} was readable by a family member")


@attack("C07", "compromise", "Two family members fully compromised on a two-person check")
def c07(ctx):
    fam = ctx.family("c07", verifiers=2)
    rid = fam.open(money=True)
    fam.approve(0, rid)
    fam.approve(1, rid)
    if fam.status(rid) == "verified":
        return Gap("an attacker holding two different family members' passwords and phones can approve. That is the limit of the two-person rule")


@attack("C08", "compromise", "Elder account compromised: add fake family members and approve")
def c08(ctx):
    fam = ctx.family("c08", verifiers=0)
    fake1 = fam.add_verifier("fake1@example.com", "fake1")
    fake2 = fam.add_verifier("fake2@example.com", "fake2")
    fam.vs += [fake1, fake2]
    rid = fam.open(money=True)
    fam.approve(0, rid)
    fam.approve(1, rid)
    if fam.status(rid) == "verified":
        return Gap("whoever controls the elder's account can invite their own people and approve. Not stopped today")


# --- sessions ------------------------------------------------------------------

def _forged_cookie(secret, user_id):
    app = Flask(__name__)
    app.secret_key = secret
    return SecureCookieSessionInterface().get_signing_serializer(app).dumps({"user_id": user_id})


@attack("C09", "compromise", "Forge a login cookie with a wrong guess of the signing key")
def c09(ctx):
    fam = ctx.family("c09", verifiers=0)
    c = ctx.anon()
    c.set_cookie("session", _forged_cookie("not the key", fam.elder.id))
    if c.get("/api/me").status_code == 200:
        return Breach("a cookie signed with the wrong key was accepted")


@attack("C10", "compromise", "Forge a login cookie using the signing key that was in the public source code")
def c10(ctx):
    fam = ctx.family("c10", verifiers=0)
    c = ctx.anon()
    c.set_cookie("session", _forged_cookie(PUBLISHED_DEV_KEY, fam.elder.id))
    res = c.get("/api/me")
    if res.status_code == 200 and res.get_json().get("id") == fam.elder.id:
        return Breach("anyone who read the public code could sign in as any account")


@attack("C11", "compromise", "Reuse a copied login cookie after the person signed out")
def c11(ctx):
    fam = ctx.family("c11", verifiers=0)
    stolen = fam.elder.client.get_cookie("session").value
    fam.elder.client.post("/api/logout")
    c = ctx.anon()
    c.set_cookie("session", stolen)
    if c.get("/api/me").status_code == 200:
        return Gap("a copied cookie still works after sign out until it expires (sessions are signed cookies, not stored on the server)")


@attack("C12", "compromise", "Guess a family member's password at login", limited=True, logs=("rate_limited", "rejected"))
def c12(ctx):
    fam = ctx.family("c12", verifiers=1)
    c = ctx.anon()
    allowed = 0
    for i in range(30):
        res = c.post("/api/login", json={"email": fam.vs[0].email, "password": f"guess-{i:04d}-wrong"})
        if res.status_code == 429:
            break
        allowed += 1
    else:
        return Breach("no limit on password guessing")
    if allowed > 5:
        return Breach(f"{allowed} guesses were allowed before the lock")


@attack("C13", "compromise", "Try thousands of different emails from one place (credential stuffing)", limited=True, logs=("rate_limited", "rejected"))
def c13(ctx):
    c = ctx.anon()
    for i in range(80):
        res = c.post("/api/login", json={"email": f"user{i}@example.com", "password": "Summer2026!"})
        if res.status_code == 429:
            return None
    return Breach("80 different logins in a row were never slowed down")


@attack("C14", "compromise", "Lock a real person out of logging in by guessing their password", limited=True)
def c14(ctx):
    fam = ctx.family("c14", verifiers=0)
    c = ctx.anon()
    for i in range(6):
        c.post("/api/login", json={"email": fam.elder.email, "password": f"wrong-{i}-wrong"})
    res = ctx.anon().post("/api/login", json={"email": fam.elder.email, "password": PASSWORD})
    if res.status_code == 429:
        return Gap("wrong guesses lock that account's login for about 15 minutes, which also blocks the real person")


# --- information leaks ---------------------------------------------------------

@attack("C15", "compromise", "Tell whether an email has an account from the login response")
def c15(ctx):
    fam = ctx.family("c15", verifiers=0)
    real = ctx.anon().post("/api/login", json={"email": fam.elder.email, "password": "wrong password"})
    fake = ctx.anon().post("/api/login", json={"email": "nobody@example.com", "password": "wrong password"})
    if real.status_code != fake.status_code or real.get_json() != fake.get_json():
        return Breach("login answers differ for real and unknown emails")


@attack("C16", "compromise", "Tell whether an email has an account from the sign up response")
def c16(ctx):
    fam = ctx.family("c16", verifiers=0)
    res = ctx.anon().post("/api/elders", json={"name": "X", "email": fam.elder.email, "password": PASSWORD})
    if res.status_code == 409:
        return Gap("sign up says an email is already taken, which confirms that person has an account. Low risk, common trade-off")


@attack("C17", "compromise", "Look for passwords, hashes or authenticator secrets in what the server sends back")
def c17(ctx):
    fam = ctx.family("c17", verifiers=1)
    seen = [
        fam.vs[0].client.get("/api/me").get_data(as_text=True),
        fam.vs[0].client.get("/api/verifier/totp").get_data(as_text=True),
        fam.elder.client.get("/api/me").get_data(as_text=True),
        fam.elder.client.get(f"/api/elders/{fam.elder.id}/verifiers").get_data(as_text=True),
        fam.elder.client.get("/api/audit").get_data(as_text=True),
    ]
    secret = fam.vs[0].secret()
    for body in seen:
        if secret in body or "argon2" in body or "password_hash" in body or "totp_secret" in body:
            return Breach("a secret showed up in a response")


# --- the activity log itself ---------------------------------------------------

@attack("C18", "compromise", "Add, change or delete activity log entries through the API")
def c18(ctx):
    fam = ctx.family("c18", verifiers=1)
    for method in ("post", "put", "patch", "delete"):
        for path in ("/api/audit", "/api/audit/1"):
            res = getattr(fam.elder.client, method)(path, json={"event_type": "nothing_happened"})
            if res.status_code < 400:
                return Breach(f"{method.upper()} {path} returned {res.status_code}")


@attack("C19", "compromise", "Edit the activity log directly in the database")
def c19(ctx):
    fam = ctx.family("c19", verifiers=2)
    rid = fam.open()
    fam.decline(0, rid)
    with ctx.app.app_context():
        target = AuditEvent.query.filter_by(event_type="response_declined").one().id
        db.session.execute(text("UPDATE audit_events SET event_type='response_approved' WHERE id=:i"), {"i": target})
        db.session.commit()
    res = fam.elder.client.get("/api/audit/verify").get_json()
    if res["intact"]:
        return Breach("an edited log entry was not noticed")


@attack("C20", "compromise", "Delete log entries from the middle of the log to hide an attack")
def c20(ctx):
    fam = ctx.family("c20", verifiers=1)
    fam.vs[0].client.post("/api/login", json={"email": fam.vs[0].email, "password": "wrong"})
    fam.vs[0].client.post("/api/logout")
    with ctx.app.app_context():
        db.session.execute(text("DELETE FROM audit_events WHERE event_type='login_failed'"))
        db.session.commit()
    if fam.elder.client.get("/api/audit/verify").get_json()["intact"]:
        return Breach("deleted log entries were not noticed")


@attack("C21", "compromise", "Delete the newest log entries so the last thing that happened disappears")
def c21(ctx):
    fam = ctx.family("c25", verifiers=1)
    fam.vs[0].client.post("/api/login", json={"email": fam.vs[0].email, "password": "wrong"})
    with ctx.app.app_context():
        last = AuditEvent.query.order_by(AuditEvent.id.desc()).first().id
        db.session.execute(text("DELETE FROM audit_events WHERE id=:i"), {"i": last})
        db.session.commit()
    if fam.elder.client.get("/api/audit/verify").get_json()["intact"]:
        return Gap("removing only the newest entries leaves a chain that still checks out, because nothing after them points back. Fix: copy the latest fingerprint somewhere else from time to time")


@attack("C22", "compromise", "Edit a log entry and rewrite every fingerprint after it (database access only)")
def c22(ctx):
    import hashlib
    import json

    fam = ctx.family("c26", verifiers=2)
    rid = fam.open()
    fam.decline(0, rid)
    with ctx.app.app_context():
        rows = [
            dict(id=e.id, created_at=e.created_at, event_type=e.event_type, outcome=e.outcome, actor_id=e.actor_id,
                 elder_id=e.elder_id, request_id=e.request_id, ip=e.ip, detail=e.detail)
            for e in AuditEvent.query.order_by(AuditEvent.id).all()
        ]
        db.session.rollback()
        prev = AuditEvent.GENESIS
        for r in rows:
            if r["event_type"] == "response_declined":
                r["event_type"] = "response_approved"
            # The attacker has read the public code, so they know how the
            # fingerprint is computed, but they do not have the server key.
            payload = json.dumps(
                [prev, r["created_at"].isoformat(), r["event_type"], r["outcome"], r["actor_id"], r["elder_id"], r["request_id"], r["ip"], r["detail"]],
                sort_keys=True, separators=(",", ":"),
            )
            r["prev_hash"], r["hash"] = prev, hashlib.sha256(payload.encode()).hexdigest()
            prev = r["hash"]
        for r in rows:
            db.session.execute(
                text("UPDATE audit_events SET event_type=:t, prev_hash=:p, hash=:h WHERE id=:i"),
                {"t": r["event_type"], "p": r["prev_hash"], "h": r["hash"], "i": r["id"]},
            )
        db.session.commit()
    if fam.elder.client.get("/api/audit/verify").get_json()["intact"]:
        return Breach("a rewritten log passed the check")


@attack("C23", "compromise", "Change a check to approved directly in the database")
def c23(ctx):
    fam = ctx.family("c21", verifiers=1)
    rid = fam.open(money=True)
    with ctx.app.app_context():
        db.session.execute(text("UPDATE verification_requests SET status='VERIFIED' WHERE id=:i"), {"i": rid})
        db.session.commit()
    shown = fam.elder.client.get(f"/api/requests/{rid}").get_json()["status"]
    if shown == "verified":
        approvals = [e for e in ctx.events("response_approved") if e["request_id"] == rid]
        if not approvals:
            return Gap("the app trusts the database: it shows approved, though the log has no approvals for it. The mismatch is visible in the log but not checked automatically")


# --- browser style attacks and replays -----------------------------------------

@attack("C24", "compromise", "Make a request on the elder's behalf from another website (cross-site post)")
def c24(ctx):
    fam = ctx.family("c22", verifiers=1)
    before = len(fam.elder.client.get("/api/audit").get_json())
    res = fam.elder.client.post(
        "/api/requests",
        data='{"answers": {"money": false, "secrecy": false, "urgency": false, "sensitive_info": false, "unfamiliarity": false, "unusual_contact": false}}',
        content_type="text/plain",
    )
    if res.status_code == 201:
        return Breach("a plain text post from another site created a check")


@attack("C25", "compromise", "Ask from an untrusted website origin and see if the server allows it")
def c25(ctx):
    fam = ctx.family("c23", verifiers=0)
    evil = fam.elder.client.get("/api/me", headers={"Origin": "https://evil.example"})
    if evil.headers.get("Access-Control-Allow-Origin"):
        return Breach("the server allowed an untrusted origin")
    good = fam.elder.client.get("/api/me", headers={"Origin": "http://localhost:5173"})
    if good.headers.get("Access-Control-Allow-Origin") != "http://localhost:5173":
        return Breach("the real app origin was not allowed, so the check above proves nothing")


@attack("C26", "compromise", "Capture an approval request and send the exact same one again", logs=("response_rejected", "rejected"))
def c26(ctx):
    fam = ctx.family("c24", verifiers=2)
    rid = fam.open(money=True)
    body = {"decision": "approve", "code": fam.vs[0].code()}
    first = fam.vs[0].client.post(f"/api/requests/{rid}/respond", json=body)
    assert first.status_code == 200
    second = fam.vs[0].client.post(f"/api/requests/{rid}/respond", json=body)
    if second.status_code == 200 or fam.status(rid) == "verified":
        return Breach("a captured approval worked twice")


@attack("C27", "compromise", "Coached elder: a scammer talks the elder into answering no to every risk question")
def c27(ctx):
    fam = ctx.family("c27", verifiers=2)
    rid = fam.open(money=False)  # the elder says "no money asked", though it is a scam
    fam.approve(0, rid)
    if fam.status(rid) == "verified":
        return Gap("if the elder is coached to answer no, the check needs only one family member. The six questions are only as honest as the elder's answers. The caller note and the family member's own call back are the backstop")
