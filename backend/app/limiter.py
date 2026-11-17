"""Rate limiting (Flask-Limiter, in memory).

Limits slow down guessing: passwords at login, and 6 digit codes when a
family member approves. Counting only failures (deduct_when) means normal
use is never blocked. In memory storage resets when the server restarts,
which is fine for this project; a real deployment would use a shared store.
"""
from flask import jsonify, request, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def user_or_ip() -> str:
    uid = session.get("user_id")
    return f"user:{uid}" if uid is not None else f"ip:{get_remote_address()}"


def email_key() -> str:
    data = request.get_json(silent=True) or {}
    email = data.get("email") if isinstance(data, dict) else None
    return f"email:{str(email or '').strip().lower()}"


limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")


def too_many(_err):
    # Imported here because audit.py needs the models, which need nothing
    # from this file, and keeping it local avoids a circular import.
    from .audit import log
    from .auth import current_user

    log("rate_limited", outcome="rejected", actor=current_user(), detail={"path": request.path})
    return jsonify({"error": "too many attempts. Wait a few minutes and try again."}), 429
