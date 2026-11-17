"""Phase 4: audit logging. Each test is one rule: the right events are
written (failures included), secrets never are, and the log cannot be
quietly edited.
"""
import json

import pytest
from sqlalchemy import text

from app.models import AuditEvent, User, db
from app.tests.helpers import PASSWORD, Family, login, new_client, register_elder
from app.tests.test_verification import expire


def events(app, event_type=None, **filters):
    with app.app_context():
        q = AuditEvent.query
        if event_type:
            q = q.filter_by(event_type=event_type)
        if filters:
            q = q.filter_by(**filters)
        return [e.to_dict() for e in q.order_by(AuditEvent.id).all()]


def types(app):
    return [e["event_type"] for e in events(app)]


# --- what gets written --------------------------------------------------------

def test_login_success_failure_and_logout_are_logged(app):
    register_elder(app.test_client())
    c = new_client(app)
    c.post("/api/login", json={"email": "grandma@example.com", "password": "wrong password"})
    c.post("/api/login", json={"email": "nobody@example.com", "password": "whatever123"})
    login(c, "grandma@example.com")
    c.post("/api/logout")

    failed = events(app, "login_failed")
    assert [e["detail"]["reason"] for e in failed] == ["wrong_password", "unknown_email"]
    assert all(e["outcome"] == "rejected" for e in failed)
    assert failed[0]["actor_id"] is not None and failed[1]["actor_id"] is None
    assert len(events(app, "login_success")) == 1
    assert len(events(app, "logout")) == 1


def test_a_full_approved_two_person_check_leaves_a_complete_trail(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)
    assert family.respond(0, req["id"], "approve").status_code == 200
    assert family.respond(1, req["id"], "approve").status_code == 200

    trail = [(e["event_type"], e["outcome"]) for e in events(app, request_id=req["id"])]
    assert trail == [
        ("request_created", "ok"),
        ("response_approved", "ok"),
        ("response_approved", "ok"),
        ("request_resolved", "ok"),
    ]
    created = events(app, "request_created")[0]
    assert created["detail"]["required_approvals"] == 2
    assert events(app, "request_resolved")[0]["detail"]["status"] == "verified"


def test_a_decline_is_logged_and_resolves_as_denied(app):
    family = Family(app, verifiers=2)
    req = family.open_request()
    family.respond(0, req["id"], "decline")
    assert len(events(app, "response_declined")) == 1
    assert events(app, "request_resolved")[0]["detail"]["status"] == "denied"


def test_enrollment_steps_are_logged(app):
    Family(app, verifiers=1)
    seen = types(app)
    for expected in ("elder_created", "invite_created", "verifier_enrolled", "totp_confirmed"):
        assert expected in seen


def test_bad_invites_are_logged_with_the_reason(app):
    family = Family(app, verifiers=1)
    with app.app_context():
        from app.models import Invite
        token = Invite.query.first().token
    res = new_client(app).post(
        "/api/verifiers",
        json={"invite_token": token, "name": "X", "email": "x@example.com", "password": PASSWORD},
    )
    assert res.status_code == 410
    new_client(app).post(
        "/api/verifiers",
        json={"invite_token": "nope", "name": "X", "email": "x@example.com", "password": PASSWORD},
    )
    reasons = [e["detail"]["reason"] for e in events(app, "invite_rejected")]
    assert reasons == ["already_used", "not_found"]


def test_every_kind_of_refused_response_is_logged(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)  # two-person, so one approval leaves it open

    assert family.respond(0, req["id"], "approve", code="000000").status_code == 401  # bad code
    ok = family.respond(0, req["id"], "approve")
    assert ok.status_code == 200
    assert family.respond(0, req["id"], "approve").status_code == 409  # same person again

    late = family.open_request()
    expire(app, late["id"])
    assert family.respond(1, late["id"], "approve").status_code == 410  # expired

    reasons = [e["detail"]["reason"] for e in events(app, "response_rejected")]
    assert reasons == ["bad_or_reused_code", "duplicate_response", "expired"]
    # The timeout itself is logged as a system event.
    timeouts = [e for e in events(app, "request_resolved") if e["detail"].get("reason") == "timeout"]
    assert len(timeouts) == 1 and timeouts[0]["actor_id"] is None


def test_a_replayed_code_is_logged_as_rejected(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)
    # Capture one valid code, use it, then try to reuse it on another request.
    from app.tests.helpers import next_code
    code = next_code(app, family.verifiers[0]["email"])
    first = family.verifier_clients[0].post(f"/api/requests/{req['id']}/respond", json={"decision": "approve", "code": code})
    assert first.status_code == 200
    other = family.open_request(money=True)
    replay = family.verifier_clients[0].post(f"/api/requests/{other['id']}/respond", json={"decision": "approve", "code": code})
    assert replay.status_code == 401
    assert events(app, "response_rejected")[-1]["detail"]["reason"] == "bad_or_reused_code"


