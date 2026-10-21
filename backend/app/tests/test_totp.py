"""Phase 4: TOTP codes for approvals, replay protection for those codes,
and rate limiting on guessing. Each test is one rule from the threat model.
"""
import pyotp

from app.models import User
from app.tests.helpers import (
    PASSWORD,
    Family,
    answers,
    confirm_totp,
    enroll_verifier,
    login,
    next_code,
    register_elder,
)


def _family(app, n=1, confirm=True):
    """A family whose members have (or have not) finished authenticator setup."""
    if confirm:
        return Family(app, verifiers=n)
    elder = register_elder(app.test_client())
    elder_client = app.test_client()
    login(elder_client, elder["email"])
    verifier = enroll_verifier(app, elder, "v0@example.com")
    vc = app.test_client()
    login(vc, "v0@example.com")
    return elder_client, vc, verifier


# --- setup ------------------------------------------------------------------

def test_setup_gives_a_secret_until_confirmed_then_never_again(app):
    elder_client, vc, _ = _family(app, confirm=False)
    first = vc.get("/api/verifier/totp").get_json()
    assert first["confirmed"] is False
    assert first["uri"].startswith("otpauth://totp/")
    assert "issuer=CallBack" in first["uri"]

    assert vc.post("/api/verifier/totp/confirm", json={"code": next_code(app, "v0@example.com")}).status_code == 200
    after = vc.get("/api/verifier/totp").get_json()
    assert after == {"confirmed": True}
    assert "secret" not in after and "uri" not in after


def test_setup_is_not_confirmed_by_a_wrong_code(app):
    _, vc, _ = _family(app, confirm=False)
    res = vc.post("/api/verifier/totp/confirm", json={"code": "000000"})
    assert res.status_code == 401
    assert vc.get("/api/me").get_json()["totp_confirmed"] is False


def test_the_secret_is_never_in_account_responses(app):
    fam = Family(app, verifiers=1)
    with app.app_context():
        secret = User.query.filter_by(email="verifier0@example.com").first().totp_secret
    for res in (
        fam.verifier_clients[0].get("/api/me"),
        fam.elder_client.get(f"/api/elders/{fam.elder['id']}/verifiers"),
    ):
        assert secret not in res.get_data(as_text=True)


def test_only_a_family_member_can_see_setup(app):
    fam = Family(app, verifiers=1)
    assert fam.elder_client.get("/api/verifier/totp").status_code == 403
    assert app.test_client().get("/api/verifier/totp").status_code == 401


# --- approving needs a code -------------------------------------------------

def test_approve_before_setup_is_refused(app):
    elder_client, vc, _ = _family(app, confirm=False)
    req = elder_client.post("/api/requests", json={"answers": answers()}).get_json()
    res = vc.post(f"/api/requests/{req['id']}/respond", json={"decision": "approve", "code": "123456"})
    assert res.status_code == 403
    assert res.get_json()["code"] == "totp_setup_required"
    assert elder_client.get(f"/api/requests/{req['id']}").get_json()["status"] == "pending"


def test_approve_without_a_code_is_refused(app):
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    for body in ({"decision": "approve"}, {"decision": "approve", "code": None}, {"decision": "approve", "code": ""}):
        res = fam.verifier_clients[0].post(f"/api/requests/{req['id']}/respond", json=body)
        assert res.status_code == 401, body
    assert fam.status(req["id"])["status"] == "pending"


def test_approve_with_a_wrong_or_malformed_code_is_refused(app):
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    for bad in ("000000", "12345", "1234567", "abcdef", 123456, ["123456"], {"a": 1}, True):
        assert fam.respond(0, req["id"], "approve", code=bad).status_code == 401, bad
    assert fam.status(req["id"])["status"] == "pending"


def test_approve_with_a_valid_code_works(app):
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    assert fam.respond(0, req["id"], "approve").status_code == 200
    assert fam.status(req["id"])["status"] == "verified"


def test_a_code_from_another_family_members_phone_is_refused(app):
    fam = Family(app, verifiers=2)
    req = fam.open_request(money=True)
    other_code = next_code(app, "verifier1@example.com")
    assert fam.respond(0, req["id"], "approve", code=other_code).status_code == 401


def test_an_old_code_is_refused(app):
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    with app.app_context():
        secret = User.query.filter_by(email="verifier0@example.com").first().totp_secret
    old = pyotp.TOTP(secret).at(app.clock() - 300)  # five minutes ago
    assert fam.respond(0, req["id"], "approve", code=old).status_code == 401


