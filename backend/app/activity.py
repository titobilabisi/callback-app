"""Read-only endpoints for the audit log. The log itself is written by
audit.py; this is only how an elder reads their family's activity.
"""
from flask import Blueprint, jsonify

from .auth import require_role
from .models import AuditEvent, Role, User

activity_bp = Blueprint("activity", __name__, url_prefix="/api")

MAX_EVENTS = 100


@activity_bp.get("/audit")
@require_role(Role.ELDER)
def list_events(elder):
    """An elder can read the activity log for their own family, newest first."""
    events = (
        AuditEvent.query.filter_by(elder_id=elder.id)
        .order_by(AuditEvent.id.desc())
        .limit(MAX_EVENTS)
        .all()
    )
    # Names for the people in this family, so the screen can say "Aunt Jane
    # approved" instead of a number. Only this elder's own family is looked up.
    family = User.query.filter((User.id == elder.id) | (User.enrolled_by_id == elder.id)).all()
    names = {u.id: u.name for u in family}
    body = []
    for e in events:
        item = e.to_dict()
        item["actor_name"] = names.get(e.actor_id)
        body.append(item)
    return jsonify(body)


@activity_bp.get("/audit/verify")
@require_role(Role.ELDER)
def verify_log(elder):
    """Re-checks the whole hash chain. Says whether the log is intact, not
    what is in it.
    """
    intact, first_bad_id = AuditEvent.verify_chain()
    return jsonify({"intact": intact, "first_bad_id": first_bad_id})
