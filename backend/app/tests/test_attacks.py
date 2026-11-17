"""Runs the whole attack suite (backend/attacks) as part of the tests. Any
attack that works when it should not, crashes the server, or is stopped
without leaving the expected audit event fails the test. Known limits
(reported as GAP) are written up in attacks/report.md and do not fail it.
"""
import pytest

from attacks import bypass, compromise  # noqa: F401  (importing registers the attacks)
from attacks.harness import ATTACKS
from attacks.run_all import run_one


@pytest.mark.parametrize("a", sorted(ATTACKS, key=lambda a: a["id"]), ids=lambda a: a["id"])
def test_attack_is_stopped(a):
    out = run_one(a)
    assert out["status"] in ("DEFENDED", "GAP"), f"{a['id']} {a['title']}: {out['status']} {out['note']}"
