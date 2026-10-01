"""Password hashing and invite token helpers, kept separate from the
request handlers so they are easy to test on their own.
"""
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(password_hash: str, plain_password: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def generate_invite_token() -> str:
    """A short, hard to guess token for one invite, used once then marked
    spent. 32 bytes of randomness, url safe so it can go in a link.
    """
    return secrets.token_urlsafe(32)
