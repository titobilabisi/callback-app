"""Enrollment: creating the first elder account, and inviting a verifier.

The core rule this file enforces: a verifier account can only ever be
created by redeeming a valid invite token, and that invite can only have
been issued by an existing elder account. There is no open sign up path
for a verifier. This is what the project proposal calls invite only
enrollment, and it is the thing that stops a scammer from talking an
elder into adding them as a trusted verifier through any route other
than the elder's own account actively creating that invite.
"""
from datetime import datetime, timezone

from flask import Blueprint, jsonify

from .audit import log
from .auth import require_role
from .inputs import json_body, text
from .models import Invite, Role, User, db
from .totp import new_secret
from .security import hash_password

enrollment_bp = Blueprint("enrollment", __name__, url_prefix="/api")


@enrollment_bp.post("/elders")
def create_elder():
    """Create the first account for an older adult. This is the only
    account type that can ever sign up on its own, with no invite needed.
    """
    data = json_body()
    name = text(data.get("name")).strip()
    email = text(data.get("email")).strip().lower()
    password = text(data.get("password"))

    if not name or not email or len(password) < 8:
        return jsonify({"error": "name, email, and a password of at least 8 characters are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "an account with that email already exists"}), 409

    elder = User(name=name, email=email, password_hash=hash_password(password), role=Role.ELDER)
    db.session.add(elder)
    db.session.flush()
    log("elder_created", actor=elder, commit=False)
    db.session.commit()

    return jsonify(elder.to_dict()), 201


@enrollment_bp.post("/elders/<int:elder_id>/invites")
@require_role(Role.ELDER)
def create_invite(elder, elder_id):
    """An elder creates an invite for one specific family member or
    caregiver. The invite is single use and expires, so it cannot be
    reused or sit open indefinitely.

    Only the logged in elder can do this, and only for their own family.
    Without this check anyone could mint an invite for any elder, join as
    a "family member", and approve a scam call.
    """
    if elder.id != elder_id:
        log("invite_rejected", outcome="rejected", actor=elder, detail={"reason": "not_your_family", "target_elder_id": elder_id})
        return jsonify({"error": "you can only invite people to your own family"}), 403

    data = json_body()
    verifier_name_hint = text(data.get("verifier_name_hint")).strip() or None

    invite = Invite.new_for(elder, verifier_name_hint=verifier_name_hint)
    db.session.add(invite)
    db.session.flush()
    log("invite_created", actor=elder, commit=False, detail={"invite_id": invite.id})
    db.session.commit()

    return jsonify(invite.to_dict()), 201


@enrollment_bp.post("/verifiers")
def accept_invite():
    """A verifier account is created only by redeeming a valid invite
    token. No invite, no account. An expired or already used token is
    rejected, not silently accepted.
    """
    data = json_body()
    token = text(data.get("invite_token"))
    name = text(data.get("name")).strip()
    email = text(data.get("email")).strip().lower()
    password = text(data.get("password"))

    if not token or not name or not email or len(password) < 8:
        return jsonify({"error": "invite_token, name, email, and a password of at least 8 characters are required"}), 400

    invite = Invite.query.filter_by(token=token).first()
    if invite is None:
        log("invite_rejected", outcome="rejected", detail={"reason": "not_found"})
        return jsonify({"error": "invite not found"}), 404
    if not invite.is_valid:
        reason = "expired" if invite.is_expired else "already used"
        log(
            "invite_rejected",
            outcome="rejected",
            elder_id=invite.created_by_id,
            detail={"reason": reason.replace(" ", "_"), "invite_id": invite.id},
        )
        return jsonify({"error": f"this invite is {reason}"}), 410

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "an account with that email already exists"}), 409

    verifier = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=Role.VERIFIER,
        enrolled_by_id=invite.created_by_id,
        totp_secret=new_secret(),
    )
    db.session.add(verifier)
    db.session.flush()  # gives verifier an id before the invite links to it

    invite.used_at = datetime.now(timezone.utc).replace(tzinfo=None)
    invite.used_by_id = verifier.id
    log("verifier_enrolled", actor=verifier, commit=False, detail={"invite_id": invite.id})
    db.session.commit()

    return jsonify(verifier.to_dict()), 201


@enrollment_bp.get("/elders/<int:elder_id>/verifiers")
@require_role(Role.ELDER)
def list_verifiers(elder, elder_id):
    """The family members or caregivers enrolled under this elder. An elder
    can only see their own list.
    """
    if elder.id != elder_id:
        return jsonify({"error": "you can only view your own family"}), 403

    verifiers = User.query.filter_by(enrolled_by_id=elder_id, role=Role.VERIFIER).all()
    return jsonify([v.to_dict() for v in verifiers])
