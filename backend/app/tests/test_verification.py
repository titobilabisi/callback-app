"""Tests for Chunk 3: verification requests and approve / decline.

Covers the happy paths for single and two-person approval, and then the
adversarial cases from the test plan: a single account trying to satisfy a
two-person request, replayed and expired responses, and verifiers or
elders reaching for requests that are not theirs.
"""
from datetime import timedelta

import pytest

from app.models import RequestStatus, VerificationRequest, _utcnow, db
from app.tests.helpers import Family, answers, enroll_verifier, login, register_elder


def expire(app, request_id):
    """Push a request's deadline into the past, as if time had run out."""
    with app.app_context():
        req = db.session.get(VerificationRequest, request_id)
        req.expires_at = _utcnow() - timedelta(seconds=1)
        db.session.commit()


# ----- login and roles -----

def test_login_logout_and_me(app):
    family = Family(app, verifiers=1)
    c = app.test_client()
    assert c.get("/api/me").status_code == 401
    login(c, "grandma@example.com")
    assert c.get("/api/me").get_json()["role"] == "elder"
    c.post("/api/logout")
    assert c.get("/api/me").status_code == 401


def test_wrong_password_and_unknown_email_look_the_same(app):
    Family(app, verifiers=1)
    c = app.test_client()
    wrong_pw = c.post("/api/login", json={"email": "grandma@example.com", "password": "nope nope nope"})
    no_user = c.post("/api/login", json={"email": "nobody@example.com", "password": "nope nope nope"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.get_json() == no_user.get_json()


def test_requests_require_login(client):
    assert client.post("/api/requests", json={"answers": answers()}).status_code == 401
    assert client.get("/api/requests/1").status_code == 401
    assert client.post("/api/requests/1/respond", json={"decision": "approve"}).status_code == 401
    assert client.get("/api/verifier/requests").status_code == 401


def test_verifier_cannot_open_a_request(app):
    family = Family(app, verifiers=1)
    res = family.verifier_clients[0].post("/api/requests", json={"answers": answers()})
    assert res.status_code == 403


def test_elder_cannot_respond_to_their_own_request(app):
    family = Family(app, verifiers=1)
    req = family.open_request()
    res = family.elder_client.post(f"/api/requests/{req['id']}/respond", json={"decision": "approve"})
    assert res.status_code == 403
    assert family.status(req["id"])["status"] == "pending"


# ----- creating requests -----

def test_cannot_open_a_request_with_nobody_enrolled(app):
    family = Family(app, verifiers=0)
    res = family.elder_client.post("/api/requests", json={"answers": answers()})
    assert res.status_code == 409


def test_new_request_starts_pending_with_a_deadline(app):
    family = Family(app, verifiers=1)
    req = family.open_request()
    assert req["status"] == "pending"
    assert req["approvals"] == 0
    assert 0 < req["seconds_left"] <= 300


def test_two_person_request_with_one_family_member_is_not_downgraded(app):
    family = Family(app, verifiers=1)
    req = family.open_request(money=True)
    assert req["route"] == "two_person"
    assert req["required_approvals"] == 2
    assert req["can_be_completed"] is False


# ----- single approval -----

def test_single_approval_verifies(app):
    family = Family(app, verifiers=2)
    req = family.open_request(urgency=True)
    assert req["route"] == "single"
    res = family.respond(0, req["id"], "approve")
    assert res.status_code == 200
    assert res.get_json()["status"] == "verified"
    assert family.status(req["id"])["status"] == "verified"


def test_single_decline_denies(app):
    family = Family(app, verifiers=2)
    req = family.open_request()
    assert family.respond(0, req["id"], "decline").get_json()["status"] == "denied"
    assert family.status(req["id"])["status"] == "denied"


# ----- two-person approval -----

def test_two_person_needs_two_distinct_approvals(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)

    first = family.respond(0, req["id"], "approve").get_json()
    assert first["status"] == "pending"
    assert first["approvals"] == 1
    assert family.status(req["id"])["status"] == "pending"

    second = family.respond(1, req["id"], "approve").get_json()
    assert second["status"] == "verified"
    assert second["approvals"] == 2


def test_decline_after_one_approval_still_denies(app):
    family = Family(app, verifiers=2)
    req = family.open_request(sensitive_info=True)
    family.respond(0, req["id"], "approve")
    res = family.respond(1, req["id"], "decline")
    assert res.get_json()["status"] == "denied"


def test_same_verifier_cannot_approve_twice(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)
    assert family.respond(0, req["id"], "approve").status_code == 200
    again = family.respond(0, req["id"], "approve")
    assert again.status_code == 409
    status = family.status(req["id"])
    assert status["status"] == "pending"
    assert status["approvals"] == 1


def test_same_verifier_cannot_change_their_answer(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)
    family.respond(0, req["id"], "approve")
    assert family.respond(0, req["id"], "decline").status_code == 409
    assert family.status(req["id"])["status"] == "pending"


def test_30_attempts_to_finish_a_high_risk_request_with_one_identity_all_fail(app):
    """Test plan, Approval integrity: 0 of 30 attempts succeed."""
    family = Family(app, verifiers=2)
    succeeded = 0
    for _ in range(30):
        req = family.open_request(money=True)
        family.respond(0, req["id"], "approve")
        for _ in range(3):
            family.respond(0, req["id"], "approve")
        if family.status(req["id"])["status"] == "verified":
            succeeded += 1
    assert succeeded == 0


def test_20_compromised_verifier_scenarios_all_fail(app):
    """Test plan, Compromise resistance: one fully compromised verifier
    account tries to finish a two-person request alone. 0 of 20 succeed.
    """
    family = Family(app, verifiers=3)
    succeeded = 0
    for _ in range(20):
        req = family.open_request(money=True, sensitive_info=True)
        for _ in range(5):
            family.respond(0, req["id"], "approve")
        if family.status(req["id"])["status"] == "verified":
            succeeded += 1
    assert succeeded == 0


def test_two_person_request_can_never_finish_with_one_enrolled_verifier(app):
    family = Family(app, verifiers=1)
    req = family.open_request(money=True)
    for _ in range(5):
        family.respond(0, req["id"], "approve")
    assert family.status(req["id"])["status"] == "pending"


# ----- who is allowed to respond or read -----

def test_verifier_of_a_different_elder_is_rejected(app):
    family = Family(app, verifiers=1)
    req = family.open_request()

    setup = app.test_client()
    other_elder = register_elder(setup, email="other.elder@example.com", name="Other Elder")
    enroll_verifier(app, other_elder, "stranger@example.com", name="Stranger")
    stranger = app.test_client()
    login(stranger, "stranger@example.com")

    res = stranger.post(f"/api/requests/{req['id']}/respond", json={"decision": "approve"})
    assert res.status_code == 403
    assert family.status(req["id"])["status"] == "pending"
    assert family.status(req["id"])["approvals"] == 0


def test_another_elder_cannot_read_a_request(app):
    family = Family(app, verifiers=1)
    req = family.open_request()

    setup = app.test_client()
    register_elder(setup, email="other.elder@example.com", name="Other Elder")
    other = app.test_client()
    login(other, "other.elder@example.com")
    assert other.get(f"/api/requests/{req['id']}").status_code == 404


def test_verifier_cannot_use_the_elder_status_endpoint(app):
    family = Family(app, verifiers=1)
    req = family.open_request()
    res = family.verifier_clients[0].get(f"/api/requests/{req['id']}")
    assert res.status_code == 403


def test_unknown_request_is_404(app):
    family = Family(app, verifiers=1)
    assert family.respond(0, 9999, "approve").status_code == 404
    assert family.elder_client.get("/api/requests/9999").status_code == 404


@pytest.mark.parametrize("bad", [None, "", "maybe", "APPROVE", True, 1])
def test_invalid_decision_is_rejected(app, bad):
    family = Family(app, verifiers=1)
    req = family.open_request()
    res = family.verifier_clients[0].post(f"/api/requests/{req['id']}/respond", json={"decision": bad})
    assert res.status_code == 400
    assert family.status(req["id"])["status"] == "pending"


# ----- expiry and replay -----

def test_unanswered_request_ends_as_unable_to_verify(app):
    family = Family(app, verifiers=1)
    req = family.open_request()
    expire(app, req["id"])
    status = family.status(req["id"])
    assert status["status"] == "unable_to_verify"
    assert status["seconds_left"] == 0


def test_expired_request_cannot_be_approved_late(app):
    family = Family(app, verifiers=2)
    req = family.open_request()
    expire(app, req["id"])
    res = family.respond(0, req["id"], "approve")
    assert res.status_code == 410
    assert family.status(req["id"])["status"] == "unable_to_verify"


def test_expiry_is_enforced_even_if_nobody_looked_in_between(app):
    """The status is only a stored 'pending' until something reads it. The
    response path must still refuse a late approval on its own.
    """
    family = Family(app, verifiers=2)
    req = family.open_request()
    expire(app, req["id"])
    with app.app_context():
        assert db.session.get(VerificationRequest, req["id"]).status == RequestStatus.PENDING
    assert family.respond(0, req["id"], "approve").status_code == 410


def test_half_approved_two_person_request_expires_to_unable_to_verify(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)
    family.respond(0, req["id"], "approve")
    expire(app, req["id"])
    assert family.respond(1, req["id"], "approve").status_code == 410
    assert family.status(req["id"])["status"] == "unable_to_verify"


def test_finished_request_cannot_be_changed(app):
    family = Family(app, verifiers=2)
    req = family.open_request()
    family.respond(0, req["id"], "approve")
    assert family.status(req["id"])["status"] == "verified"
    assert family.respond(1, req["id"], "decline").status_code == 409
    assert family.status(req["id"])["status"] == "verified"


def test_denied_request_cannot_be_flipped_to_verified(app):
    family = Family(app, verifiers=2)
    req = family.open_request()
    family.respond(0, req["id"], "decline")
    assert family.respond(1, req["id"], "approve").status_code == 409
    assert family.status(req["id"])["status"] == "denied"


def test_30_expired_or_replayed_responses_are_all_rejected(app):
    """Test plan, Expiry & replay: 100% rejected."""
    family = Family(app, verifiers=2)
    accepted = 0

    for _ in range(15):  # expired
        req = family.open_request()
        expire(app, req["id"])
        if family.respond(0, req["id"], "approve").status_code == 200:
            accepted += 1

    for _ in range(15):  # replayed after the request was already answered
        req = family.open_request(money=True)
        family.respond(0, req["id"], "approve")
        if family.respond(0, req["id"], "approve").status_code == 200:
            accepted += 1

    assert accepted == 0


# ----- verifier inbox -----

def test_inbox_shows_open_requests_with_the_call_summary(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True, urgency=True)
    inbox = family.verifier_clients[0].get("/api/verifier/requests").get_json()
    assert [r["id"] for r in inbox] == [req["id"]]
    item = inbox[0]
    assert item["elder_name"] == "Grandma"
    assert item["route"] == "two_person"
    by_key = {row["key"]: row["value"] for row in item["summary"]}
    assert by_key["money"] is True
    assert by_key["urgency"] is True
    assert by_key["secrecy"] is False
    assert len(item["summary"]) == 6


def test_inbox_hides_requests_this_verifier_already_answered(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)
    family.respond(0, req["id"], "approve")
    assert family.verifier_clients[0].get("/api/verifier/requests").get_json() == []
    # The second verifier still needs to see it.
    assert [r["id"] for r in family.verifier_clients[1].get("/api/verifier/requests").get_json()] == [req["id"]]


def test_inbox_hides_finished_and_expired_requests(app):
    family = Family(app, verifiers=2)
    done = family.open_request()
    family.respond(0, done["id"], "approve")
    late = family.open_request()
    expire(app, late["id"])
    assert family.verifier_clients[1].get("/api/verifier/requests").get_json() == []


def test_inbox_never_shows_another_elders_requests(app):
    family = Family(app, verifiers=1)
    family.open_request()

    setup = app.test_client()
    other_elder = register_elder(setup, email="other.elder@example.com", name="Other Elder")
    enroll_verifier(app, other_elder, "stranger@example.com", name="Stranger")
    stranger = app.test_client()
    login(stranger, "stranger@example.com")
    assert stranger.get("/api/verifier/requests").get_json() == []


def test_elder_cannot_read_the_verifier_inbox(app):
    family = Family(app, verifiers=1)
    assert family.elder_client.get("/api/verifier/requests").status_code == 403


# --- Caller note (optional text the family member sees) ---------------------

def test_caller_note_reaches_the_family_member(app):
    fam = Family(app, verifiers=1)
    res = fam.elder_client.post(
        "/api/requests", json={"answers": answers(), "caller_note": "  Says he is   from my insurance "}
    )
    assert res.status_code == 201
    inbox = fam.verifier_clients[0].get("/api/verifier/requests").get_json()
    assert inbox[0]["caller_note"] == "Says he is from my insurance"


def test_caller_note_is_optional_and_blank_means_none(app):
    fam = Family(app, verifiers=1)
    for body in ({"answers": answers()}, {"answers": answers(), "caller_note": "   "}):
        assert fam.elder_client.post("/api/requests", json=body).status_code == 201
    inbox = fam.verifier_clients[0].get("/api/verifier/requests").get_json()
    assert [r["caller_note"] for r in inbox] == [None, None]


def test_caller_note_must_be_short_text(app):
    fam = Family(app, verifiers=1)
    for bad in ("x" * 141, 123, ["a"], {"a": 1}, True):
        res = fam.elder_client.post("/api/requests", json={"answers": answers(), "caller_note": bad})
        assert res.status_code == 400, bad


def test_caller_note_never_changes_the_route(app):
    fam = Family(app, verifiers=2)
    res = fam.elder_client.post(
        "/api/requests",
        json={"answers": answers(), "caller_note": "urgent money wire gift card personal info"},
    )
    assert res.get_json()["route"] == "single"
