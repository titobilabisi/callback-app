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

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from .auth import require_role
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
    data = request.get_json(silent=True) or {}

    try:
        assessment = assess(data.get("answers"))
    except InvalidAnswers as err:
        return jsonify({"error": str(err)}), 400

    note, note_error = _clean_note(data.get("caller_note"))
    if note_error:
        return jsonify({"error": note_error}), 400

    verifiers = _enrolled_verifiers(elder)
    if not verifiers:
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


@verification_bp.post("/requests/<int:request_id>/respond")
@require_role(Role.VERIFIER)
def respond(verifier, request_id):
    data = request.get_json(silent=True) or {}
    try:
        decision = Decision(data.get("decision"))
    except ValueError:
        return jsonify({"error": "decision must be 'approve' or 'decline'"}), 400

    req = db.session.get(VerificationRequest, request_id)
    if req is None:
        return jsonify({"error": "request not found"}), 404

    # Checked on every response, not just at login.
    if verifier.enrolled_by_id != req.elder_id:
        return jsonify({"error": "you are not enrolled as a verifier for this person"}), 403

    req.settle_if_expired()
    if req.status == RequestStatus.UNABLE_TO_VERIFY:
        db.session.commit()
        return jsonify({"error": "this request has expired"}), 410
    if req.status != RequestStatus.PENDING:
        return jsonify({"error": f"this request is already {req.status.value}"}), 409

    if any(r.verifier_id == verifier.id for r in req.responses):
        return jsonify({"error": "you already responded to this request"}), 409

    db.session.add(VerificationResponse(request_id=req.id, verifier_id=verifier.id, decision=decision))
    try:
        db.session.flush()
    except IntegrityError:
        # Backstop for the unique constraint if two submissions race.
        db.session.rollback()
        return jsonify({"error": "you already responded to this request"}), 409

    db.session.refresh(req)
    if decision == Decision.DECLINE:
        req.status = RequestStatus.DENIED
        req.resolved_at = _utcnow()
    elif req.approvals >= req.required_approvals:
        req.status = RequestStatus.VERIFIED
        req.resolved_at = _utcnow()

    db.session.commit()
    return jsonify(req.to_dict())
