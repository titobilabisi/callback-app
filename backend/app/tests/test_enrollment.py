"""Tests for Chunk 1: invite only enrollment.

The property under test throughout this file is the one the whole
project proposal rests on: a verifier account can only come into
existence by redeeming a valid invite that an elder actively created.
There is no other door in.
"""
from datetime import datetime, timedelta, timezone

from app.models import Invite, User, db


def make_elder(client, email="grandma@example.com"):
    res = client.post(
        "/api/elders",
        json={"name": "Grandma", "email": email, "password": "correct horse battery"},
    )
    assert res.status_code == 201
    return res.get_json()


def make_invite(client, elder_id, verifier_name_hint=None):
    res = client.post(
        f"/api/elders/{elder_id}/invites",
        json={"verifier_name_hint": verifier_name_hint},
    )
    assert res.status_code == 201
    return res.get_json()


def test_elder_can_self_register(client):
    elder = make_elder(client)
    assert elder["role"] == "elder"
    assert elder["enrolled_by_id"] is None


def test_elder_email_must_be_unique(client):
    make_elder(client, email="dup@example.com")
    res = client.post(
        "/api/elders",
        json={"name": "Someone Else", "email": "dup@example.com", "password": "another password"},
    )
    assert res.status_code == 409


def test_verifier_cannot_be_created_without_a_token(client):
    res = client.post(
        "/api/verifiers",
        json={"name": "Aunt Jane", "email": "jane@example.com", "password": "a real password"},
    )
    assert res.status_code == 400


def test_verifier_cannot_be_created_with_an_unknown_token(client):
    res = client.post(
        "/api/verifiers",
        json={
            "invite_token": "this-token-was-never-issued",
            "name": "Aunt Jane",
            "email": "jane@example.com",
            "password": "a real password",
        },
    )
    assert res.status_code == 404


def test_valid_invite_creates_a_verifier_linked_to_the_right_elder(client):
    elder = make_elder(client)
    invite = make_invite(client, elder["id"], verifier_name_hint="Aunt Jane")

    res = client.post(
        "/api/verifiers",
        json={
            "invite_token": invite["token"],
            "name": "Aunt Jane",
            "email": "jane@example.com",
            "password": "a real password",
        },
    )
    assert res.status_code == 201
    verifier = res.get_json()
    assert verifier["role"] == "verifier"
    assert verifier["enrolled_by_id"] == elder["id"]


def test_an_invite_cannot_be_redeemed_twice(client):
    elder = make_elder(client)
    invite = make_invite(client, elder["id"])

    first = client.post(
        "/api/verifiers",
        json={
            "invite_token": invite["token"],
            "name": "Aunt Jane",
            "email": "jane@example.com",
            "password": "a real password",
        },
    )
    assert first.status_code == 201

    second = client.post(
        "/api/verifiers",
        json={
            "invite_token": invite["token"],
            "name": "A Different Person",
            "email": "different@example.com",
            "password": "a real password",
        },
    )
    assert second.status_code == 410


def test_an_expired_invite_is_rejected(client, app):
    elder = make_elder(client)
    invite = make_invite(client, elder["id"])

    # Force the invite into the past, the way real time passing would.
    with app.app_context():
        row = Invite.query.filter_by(token=invite["token"]).first()
        row.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        db.session.commit()

    res = client.post(
        "/api/verifiers",
        json={
            "invite_token": invite["token"],
            "name": "Aunt Jane",
            "email": "jane@example.com",
            "password": "a real password",
        },
    )
    assert res.status_code == 410


def test_invites_cannot_be_created_for_a_nonexistent_elder(client):
    res = client.post("/api/elders/999/invites", json={})
    assert res.status_code == 404


def test_verifier_list_does_not_leak_across_elders(client):
    elder_a = make_elder(client, email="elder-a@example.com")
    elder_b = make_elder(client, email="elder-b@example.com")

    invite_a = make_invite(client, elder_a["id"])
    invite_b = make_invite(client, elder_b["id"])

    client.post(
        "/api/verifiers",
        json={
            "invite_token": invite_a["token"],
            "name": "Verifier A",
            "email": "verifier-a@example.com",
            "password": "a real password",
        },
    )
    client.post(
        "/api/verifiers",
        json={
            "invite_token": invite_b["token"],
            "name": "Verifier B",
            "email": "verifier-b@example.com",
            "password": "a real password",
        },
    )

    res_a = client.get(f"/api/elders/{elder_a['id']}/verifiers")
    names_a = [v["name"] for v in res_a.get_json()]
    assert names_a == ["Verifier A"]

    res_b = client.get(f"/api/elders/{elder_b['id']}/verifiers")
    names_b = [v["name"] for v in res_b.get_json()]
    assert names_b == ["Verifier B"]
