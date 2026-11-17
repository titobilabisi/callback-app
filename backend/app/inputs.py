"""Safe reading of what a client sends. Anything can arrive in a request
body (a list where a name should be, a number where an email should be),
so every handler reads it through here and gets plain text or nothing,
never a crash.
"""
from flask import request


def json_body() -> dict:
    """The JSON object the client sent, or an empty one if it sent anything else."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text(value) -> str:
    """The value if it is a string, otherwise an empty string."""
    return value if isinstance(value, str) else ""