def test_a_code_outside_the_time_window_is_refused(app):
    """Not an old one (the replay rule would catch that first): one from a
    few minutes in the future, which no real phone would show yet.
    """
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    with app.app_context():
        secret = User.query.filter_by(email="verifier0@example.com").first().totp_secret
    future = pyotp.TOTP(secret).at(app.clock() + 150)
    assert fam.respond(0, req["id"], "approve", code=future).status_code == 401


def test_declining_needs_no_code(app):
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    assert fam.respond(0, req["id"], "decline", code=None).status_code == 200
    assert fam.status(req["id"])["status"] == "denied"


# --- replay protection ------------------------------------------------------

def test_a_code_cannot_be_used_twice(app):
    fam = Family(app, verifiers=1)
    first = fam.open_request()
    second = fam.open_request()
    code = next_code(app, "verifier0@example.com")
    assert fam.respond(0, first["id"], "approve", code=code).status_code == 200
    replay = fam.respond(0, second["id"], "approve", code=code)
    assert replay.status_code == 401
    assert fam.status(second["id"])["status"] == "pending"


def test_an_older_code_than_the_last_used_is_refused(app):
    fam = Family(app, verifiers=1)
    first = fam.open_request()
    second = fam.open_request()
    with app.app_context():
        secret = User.query.filter_by(email="verifier0@example.com").first().totp_secret
    older = pyotp.TOTP(secret).at(app.clock() + 30 - 30)  # the current window
    app.clock.advance(30)
    newer = pyotp.TOTP(secret).at(app.clock())
    assert fam.respond(0, first["id"], "approve", code=newer).status_code == 200
    assert fam.respond(0, second["id"], "approve", code=older).status_code == 401


def test_a_failed_attempt_does_not_use_up_a_code(app):
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    code = next_code(app, "verifier0@example.com")
    assert fam.respond(0, req["id"], "approve", code="000000").status_code == 401
    assert fam.respond(0, req["id"], "approve", code=code).status_code == 200


def test_two_person_request_needs_a_code_from_each_member(app):
    fam = Family(app, verifiers=2)
    req = fam.open_request(money=True)
    assert fam.respond(0, req["id"], "approve").status_code == 200
    assert fam.status(req["id"])["status"] == "pending"
    assert fam.respond(1, req["id"], "approve", code="000000").status_code == 401
    assert fam.status(req["id"])["status"] == "pending"
    assert fam.respond(1, req["id"], "approve").status_code == 200
    assert fam.status(req["id"])["status"] == "verified"


# --- rate limiting ----------------------------------------------------------

def test_wrong_codes_lock_out_guessing_even_a_right_code(limited_app):
    app = limited_app
    fam = Family(app, verifiers=1)
    req = fam.open_request()
    for _ in range(5):
        assert fam.respond(0, req["id"], "approve", code="000000").status_code == 401
    locked = fam.respond(0, req["id"], "approve")  # a valid code now
    assert locked.status_code == 429
    assert fam.status(req["id"])["status"] == "pending"


def test_wrong_passwords_lock_that_account_not_others(limited_app):
    app = limited_app
    elder = register_elder(app.test_client(), email="a@example.com")
    register_elder(app.test_client(), email="b@example.com", name="Other")
    c = app.test_client()
    for _ in range(5):
        assert c.post("/api/login", json={"email": "a@example.com", "password": "wrong password"}).status_code == 401
    # Even the right password is refused for a while.
    assert c.post("/api/login", json={"email": "a@example.com", "password": PASSWORD}).status_code == 429
    # A different account is unaffected.
    assert c.post("/api/login", json={"email": "b@example.com", "password": PASSWORD}).status_code == 200


def test_normal_use_is_not_blocked(limited_app):
    app = limited_app
    register_elder(app.test_client())
    c = app.test_client()
    for _ in range(10):
        assert c.post("/api/login", json={"email": "grandma@example.com", "password": PASSWORD}).status_code == 200


def test_too_many_attempts_message_is_plain_json(limited_app):
    app = limited_app
    register_elder(app.test_client())
    c = app.test_client()
    for _ in range(5):
        c.post("/api/login", json={"email": "grandma@example.com", "password": "nope nope nope"})
    res = c.post("/api/login", json={"email": "grandma@example.com", "password": PASSWORD})
    assert res.status_code == 429
    assert "too many attempts" in res.get_json()["error"]
