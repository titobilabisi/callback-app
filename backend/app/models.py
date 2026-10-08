import enum
from datetime import datetime, timedelta, timezone

from flask_sqlalchemy import SQLAlchemy

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

    enrolled_by = db.relationship("User", remote_side=[id])

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "enrolled_by_id": self.enrolled_by_id,
        }


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
