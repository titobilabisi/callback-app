"""TOTP (RFC 6238): the 6 digit code from an authenticator app.

Why it is here: a family member's password alone is not enough to approve
a call. Approving also needs a code from the phone they enrolled, so a
stolen or guessed password cannot approve anything by itself.

Rules enforced here, each with a test:
  * A code is 6 digits and valid for its 30 second window (plus one window
    either side for clock drift).
  * A code works once. The last accepted time step is stored, so a code
    that was already used (or an older one) is rejected: replay protection.
  * Only approving needs a code. Declining is the safe direction.
"""
import hmac
import time

import pyotp
from flask import Blueprint, current_app, jsonify, request

from .auth import require_role
from .limiter import limiter
from .models import Role, db

STEP_SECONDS = 30
ISSUER = "CallBack"

totp_bp = Blueprint("totp", __name__, url_prefix="/api")


def new_secret() -> str:
    return pyotp.random_base32()


def now() -> float:
    """The clock the TOTP checks use. Tests replace it with a fake clock."""
    clock = current_app.config.get("TOTP_NOW")
    return clock() if clock else time.time()


def provisioning_uri(user) -> str:
    return pyotp.TOTP(user.totp_secret, interval=STEP_SECONDS).provisioning_uri(
        name=user.email, issuer_name=ISSUER
    )


def verify_and_consume(user, code, at=None) -> bool:
    """True only for a correct code that has not been used before.
    On success the time step is recorded on the user (the caller commits).
    """
    if not user.totp_secret or not isinstance(code, str):
        return False
    code = code.replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return False

    totp = pyotp.TOTP(user.totp_secret, interval=STEP_SECONDS)
    current_step = int((now() if at is None else at) // STEP_SECONDS)
    for step in (current_step - 1, current_step, current_step + 1):
        if hmac.compare_digest(totp.at(step * STEP_SECONDS), code):
            if user.totp_last_step is not None and step <= user.totp_last_step:
                return False  # replay: this code, or an older one, was already used
            user.totp_last_step = step
            return True
    return False


@totp_bp.get("/verifier/totp")
@require_role(Role.VERIFIER)
def totp_setup(verifier):
    """What the family member needs to add CallBack to their authenticator
    app. The secret is only shown until setup is confirmed.
    """
    if verifier.totp_confirmed:
        return jsonify({"confirmed": True})
    if not verifier.totp_secret:
        verifier.totp_secret = new_secret()
        db.session.commit()
    return jsonify({"confirmed": False, "secret": verifier.totp_secret, "uri": provisioning_uri(verifier)})


def _failed_code(response):
    return response.status_code == 401


@totp_bp.post("/verifier/totp/confirm")
@limiter.limit("5 per 15 minutes", deduct_when=_failed_code)
@require_role(Role.VERIFIER)
def totp_confirm(verifier):
    """Setup is complete once they type a valid code from their app."""
    if verifier.totp_confirmed:
        return jsonify({"error": "already set up"}), 409
    data = request.get_json(silent=True) or {}
    if not verify_and_consume(verifier, data.get("code")):
        return jsonify({"error": "that code is not right. Check the app and try the newest code."}), 401
    verifier.totp_confirmed = True
    db.session.commit()
    return jsonify({"confirmed": True})
