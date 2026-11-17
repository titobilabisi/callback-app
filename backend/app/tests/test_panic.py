"""The panic alert: one tap from the elder, seen only by their own family."""
from app.tests.helpers import Family, new_client, register_elder
from app.tests.test_audit import events


def test_elder_raises_an_alert_and_family_sees_it(app):
    family = Family(app, verifiers=2)
    res = family.elder_client.post("/api/panic")
    assert res.status_code == 201
    assert res.get_json()["notified"] == 2
    for c in family.verifier_clients:
        alerts = c.get("/api/verifier/alerts").get_json()
        assert len(alerts) == 1 and alerts[0]["elder_name"] == "Grandma"


def test_pressing_twice_does_not_make_a_second_alert(app):
    family = Family(app, verifiers=1)
    assert family.elder_client.post("/api/panic").status_code == 201
    assert family.elder_client.post("/api/panic").status_code == 200
    assert len(family.verifier_clients[0].get("/api/verifier/alerts").get_json()) == 1
    assert len(events(app, "panic_raised")) == 1
    assert len(events(app, "panic_repeated")) == 1


def test_handling_clears_it_for_everyone_and_a_new_one_can_follow(app):
    family = Family(app, verifiers=2)
    alert = family.elder_client.post("/api/panic").get_json()
    res = family.verifier_clients[0].post(f"/api/verifier/alerts/{alert['id']}/handle")
    assert res.status_code == 200 and res.get_json()["handled"] is True
    assert family.verifier_clients[1].get("/api/verifier/alerts").get_json() == []
    assert family.elder_client.post("/api/panic").status_code == 201
    assert len(events(app, "panic_handled")) == 1


def test_a_verifier_cannot_raise_an_alert(app):
    family = Family(app, verifiers=1)
    assert family.verifier_clients[0].post("/api/panic").status_code == 403


def test_logged_out_cannot_raise_an_alert(app):
    assert new_client(app).post("/api/panic").status_code == 401


def test_an_elder_cannot_read_or_handle_the_verifier_endpoints(app):
    family = Family(app, verifiers=1)
    alert = family.elder_client.post("/api/panic").get_json()
    assert family.elder_client.get("/api/verifier/alerts").status_code == 403
    assert family.elder_client.post(f"/api/verifier/alerts/{alert['id']}/handle").status_code == 403


def test_another_familys_alert_is_invisible_and_cannot_be_handled(app):
    family = Family(app, verifiers=1)
    alert = family.elder_client.post("/api/panic").get_json()

    other_elder = register_elder(app.test_client(), email="other@example.com", name="Other")
    from app.tests.helpers import enroll_verifier, login
    enroll_verifier(app, other_elder, "stranger@example.com", name="Stranger")
    c = app.test_client()
    login(c, "stranger@example.com")
    assert c.get("/api/verifier/alerts").get_json() == []
    assert c.post(f"/api/verifier/alerts/{alert['id']}/handle").status_code == 404
    assert len(family.verifier_clients[0].get("/api/verifier/alerts").get_json()) == 1


def test_alert_with_no_family_still_works_and_says_nobody_was_told(app):
    c = new_client(app)
    register_elder(c)
    from app.tests.helpers import login
    login(c, "grandma@example.com")
    res = c.post("/api/panic")
    assert res.status_code == 201 and res.get_json()["notified"] == 0


def test_alerts_are_in_the_audit_log(app):
    family = Family(app, verifiers=1)
    alert = family.elder_client.post("/api/panic").get_json()
    family.verifier_clients[0].post(f"/api/verifier/alerts/{alert['id']}/handle")
    assert [e["event_type"] for e in events(app) if e["event_type"].startswith("panic")] == ["panic_raised", "panic_handled"]
