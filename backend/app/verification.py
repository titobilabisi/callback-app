"""Chunk 2 and Chunk 3 endpoints: risk routing, verification requests, and
verifier approve / decline.

The rules this file enforces, each of which has a test:

  * The route (single or two-person) is computed here from the six risk
    answers. A route sent by the client is ignored.
  * Only a logged in elder can open a request, and only the elder who
    opened it can read it.
  * Only a verifier enrolled under that elder can respond.
  * A high-risk request needs approvals from two DISTINCT verifiers. The
    same verifier answering twice is rejected.
  * Any decline ends the request as Denied.
  * A request that nobody finished in time becomes Unable to Verify. It
    can never be approved after it expires, and a finished request can
    never be changed.
"""
from datetime import timedelta

from flask import Blueprint, current_app, jsonify
from sqlalchemy.exc import IntegrityError

from . import totp
from .audit import log
from .auth import require_role
from .inputs import json_body
from .limiter import limiter, user_or_ip
from .models import (
    Decision,
    RequestStatus,
    Role,
    User,
    VerificationRequest,
    VerificationResponse,
    _utcnow,
    db,
)
from .risk import RISK_FACTORS, TWO_PERSON, InvalidAnswers, assess

verification_bp = Blueprint("verification", __name__, url_prefix="/api")

DEFAULT_REQUEST_TTL_SECONDS = 300
MAX_NOTE_LENGTH = 140


def _clean_note(value):
    """The optional caller note. Returns (note, error). Must be a string,
    is trimmed, and is limited in length. An empty note means no note.
    """
    if value is None:
        return None, None
    if not isinstance(value, str):
        return None, "caller_note must be text"
    note = " ".join(value.split())
    if len(note) > MAX_NOTE_LENGTH:
        return None, f"caller_note must be {MAX_NOTE_LENGTH} characters or fewer"
    return (note or None), None


def _enrolled_verifiers(elder: User):
    return User.query.filter_by(enrolled_by_id=elder.id, role=Role.VERIFIER).all()


@verification_bp.get("/risk/questions")
def risk_questions():
    """The questions, in order. The app reads them from here so the wording
    lives in exactly one place (risk.py).
    """
    return jsonify(RISK_FACTORS)


@verification_bp.post("/requests")
@require_role(Role.ELDER)
def create_request(elder):
    """An elder submits their six answers. The server decides the route."""
    data = json_body()

    try:
        assessment = assess(data.get("answers"))
    except InvalidAnswers as err:
        log("request_rejected", outcome="rejected", actor=elder, detail={"reason": "invalid_answers"})
        return jsonify({"error": str(err)}), 400

    note, note_error = _clean_note(data.get("caller_note"))
    if note_error:
        log("request_rejected", outcome="rejected", actor=elder, detail={"reason": "invalid_note"})
        return jsonify({"error": note_error}), 400

    verifiers = _enrolled_verifiers(elder)
    if not verifiers:
        log("request_rejected", outcome="rejected", actor=elder, detail={"reason": "no_family_enrolled"})
        return jsonify({"error": "no family members are enrolled yet, so nobody can check this call"}), 409

    ttl = current_app.config.get("REQUEST_TTL_SECONDS", DEFAULT_REQUEST_TTL_SECONDS)
    req = VerificationRequest(
        elder_id=elder.id,
        answers=assessment.answers,
        route=assessment.route,
        required_approvals=assessment.required_approvals,
        caller_note=note,
        expires_at=_utcnow() + timedelta(seconds=ttl),
    )
    db.session.add(req)
    db.session.flush()
    log(
        "request_created",
        actor=elder,
        request_id=req.id,
        commit=False,
        detail={"route": req.route, "required_approvals": req.required_approvals, "enrolled_verifiers": len(verifiers)},
    )
    db.session.commit()

    body = req.to_dict()
    body["enrolled_verifiers"] = len(verifiers)
    # A two-person request with fewer than two enrolled family members is
    # still created, never quietly downgraded to one approval. It will end
    # as Unable to Verify unless a second person is enrolled in time, and
    # the app can tell the elder that.
    body["can_be_completed"] = len(verifiers) >= req.required_approvals
    return jsonify(body), 201


@verification_bp.get("/requests/<int:request_id>")
@require_role(Role.ELDER)
def get_request(elder, request_id):
    """The elder polls this to see the result."""
    req = db.session.get(VerificationRequest, request_id)
    if req is None or req.elder_id != elder.id:
        return jsonify({"error": "request not found"}), 404

    req.settle_if_expired()
    db.session.commit()
    return jsonify(req.to_dict())


