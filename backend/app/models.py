import enum
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

from .security import generate_invite_token

db = SQLAlchemy()


def _utcnow() -> datetime:
    """Naive UTC datetime, matching how SQLite stores DateTime columns here."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(str, enum.Enum):
    ELDER = "elder"
    VERIFIER = "verifier"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(Role), nullable=False)

    # Only set for a verifier account, and only ever set once, at creation,
    # from the invite they redeemed. A verifier is always tied to exactly
    # one elder and that link cannot be changed after the fact.
    enrolled_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    # TOTP (verifiers only). The secret is never returned by any endpoint
    # except the one-time setup screen. totp_last_step is the newest time
    # step already accepted, which is what blocks a replayed code.
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    totp_last_step = db.Column(db.Integer, nullable=True)

    enrolled_by = db.relationship("User", remote_side=[id])

    def to_dict(self):
        body = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "enrolled_by_id": self.enrolled_by_id,
        }
        if self.role == Role.VERIFIER:
            body["totp_confirmed"] = self.totp_confirmed
        return body


class Invite(db.Model):
    """An invite is the only way a verifier account can ever be created.
    There is no open verifier sign up: this is what makes enrollment
    invite only, tied to a specific elder's account.
    """

    __tablename__ = "invites"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    verifier_name_hint = db.Column(db.String(120), nullable=True)

    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    used_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    used_by = db.relationship("User", foreign_keys=[used_by_id])

    @staticmethod
    def new_for(elder: "User", verifier_name_hint: str | None = None, ttl_hours: int = 72) -> "Invite":
        return Invite(
            token=generate_invite_token(),
            created_by_id=elder.id,
            verifier_name_hint=verifier_name_hint,
            expires_at=_utcnow() + timedelta(hours=ttl_hours),
        )

    @property
    def is_expired(self) -> bool:
        return _utcnow() > self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and not self.is_used

    def to_dict(self):
        return {
            "id": self.id,
            "token": self.token,
            "created_by_id": self.created_by_id,
            "verifier_name_hint": self.verifier_name_hint,
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired,
            "is_used": self.is_used,
        }


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    DENIED = "denied"
    # The safe default. A request nobody answered in time ends here. The
    # system never silently turns non-response into approval.
    UNABLE_TO_VERIFY = "unable_to_verify"


class Decision(str, enum.Enum):
    APPROVE = "approve"
    DECLINE = "decline"


class VerificationRequest(db.Model):
    """One "I got a call, help me check" from an elder.

    The route and the number of approvals required are computed on the
    server from the risk answers (see risk.py) and stored here. They are
    never taken from the client.
    """

    __tablename__ = "verification_requests"

    id = db.Column(db.Integer, primary_key=True)
    elder_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # The six yes/no risk answers. All six are kept, including the ones
    # that do not change the route, so they are available to the audit
    # trail and to the verifier's call summary.
    answers = db.Column(db.JSON, nullable=False)
    route = db.Column(db.String(20), nullable=False)
    required_approvals = db.Column(db.Integer, nullable=False)

    # Optional short note from the elder about who the caller said they
    # were ("says he is from my insurance"). Shown to verifiers as plain
    # text. It never affects the route or the result.
    caller_note = db.Column(db.String(140), nullable=True)

    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    elder = db.relationship("User", foreign_keys=[elder_id])
    responses = db.relationship(
        "VerificationResponse", backref="request", order_by="VerificationResponse.created_at"
    )

    @property
    def is_expired(self) -> bool:
        return _utcnow() > self.expires_at

    @property
    def is_open(self) -> bool:
        """Still waiting on verifiers and still inside its time window."""
        return self.status == RequestStatus.PENDING and not self.is_expired

    def settle_if_expired(self) -> None:
        """Move a pending request that ran out of time to Unable to Verify.
        Called on every read and every response attempt, so an expired
        request can never be approved late, whether or not anything ever
        looked at it in between.
        """
        if self.status == RequestStatus.PENDING and self.is_expired:
            self.status = RequestStatus.UNABLE_TO_VERIFY
            self.resolved_at = self.expires_at
            AuditEvent.record(
                "request_resolved",
                elder_id=self.elder_id,
                request_id=self.id,
                detail={"status": "unable_to_verify", "reason": "timeout"},
            )

    @property
    def approvals(self) -> int:
        return sum(1 for r in self.responses if r.decision == Decision.APPROVE)

    def to_dict(self):
        seconds_left = 0
        if self.status == RequestStatus.PENDING:
            seconds_left = max(0, int((self.expires_at - _utcnow()).total_seconds()))
        return {
            "id": self.id,
            "status": self.status.value,
            "route": self.route,
            "required_approvals": self.required_approvals,
            "approvals": self.approvals,
            "caller_note": self.caller_note,
            "expires_at": self.expires_at.isoformat(),
            "seconds_left": seconds_left,
        }


class VerificationResponse(db.Model):
    """One verifier's approve or decline on one request.

    The unique constraint is what enforces "two distinct verifiers" at the
    database level: the same verifier cannot answer the same request twice,
    so one compromised verifier account cannot satisfy a two-person
    request by itself.
    """

    __tablename__ = "verification_responses"
    __table_args__ = (db.UniqueConstraint("request_id", "verifier_id", name="one_response_per_verifier"),)

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("verification_requests.id"), nullable=False)
    verifier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    decision = db.Column(db.Enum(Decision), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow, nullable=False)

    verifier = db.relationship("User", foreign_keys=[verifier_id])


class AuditEvent(db.Model):
    """One line of the audit log. See audit.py for what is recorded.

    Append only: each event stores the hash of the one before it (prev_hash)
    and its own hash, so editing or removing an old row breaks the chain.
    Nothing here ever holds a password, code, token or secret.
    """

    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False)
    event_type = db.Column(db.String(40), nullable=False)
    outcome = db.Column(db.String(10), nullable=False)  # "ok" or "rejected"
    actor_id = db.Column(db.Integer, nullable=True)  # who did it, if known
    elder_id = db.Column(db.Integer, nullable=True, index=True)  # whose family it belongs to
    request_id = db.Column(db.Integer, nullable=True)
    ip = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.JSON, nullable=True)
    prev_hash = db.Column(db.String(64), nullable=False)
    hash = db.Column(db.String(64), nullable=False)

    GENESIS = "0" * 64

    @staticmethod
    def _digest(prev_hash, created_at, event_type, outcome, actor_id, elder_id, request_id, ip, detail):
        payload = json.dumps(
            [prev_hash, created_at.isoformat(), event_type, outcome, actor_id, elder_id, request_id, ip, detail],
            sort_keys=True,
            separators=(",", ":"),
        )
        # Keyed with the server's secret key, which is not stored in the
        # database. Someone who can only write to the database can change a
        # row but cannot recompute the hashes that follow it.
        key = current_app.config["SECRET_KEY"].encode()
        return hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()

    @classmethod
    def record(cls, event_type, *, outcome="ok", actor_id=None, elder_id=None, request_id=None, ip=None, detail=None):
        last = db.session.query(cls.hash).order_by(cls.id.desc()).first()
        prev_hash = last[0] if last else cls.GENESIS
        created_at = _utcnow()
        event = cls(
            created_at=created_at,
            event_type=event_type,
            outcome=outcome,
            actor_id=actor_id,
            elder_id=elder_id,
            request_id=request_id,
            ip=ip,
            detail=detail,
            prev_hash=prev_hash,
            hash=cls._digest(prev_hash, created_at, event_type, outcome, actor_id, elder_id, request_id, ip, detail),
        )
        db.session.add(event)
        return event

    @classmethod
    def verify_chain(cls):
        """(True, None) if every event matches its hash and links to the one
        before it. Otherwise (False, id of the first event that does not).
        """
        prev_hash = cls.GENESIS
        for e in cls.query.order_by(cls.id).all():
            expected = cls._digest(
                prev_hash, e.created_at, e.event_type, e.outcome, e.actor_id, e.elder_id, e.request_id, e.ip, e.detail
            )
            if e.prev_hash != prev_hash or e.hash != expected:
                return False, e.id
            prev_hash = e.hash
        return True, None

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "event_type": self.event_type,
            "outcome": self.outcome,
            "actor_id": self.actor_id,
            "request_id": self.request_id,
            "ip": self.ip,
            "detail": self.detail,
        }


@event.listens_for(AuditEvent, "before_update")
@event.listens_for(AuditEvent, "before_delete")
def _audit_is_append_only(mapper, connection, target):
    raise RuntimeError("audit events cannot be changed or deleted")
