"""Chunk 2: risk assessment and routing.

This is the single source of truth for the six risk factors, their exact
wording, and the routing rule from the threat model. It is deliberately a
plain module with no Flask or database imports, so the whole 2^6 = 64
combination matrix can be tested directly against it.

Routing rule (from the threat model, "Risk Factors & Routing Rule"):

  * Two-person approval is required if money is requested OR sensitive
    info is requested.
  * Otherwise single-person approval. Secrecy, urgency, unfamiliarity and
    unusual contact are recorded but do not by themselves raise the route.
  * Verification is never skipped: with every answer "no", the route is
    still single-person approval.

The client only ever sends answers. The route is always computed here, on
the server, and any route the client sends is ignored.
"""
from dataclasses import dataclass

SINGLE = "single"
TWO_PERSON = "two_person"

# Order matters: this is the order the questions are shown in the app.
RISK_FACTORS = [
    {
        "key": "money",
        "text": "Is the caller asking for money, gift cards, wire transfer, or payment of any kind?",
        "short_text": "Asking for money or payment",
    },
    {
        "key": "secrecy",
        "text": "Did the caller ask you not to tell anyone else in the family?",
        "short_text": "Asked to keep it secret",
    },
    {
        "key": "urgency",
        "text": "Did the caller say you must act immediately?",
        "short_text": "Said to act right now",
    },
    {
        "key": "sensitive_info",
        "text": "Did the caller ask for personal info like your SSN, bank login, or account numbers?",
        "short_text": "Asked for personal or account info",
    },
    {
        "key": "unfamiliarity",
        "text": "Did anything about the caller's voice, story, or details seem off or unfamiliar?",
        "short_text": "Something seemed off",
    },
    {
        "key": "unusual_contact",
        "text": "Did the call or text come from an unknown or unsaved number?",
        "short_text": "Unknown or unsaved number",
    },
]

FACTOR_KEYS = [f["key"] for f in RISK_FACTORS]

# The two factors that carry direct financial or identity harm.
HIGH_RISK_FACTORS = ("money", "sensitive_info")


class InvalidAnswers(ValueError):
    """Raised when the submitted answers are not exactly the six expected
    yes/no answers. Callers should treat this as a bad request.
    """


@dataclass(frozen=True)
class RiskAssessment:
    answers: dict
    route: str

    @property
    def required_approvals(self) -> int:
        return 2 if self.route == TWO_PERSON else 1


def validate_answers(answers) -> dict:
    """Return a clean {factor: bool} dict, or raise InvalidAnswers.

    Strict on purpose. Every factor must be present, and every value must
    be a real JSON boolean. Strings like "false" or numbers like 0 are
    rejected rather than coerced: in Python, bool("false") is True, which
    would let a tampered client flip an answer without meaning to.
    Unknown extra keys are rejected too, so nothing unreviewed is stored.
    """
    if not isinstance(answers, dict):
        raise InvalidAnswers("answers must be an object of yes/no values")

    missing = [k for k in FACTOR_KEYS if k not in answers]
    if missing:
        raise InvalidAnswers(f"missing answers: {', '.join(missing)}")

    extra = [k for k in answers if k not in FACTOR_KEYS]
    if extra:
        raise InvalidAnswers(f"unknown answers: {', '.join(sorted(extra))}")

    not_bool = [k for k in FACTOR_KEYS if not isinstance(answers[k], bool)]
    if not_bool:
        raise InvalidAnswers(f"answers must be true or false: {', '.join(not_bool)}")

    return {k: answers[k] for k in FACTOR_KEYS}


def assess(answers) -> RiskAssessment:
    """Validate the answers and compute the route on the server."""
    clean = validate_answers(answers)
    high_risk = any(clean[k] for k in HIGH_RISK_FACTORS)
    return RiskAssessment(answers=clean, route=TWO_PERSON if high_risk else SINGLE)