def test_refused_access_is_logged(app):
    family = Family(app, verifiers=1)
    # Not logged in.
    new_client(app).get("/api/audit")
    # A family member trying an elder only action.
    assert family.verifier_clients[0].post("/api/requests", json={"answers": {}}).status_code == 403
    denied = events(app, "access_denied")
    assert [e["detail"]["reason"] for e in denied] == ["not_logged_in", "wrong_role"]


def test_rate_limit_hits_are_logged(limited_app):
    app = limited_app
    register_elder(app.test_client())
    c = new_client(app)
    for _ in range(6):
        c.post("/api/login", json={"email": "grandma@example.com", "password": "wrong password"})
    assert any(e["detail"]["path"] == "/api/login" for e in events(app, "rate_limited"))


# --- what must never be written ----------------------------------------------

def test_no_secret_ever_appears_in_the_log(app):
    family = Family(app, verifiers=2)
    req = family.open_request(money=True)
    family.respond(0, req["id"], "approve", code="123456")
    family.respond(0, req["id"], "approve")
    new_client(app).post("/api/login", json={"email": "grandma@example.com", "password": "hunter2hunter2"})

    with app.app_context():
        secrets = [PASSWORD, "hunter2hunter2", "123456"]
        secrets += [u.totp_secret for u in User.query.all() if u.totp_secret]
        secrets += [u.password_hash for u in User.query.all()]
        from app.models import Invite
        secrets += [i.token for i in Invite.query.all()]
        dump = json.dumps([e.to_dict() for e in AuditEvent.query.all()])
    for secret in secrets:
        assert secret not in dump


# --- tamper evidence ----------------------------------------------------------

def test_events_cannot_be_updated_or_deleted_through_the_app(app):
    Family(app, verifiers=1)
    with app.app_context():
        e = AuditEvent.query.first()
        e.event_type = "nothing_happened"
        with pytest.raises(RuntimeError):
            db.session.commit()
        db.session.rollback()
        db.session.delete(AuditEvent.query.first())
        with pytest.raises(RuntimeError):
            db.session.commit()
        db.session.rollback()


def test_an_untouched_log_verifies(app):
    family = Family(app, verifiers=2)
    family.open_request()
    with app.app_context():
        assert AuditEvent.verify_chain() == (True, None)
    res = family.elder_client.get("/api/audit/verify")
    assert res.get_json() == {"intact": True, "first_bad_id": None}


def test_editing_a_row_directly_in_the_database_is_detected(app):
    family = Family(app, verifiers=2)
    req = family.open_request()
    family.respond(0, req["id"], "decline")
    with app.app_context():
        target = AuditEvent.query.filter_by(event_type="response_declined").one().id
        db.session.execute(text("UPDATE audit_events SET event_type='response_approved' WHERE id=:i"), {"i": target})
        db.session.commit()
        assert AuditEvent.verify_chain() == (False, target)
    assert family.elder_client.get("/api/audit/verify").get_json()["intact"] is False


def test_deleting_a_row_directly_in_the_database_is_detected(app):
    family = Family(app, verifiers=2)
    family.open_request()
    with app.app_context():
        middle = AuditEvent.query.order_by(AuditEvent.id).all()[3].id
        db.session.execute(text("DELETE FROM audit_events WHERE id=:i"), {"i": middle})
        db.session.commit()
        intact, bad = AuditEvent.verify_chain()
        assert intact is False and bad == middle + 1


# --- who can read it ----------------------------------------------------------

def test_an_elder_sees_only_their_own_familys_events(app):
    family = Family(app, verifiers=2)
    family.open_request()

    other = new_client(app)
    other.post("/api/elders", json={"name": "Other", "email": "other@example.com", "password": PASSWORD})
    login(other, "other@example.com")

    mine = family.elder_client.get("/api/audit").get_json()
    theirs = other.get("/api/audit").get_json()
    assert any(e["event_type"] == "request_created" for e in mine)
    assert all(e["event_type"] != "request_created" for e in theirs)
    assert [e["id"] for e in mine] == sorted([e["id"] for e in mine], reverse=True)


def test_a_family_member_cannot_read_the_log(app):
    family = Family(app, verifiers=1)
    assert family.verifier_clients[0].get("/api/audit").status_code == 403
    assert new_client(app).get("/api/audit").status_code == 401


def test_events_include_the_name_of_who_did_it(app):
    family = Family(app, verifiers=2)
    req = family.open_request()
    family.respond(0, req["id"], "approve")
    body = family.elder_client.get("/api/audit").get_json()
    approved = [e for e in body if e["event_type"] == "response_approved"][0]
    assert approved["actor_name"] == "Verifier 0"
    created = [e for e in body if e["event_type"] == "request_created"][0]
    assert created["actor_name"] == "Grandma"