@verification_bp.get("/verifier/requests")
@require_role(Role.VERIFIER)
def verifier_inbox(verifier):
    """Open requests from the elder this verifier is enrolled under that
    this verifier has not answered yet.
    """
    pending = (
        VerificationRequest.query.filter_by(
            elder_id=verifier.enrolled_by_id, status=RequestStatus.PENDING
        )
        .order_by(VerificationRequest.created_at)
        .all()
    )

    inbox = []
    for req in pending:
        req.settle_if_expired()
        if not req.is_open:
            continue
        if any(r.verifier_id == verifier.id for r in req.responses):
            continue
        item = req.to_dict()
        item["elder_name"] = req.elder.name
        item["summary"] = [
            {"key": f["key"], "label": f["short_text"], "value": req.answers[f["key"]]}
            for f in RISK_FACTORS
        ]
        inbox.append(item)
    db.session.commit()
    return jsonify(inbox)


def _wrong_code(response):
    return response.status_code == 401


@verification_bp.post("/requests/<int:request_id>/respond")
@limiter.limit("5 per 15 minutes", key_func=user_or_ip, deduct_when=_wrong_code)
@require_role(Role.VERIFIER)
def respond(verifier, request_id):
    data = json_body()
    try:
        decision = Decision(data.get("decision"))
    except ValueError:
        log("response_rejected", outcome="rejected", actor=verifier, request_id=request_id, detail={"reason": "invalid_decision"})
        return jsonify({"error": "decision must be 'approve' or 'decline'"}), 400

    req = db.session.get(VerificationRequest, request_id)
    if req is None:
        log("response_rejected", outcome="rejected", actor=verifier, request_id=request_id, detail={"reason": "request_not_found"})
        return jsonify({"error": "request not found"}), 404

    # Checked on every response, not just at login.
    if verifier.enrolled_by_id != req.elder_id:
        log("response_rejected", outcome="rejected", actor=verifier, elder_id=req.elder_id, request_id=req.id, detail={"reason": "not_enrolled_for_this_person"})
        return jsonify({"error": "you are not enrolled as a verifier for this person"}), 403

    req.settle_if_expired()
    if req.status == RequestStatus.UNABLE_TO_VERIFY:
        log("response_rejected", outcome="rejected", actor=verifier, elder_id=req.elder_id, request_id=req.id, detail={"reason": "expired"}, commit=False)
        db.session.commit()
        return jsonify({"error": "this request has expired"}), 410
    if req.status != RequestStatus.PENDING:
        log("response_rejected", outcome="rejected", actor=verifier, elder_id=req.elder_id, request_id=req.id, detail={"reason": "already_finished", "status": req.status.value})
        return jsonify({"error": f"this request is already {req.status.value}"}), 409

    if any(r.verifier_id == verifier.id for r in req.responses):
        log("response_rejected", outcome="rejected", actor=verifier, elder_id=req.elder_id, request_id=req.id, detail={"reason": "duplicate_response"})
        return jsonify({"error": "you already responded to this request"}), 409

    # Declining is the safe direction, so it needs nothing extra. Approving
    # needs a valid, unused code from the family member's authenticator app.
    if decision == Decision.APPROVE:
        if not verifier.totp_confirmed:
            log("response_rejected", outcome="rejected", actor=verifier, elder_id=req.elder_id, request_id=req.id, detail={"reason": "authenticator_not_set_up"})
            return jsonify({"error": "set up your authenticator app before approving", "code": "totp_setup_required"}), 403
        if not totp.verify_and_consume(verifier, data.get("code")):
            log("response_rejected", outcome="rejected", actor=verifier, elder_id=req.elder_id, request_id=req.id, detail={"reason": "bad_or_reused_code"})
            return jsonify({"error": "that code is not right or was already used. Wait for a new code and try again."}), 401

    db.session.add(VerificationResponse(request_id=req.id, verifier_id=verifier.id, decision=decision))
    try:
        db.session.flush()
    except IntegrityError:
        # Backstop for the unique constraint if two submissions race.
        db.session.rollback()
        log("response_rejected", outcome="rejected", actor=verifier, elder_id=req.elder_id, request_id=req.id, detail={"reason": "duplicate_response"})
        return jsonify({"error": "you already responded to this request"}), 409

    db.session.refresh(req)
    log(
        "response_approved" if decision == Decision.APPROVE else "response_declined",
        actor=verifier,
        elder_id=req.elder_id,
        request_id=req.id,
        commit=False,
    )
    if decision == Decision.DECLINE:
        req.status = RequestStatus.DENIED
        req.resolved_at = _utcnow()
    elif req.approvals >= req.required_approvals:
        req.status = RequestStatus.VERIFIED
        req.resolved_at = _utcnow()
    if req.status != RequestStatus.PENDING:
        log(
            "request_resolved",
            actor=verifier,
            elder_id=req.elder_id,
            request_id=req.id,
            commit=False,
            detail={"status": req.status.value, "approvals": req.approvals},
        )

    db.session.commit()
    return jsonify(req.to_dict())
