"""Tests for Chunk 2: risk scoring and routing.

Ground truth comes straight from the threat model: a request needs
two-person approval if money OR sensitive info is "yes", and single-person
approval otherwise, however many of the other four factors are "yes".

The full 2^6 = 64 combination matrix is run twice: once against the pure
routing function, and once through the real HTTP endpoint with a real
logged in elder, so the number the app actually uses is what is checked.
"""
from itertools import product

import pytest

from app.risk import FACTOR_KEYS, SINGLE, TWO_PERSON, InvalidAnswers, assess, validate_answers
from app.tests.helpers import Family, answers

ALL_COMBINATIONS = [dict(zip(FACTOR_KEYS, combo)) for combo in product([False, True], repeat=6)]


def expected_route(a):
    """The threat model's rule, written out independently of risk.py."""
    return TWO_PERSON if (a["money"] or a["sensitive_info"]) else SINGLE


def test_there_are_exactly_64_combinations():
    assert len(ALL_COMBINATIONS) == 64
    assert len({tuple(c.values()) for c in ALL_COMBINATIONS}) == 64


@pytest.mark.parametrize("combo", ALL_COMBINATIONS, ids=lambda c: "".join("1" if v else "0" for v in c.values()))
def test_routing_function_matches_threat_model_for_all_64(combo):
    result = assess(combo)
    assert result.route == expected_route(combo)
    assert result.required_approvals == (2 if expected_route(combo) == TWO_PERSON else 1)


def test_all_no_still_requires_verification():
    """Never skipped, never auto-approved."""
    result = assess(answers())
    assert result.route == SINGLE
    assert result.required_approvals == 1


@pytest.mark.parametrize("factor", ["money", "sensitive_info"])
def test_either_high_risk_factor_alone_forces_two_person(factor):
    assert assess(answers(**{factor: True})).route == TWO_PERSON


@pytest.mark.parametrize("factor", ["secrecy", "urgency", "unfamiliarity", "unusual_contact"])
def test_other_factors_alone_do_not_raise_the_route(factor):
    assert assess(answers(**{factor: True})).route == SINGLE


def test_all_four_low_risk_factors_together_still_single():
    result = assess(answers(secrecy=True, urgency=True, unfamiliarity=True, unusual_contact=True))
    assert result.route == SINGLE


def test_everything_yes_is_two_person():
    assert assess({k: True for k in FACTOR_KEYS}).route == TWO_PERSON


# ----- strict validation: the client is never trusted -----

def test_missing_answer_is_rejected():
    a = answers()
    del a["money"]
    with pytest.raises(InvalidAnswers):
        validate_answers(a)


def test_unknown_answer_is_rejected():
    with pytest.raises(InvalidAnswers):
        validate_answers({**answers(), "route": "single"})


@pytest.mark.parametrize("bad", ["false", "true", 0, 1, None, "", "no", [], {}])
def test_non_boolean_values_are_rejected_not_coerced(bad):
    """bool("false") is True in Python. A string must never be quietly
    turned into a yes or a no.
    """
    with pytest.raises(InvalidAnswers):
        validate_answers(answers(money=bad))


@pytest.mark.parametrize("bad", [None, [], "money", 5, True])
def test_answers_must_be_an_object(bad):
    with pytest.raises(InvalidAnswers):
        validate_answers(bad)


# ----- through the real endpoint -----

def test_questions_endpoint_serves_all_six_in_order(client):
    res = client.get("/api/risk/questions")
    assert res.status_code == 200
    assert [q["key"] for q in res.get_json()] == FACTOR_KEYS
    assert all(q["text"] and q["short_text"] for q in res.get_json())


def test_all_64_combinations_through_the_endpoint(app):
    family = Family(app, verifiers=2)
    wrong = []
    for combo in ALL_COMBINATIONS:
        res = family.elder_client.post("/api/requests", json={"answers": combo})
        assert res.status_code == 201
        body = res.get_json()
        if body["route"] != expected_route(combo):
            wrong.append(combo)
        assert body["required_approvals"] == (2 if expected_route(combo) == TWO_PERSON else 1)
    assert wrong == []


def test_client_cannot_choose_its_own_route(app):
    """The attack in the threat model: force a high-risk request down the
    single-approval path by sending the route (or approval count) along.
    """
    family = Family(app, verifiers=2)
    res = family.elder_client.post(
        "/api/requests",
        json={"answers": answers(money=True), "route": "single", "required_approvals": 1},
    )
    assert res.status_code == 201
    body = res.get_json()
    assert body["route"] == TWO_PERSON
    assert body["required_approvals"] == 2


def test_route_inside_answers_is_rejected(app):
    family = Family(app, verifiers=2)
    res = family.elder_client.post(
        "/api/requests", json={"answers": {**answers(money=True), "route": "single"}}
    )
    assert res.status_code == 400


def test_string_false_cannot_downgrade_a_money_request(app):
    """A tampered client sends "false" hoping it is read as no, or "true"
    hoping it is read as something else. Either way it is rejected.
    """
    family = Family(app, verifiers=2)
    res = family.elder_client.post("/api/requests", json={"answers": answers(money="false")})
    assert res.status_code == 400


def test_missing_answers_body_is_rejected(app):
    family = Family(app, verifiers=2)
    assert family.elder_client.post("/api/requests", json={}).status_code == 400
    assert family.elder_client.post("/api/requests", json={"answers": {"money": True}}).status_code == 400
