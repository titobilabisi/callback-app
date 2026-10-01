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
