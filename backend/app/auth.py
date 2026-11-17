"""Login, logout, and the role checks the verification endpoints rely on.

Sessions use Flask's signed, HttpOnly cookie. The role of the logged in
user is always read from the database on each request, never from
anything the client sends, so the server-side authorization check the
threat model asks for happens on every verifier and elder action, not
just at login.

Login is rate limited (see limiter.py). Logins, failures and refused
access are written to the audit log (see audit.py).
"""
from functools import wraps

from flask import Blueprint, jsonify, request, session

from .audit import log
from .inputs import json_body, text
from .limiter import email_key, limiter
from .models import Role, User, db
from .security import hash_password, verify_password

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

# Verified against when the email is unknown, so a wrong email and a wrong
# password take about the same time and give the same answer.
_DUMMY_HASH = hash_password("not-a-real-account-password")


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def require_role(role: Role):
    """Decorator: the caller must be logged in with exactly this role."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if user is None:
                log("access_denied", outcome="rejected", detail={"path": request.path, "reason": "not_logged_in"})
                return jsonify({"error": "not logged in"}), 401
            if user.role != role:
                log(
                    "access_denied",
                    outcome="rejected",
                    actor=user,
                    detail={"path": request.path, "reason": "wrong_role", "needs": role.value},
                )
                return jsonify({"error": "this action is not available for your account type"}), 403
            return view(user, *args, **kwargs)

        return wrapped

    return decorator


def _failed_login(response):
    return response.status_code == 401


@auth_bp.post("/login")
@limiter.limit("30 per minute")
@limiter.limit("5 per 15 minutes", key_func=email_key, deduct_when=_failed_login)
def login():
    data = json_body()
    email = text(data.get("email")).strip().lower()
    password = text(data.get("password"))

    user = User.query.filter_by(email=email).first()
    if user is None:
        verify_password(_DUMMY_HASH, password)
        log("login_failed", outcome="rejected", detail={"reason": "unknown_email", "email": email[:120]})
        return jsonify({"error": "wrong email or password"}), 401
    if not verify_password(user.password_hash, password):
        log("login_failed", outcome="rejected", actor=user, detail={"reason": "wrong_password"})
        return jsonify({"error": "wrong email or password"}), 401

    session.clear()
    session["user_id"] = user.id
    log("login_success", actor=user)
    return jsonify(user.to_dict())


@auth_bp.post("/logout")
def logout():
    user = current_user()
    if user is not None:
        log("logout", actor=user)
    session.clear()
    return jsonify({"ok": True})


@auth_bp.get("/me")
def me():
    user = current_user()
    if user is None:
        return jsonify({"error": "not logged in"}), 401
    return jsonify(user.to_dict())
