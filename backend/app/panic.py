"""The panic alert: one tap from an older adult who feels pressured.

Rules, each with a test:
  * Only a logged in elder can raise it, and it goes only to the family
    members enrolled under that elder.
  * Raising it twice while one is still open does not create a second one,
    so the button cannot be used to flood the family.
  * A family member can only see and handle alerts for the elder they are
    enrolled under. Handling needs no authenticator code, because it only
    says "I am on it" and never approves anything.
  * Everything is written to the audit log.
"""
from flask import Blueprint, jsonify

from .audit import log
from .auth import require_role
from .limiter import limiter, user_or_ip
from .models import PanicAlert, Role, User, _utcnow, db

panic_bp = Blueprint("panic", __name__, url_prefix="/api")


@panic_bp.post("/panic")
@limiter.limit("10 per hour", key_func=user_or_ip)
@require_role(Role.ELDER)
def raise_alert(elder):
    notified = User.query.filter_by(enrolled_by_id=elder.id, role=Role.VERIFIER).count()
    open_alert = PanicAlert.query.filter_by(elder_id=elder.id, handled_at=None).first()
    if open_alert is not None:
        log("panic_repeated", actor=elder, detail={"alert_id": open_alert.id})
        return jsonify({**open_alert.to_dict(), "notified": notified}), 200

    alert = PanicAlert(elder_id=elder.id)
    db.session.add(alert)
    db.session.flush()
    log("panic_raised", actor=elder, commit=False, detail={"alert_id": alert.id, "notified": notified})
    db.session.commit()
    return jsonify({**alert.to_dict(), "notified": notified}), 201


@panic_bp.get("/verifier/alerts")
@require_role(Role.VERIFIER)
def open_alerts(verifier):
    alerts = (
        PanicAlert.query.filter_by(elder_id=verifier.enrolled_by_id, handled_at=None)
        .order_by(PanicAlert.created_at)
        .all()
    )
    return jsonify([a.to_dict() for a in alerts])


@panic_bp.post("/verifier/alerts/<int:alert_id>/handle")
@require_role(Role.VERIFIER)
def handle_alert(verifier, alert_id):
    alert = db.session.get(PanicAlert, alert_id)
    if alert is None or alert.elder_id != verifier.enrolled_by_id:
        log("panic_rejected", outcome="rejected", actor=verifier, detail={"reason": "not_found_or_not_yours"})
        return jsonify({"error": "alert not found"}), 404
    if alert.handled_at is not None:
        return jsonify(alert.to_dict()), 200
    alert.handled_at = _utcnow()
    alert.handled_by_id = verifier.id
    log("panic_handled", actor=verifier, commit=False, detail={"alert_id": alert.id})
    db.session.commit()
    return jsonify(alert.to_dict())
