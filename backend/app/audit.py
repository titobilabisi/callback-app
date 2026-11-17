"""Audit logging: a record of every security relevant thing that happens.

What gets recorded (the event_type column):

  accounts     elder_created, verifier_enrolled, invite_created, invite_rejected
  sessions     login_success, login_failed, logout, access_denied, rate_limited
  approvals    totp_confirmed, totp_confirm_failed
  requests     request_created, request_rejected, response_approved,
               response_declined, response_rejected, request_resolved

Rules, each with a test:
  * Rejected and failed attempts are logged as well as successes, because
    those are what an investigation looks for.
  * Passwords, codes, invite tokens and secrets are never written to the log.
  * The log is append only. Updating or deleting an event through the app is
    blocked, and every event carries a hash of the one before it, so a row
    changed or removed straight in the database is caught by verify_chain().
"""
from flask import request

from .models import AuditEvent, Role, db


def log(event_type, *, outcome="ok", actor=None, elder_id=None, request_id=None, detail=None, commit=True):
    """Add one event. Pass commit=False when the caller commits its own
    change in the same step, so the event and the change succeed or fail
    together. Failed attempts use the default so they are saved even though
    nothing else changed.
    """
    actor_id = actor.id if actor is not None else None
    if elder_id is None and actor is not None:
        elder_id = actor.id if actor.role == Role.ELDER else actor.enrolled_by_id
    AuditEvent.record(
        event_type,
        outcome=outcome,
        actor_id=actor_id,
        elder_id=elder_id,
        request_id=request_id,
        ip=request.remote_addr,
        detail=detail,
    )
    if commit:
        db.session.commit()
