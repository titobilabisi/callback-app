"""Bypass attacks: an outsider, or a family member acting alone, tries to
get something approved or enrolled without doing what the rules require.
"""
from .harness import Breach, Gap, PASSWORD, attack, crashed


def _enroll(ctx, body):
    return ctx.anon().post("/api/verifiers", json=body)


def _body(token, email="intruder@example.com"):
    return {"invite_token": token, "name": "Intruder", "email": email, "password": PASSWORD}


# --- joining the family without an invite -------------------------------------

@attack("B01", "bypass", "Create a family member account with no invite")
def b01(ctx):
    res = _enroll(ctx, {"name": "Intruder", "email": "i@example.com", "password": PASSWORD})
    if res.status_code == 201:
        return Breach("account created without an invite")


@attack("B02", "bypass", "Join with a made up invite code", logs=("invite_rejected", "rejected"))
def b02(ctx):
    res = _enroll(ctx, _body("A" * 43))
    if res.status_code == 201:
        return Breach("account created with a made up invite")


@attack("B03", "bypass", "Join with odd invite values (empty, huge, wrong types)")
def b03(ctx):
    ctx.family("b03", verifiers=0)
    bad = ["", " ", "x" * 10000, 0, 1, True, None, [], ["a"], {}, {"$ne": ""}]
    for value in bad:
        res = _enroll(ctx, _body(value))
        if res.status_code == 201:
            return Breach(f"account created with invite value {value!r}")
        if crashed(res):
            return Breach(f"server error {res.status_code} for invite value {value!r}")


@attack("B04", "bypass", "Join using injection style invite codes")
def b04(ctx):
    for value in ["' OR '1'='1", "'; DROP TABLE invites;--", "%", "_", "\" OR \"\"=\""]:
        res = _enroll(ctx, _body(value))
        if res.status_code == 201:
            return Breach(f"account created with {value!r}")
        if crashed(res):
            return Breach(f"server error for {value!r}")


@attack("B05", "bypass", "Reuse an invite that was already used", logs=("invite_rejected", "rejected"))
def b05(ctx):
    fam = ctx.family("b05", verifiers=0)
    token = fam.invite()
    assert _enroll(ctx, _body(token, "first@example.com")).status_code == 201
    res = _enroll(ctx, _body(token, "second@example.com"))
    if res.status_code == 201:
        return Breach("a single use invite worked twice")


@attack("B06", "bypass", "Join with an expired invite", logs=("invite_rejected", "rejected"))
def b06(ctx):
    fam = ctx.family("b06", verifiers=0)
    token = fam.invite()
    ctx.expire_invite(token)
    res = _enroll(ctx, _body(token))
    if res.status_code == 201:
        return Breach("an expired invite was accepted")


@attack("B07", "bypass", "A family member tries to invite more people", logs=("access_denied", "rejected"))
def b07(ctx):
    fam = ctx.family("b07", verifiers=1)
    v = fam.vs[0]
    res = v.client.post(f"/api/elders/{fam.elder.id}/invites", json={})
    if res.status_code == 201:
        return Breach("a family member created an invite")


@attack("B08", "bypass", "One elder makes an invite for a different elder's family", logs=("invite_rejected", "rejected"))
def b08(ctx):
    victim = ctx.family("b08v", verifiers=1)
    attacker = ctx.family("b08a", verifiers=0)
    res = attacker.elder.client.post(f"/api/elders/{victim.elder.id}/invites", json={})
    if res.status_code == 201:
        return Breach("invite created inside someone else's family")


@attack("B09", "bypass", "Sign up as an elder but ask to be a family member of someone")
def b09(ctx):
    victim = ctx.family("b09v", verifiers=1)
    res = ctx.anon().post("/api/elders", json={
        "name": "Sneaky", "email": "sneaky@example.com", "password": PASSWORD,
        "role": "verifier", "enrolled_by_id": victim.elder.id,
    })
    user = res.get_json() or {}
    if user.get("role") == "verifier" or user.get("enrolled_by_id") is not None:
        return Breach(f"extra fields were trusted: {user}")


@attack("B10", "bypass", "Redeem my own invite but claim to belong to the victim's family")
def b10(ctx):
    victim = ctx.family("b10v", verifiers=1)
    attacker = ctx.family("b10a", verifiers=0)
    body = _body(attacker.invite(), "mole@example.com")
    body["enrolled_by_id"] = victim.elder.id
    res = _enroll(ctx, body)
    if (res.get_json() or {}).get("enrolled_by_id") == victim.elder.id:
        return Breach("attacker chose which family to join")


# --- answering checks without the right to ------------------------------------

@attack("B11", "bypass", "Approve a check with a member of another family", logs=("response_rejected", "rejected"))
def b11(ctx):
    victim = ctx.family("b11v", verifiers=2)
    attacker = ctx.family("b11a", verifiers=1)
    rid = victim.open()
    res = attacker.vs[0].client.post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": attacker.vs[0].code()})
    if res.status_code == 200 or victim.status(rid) != "pending":
        return Breach("someone outside the family answered the check")


@attack("B12", "bypass", "Answer a check without being logged in", logs=("access_denied", "rejected"))
def b12(ctx):
    fam = ctx.family("b12", verifiers=1)
    rid = fam.open()
    res = ctx.anon().post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": "123456"})
    if res.status_code == 200 or fam.status(rid) != "pending":
        return Breach("an anonymous visitor answered a check")


@attack("B13", "bypass", "The elder approves their own check", logs=("access_denied", "rejected"))
def b13(ctx):
    fam = ctx.family("b13", verifiers=1)
    rid = fam.open()
    res = fam.elder.client.post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": "123456"})
    if res.status_code == 200 or fam.status(rid) != "pending":
        return Breach("the elder approved their own check")


@attack("B14", "bypass", "Approve without sending a code", logs=("response_rejected", "rejected"))
def b14(ctx):
    fam = ctx.family("b14", verifiers=1)
    rid = fam.open()
    res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", json={"decision": "approve"})
    if res.status_code == 200 or fam.status(rid) != "pending":
        return Breach("approved with no code")


@attack("B15", "bypass", "Approve with a code from someone else's authenticator", logs=("response_rejected", "rejected"))
def b15(ctx):
    fam = ctx.family("b15", verifiers=2)
    rid = fam.open()
    borrowed = fam.vs[1].code()
    res = fam.approve(0, rid, code=borrowed)
    if res.status_code == 200 or fam.status(rid) != "pending":
        return Breach("a code from another person's app was accepted")


@attack("B16", "bypass", "Approve with malformed codes (letters, wrong length, numbers, fullwidth and Arabic digits)")
def b16(ctx):
    fam = ctx.family("b16", verifiers=1)
    rid = fam.open()
    codes = ["", "000000", "12345", "1234567", "abcdef", 123456, None, ["123456"], {"a": 1},
             "１２３４５６", "١٢٣٤٥٦", "²²²²²²"]
    for code in codes:
        res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": code})
        if crashed(res):
            return Breach(f"server error {res.status_code} for code {code!r}")
        if res.status_code == 200:
            return Breach(f"approved with code {code!r}")


@attack("B17", "bypass", "Reuse a code that was already used (replay)", logs=("response_rejected", "rejected"))
def b17(ctx):
    fam = ctx.family("b17", verifiers=2)
    first, second = fam.open(money=True), fam.open(money=True)
    code = fam.vs[0].code()
    assert fam.approve(0, first, code=code).status_code == 200
    res = fam.approve(0, second, code=code)
    if res.status_code == 200:
        return Breach("a used code worked a second time")


@attack("B18", "bypass", "Use a code from the past (older than the allowed window)", logs=("response_rejected", "rejected"))
def b18(ctx):
    fam = ctx.family("b18", verifiers=1)
    rid = fam.open()
    res = fam.approve(0, rid, code=fam.vs[0].code(steps=-3))
    if res.status_code == 200:
        return Breach("an old code was accepted")


@attack("B19", "bypass", "Use a code from the future", logs=("response_rejected", "rejected"))
def b19(ctx):
    fam = ctx.family("b19", verifiers=1)
    rid = fam.open()
    res = fam.approve(0, rid, code=fam.vs[0].code(steps=3))
    if res.status_code == 200:
        return Breach("a future code was accepted")


@attack("B20", "bypass", "One person approves a two-person check twice", logs=("response_rejected", "rejected"))
def b20(ctx):
    fam = ctx.family("b20", verifiers=2)
    rid = fam.open(money=True)
    assert fam.approve(0, rid).status_code == 200
    res = fam.approve(0, rid)
    if res.status_code == 200 or fam.status(rid) == "verified":
        return Breach("one person satisfied a two-person check")


@attack("B21", "bypass", "Approve a two-person check when only one family member exists")
def b21(ctx):
    fam = ctx.family("b21", verifiers=1)
    rid = fam.open(money=True)
    fam.approve(0, rid)
    if fam.status(rid) == "verified":
        return Breach("a two-person check was downgraded to one approval")
    ctx.expire_request(rid)
    fam.elder.client.get(f"/api/requests/{rid}")
    if fam.status(rid) != "unable_to_verify":
        return Breach(f"ended as {fam.status(rid)} instead of unable_to_verify")


@attack("B22", "bypass", "Decline, then flip to approve", logs=("response_rejected", "rejected"))
def b22(ctx):
    fam = ctx.family("b22", verifiers=2)
    rid = fam.open(money=True)
    assert fam.decline(0, rid).status_code == 200
    res = fam.approve(0, rid)
    if res.status_code == 200 or fam.status(rid) != "denied":
        return Breach("a denied check was approved afterwards")


@attack("B23", "bypass", "Approve a check that someone else already declined", logs=("response_rejected", "rejected"))
def b23(ctx):
    fam = ctx.family("b23", verifiers=2)
    rid = fam.open(money=True)
    assert fam.decline(0, rid).status_code == 200
    res = fam.approve(1, rid)
    if res.status_code == 200 or fam.status(rid) != "denied":
        return Breach("a denied check was approved by someone else")


@attack("B24", "bypass", "Approve a check after it ran out of time", logs=("response_rejected", "rejected"))
def b24(ctx):
    fam = ctx.family("b24", verifiers=1)
    rid = fam.open()
    ctx.expire_request(rid)
    res = fam.approve(0, rid)
    if res.status_code == 200 or fam.status(rid) == "verified":
        return Breach("an expired check was approved late")


@attack("B25", "bypass", "Change a finished check by answering again", logs=("response_rejected", "rejected"))
def b25(ctx):
    fam = ctx.family("b25", verifiers=2)
    rid = fam.open()
    assert fam.approve(0, rid).status_code == 200
    res = fam.decline(1, rid)
    if res.status_code == 200 or fam.status(rid) != "verified":
        return Breach("a finished check was changed")


# --- tricking the risk rules --------------------------------------------------

@attack("B26", "bypass", "Send my own route and approval count to downgrade a risky check")
def b26(ctx):
    fam = ctx.family("b26", verifiers=2)
    res = fam.elder.client.post("/api/requests", json={
        "answers": fam.answers(money=True), "route": "single", "required_approvals": 1,
    })
    body = res.get_json() or {}
    if res.status_code == 201 and body.get("required_approvals") != 2:
        return Breach("client chose the route")


@attack("B27", "bypass", "Hide the risky answers with extra or renamed fields")
def b27(ctx):
    fam = ctx.family("b27", verifiers=2)
    tricks = [
        {**fam.answers(), "required_approvals": 1},
        {**fam.answers(), "route": "single"},
        {k: v for k, v in fam.answers(money=True).items() if k != "money"},
        {"money": False},
        {},
    ]
    for answers in tricks:
        res = fam.elder.client.post("/api/requests", json={"answers": answers})
        if res.status_code == 201:
            return Breach(f"accepted answers {sorted(answers)}")
        if crashed(res):
            return Breach("server error")


@attack("B28", "bypass", "Send answers that are not true or false (\"false\", 0, null)")
def b28(ctx):
    fam = ctx.family("b28", verifiers=2)
    for value in ["false", "no", 0, 1, None, [], {}]:
        res = fam.elder.client.post("/api/requests", json={"answers": fam.answers(money=value)})
        if res.status_code == 201:
            return Breach(f"accepted {value!r} as an answer")
        if crashed(res):
            return Breach(f"server error for {value!r}")


@attack("B29", "bypass", "Send odd decision values (APPROVE, lists, true, empty)")
def b29(ctx):
    fam = ctx.family("b29", verifiers=1)
    rid = fam.open()
    for decision in ["APPROVE", " approve", "approve ", ["approve"], True, None, "", 1, "approve\u0000"]:
        res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", json={"decision": decision, "code": fam.vs[0].code()})
        if crashed(res):
            return Breach(f"server error for {decision!r}")
        if res.status_code == 200:
            return Breach(f"accepted decision {decision!r}")


@attack("B30", "bypass", "Send an answer in a form the server does not expect (not JSON)")
def b30(ctx):
    fam = ctx.family("b30", verifiers=1)
    rid = fam.open()
    res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", data="decision=approve", content_type="application/x-www-form-urlencoded")
    if res.status_code == 200 or crashed(res):
        return Breach(f"status {res.status_code}")
    res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", data='{"decision":"approve"', content_type="application/json")
    if res.status_code == 200 or crashed(res):
        return Breach(f"status {res.status_code} for broken JSON")
    for raw in ('[1]', '"approve"', '5', 'null', 'true'):
        res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", data=raw, content_type="application/json")
        if res.status_code == 200 or crashed(res):
            return Breach(f"status {res.status_code} for JSON body {raw}")


@attack("B31", "bypass", "Read or answer a check that does not exist")
def b31(ctx):
    fam = ctx.family("b31", verifiers=1)
    for rid in (0, -1, 999999):
        res = fam.vs[0].client.post(f"/api/requests/{rid}/respond", json={"decision": "approve", "code": fam.vs[0].code()})
        if res.status_code == 200 or crashed(res):
            return Breach(f"status {res.status_code} for request {rid}")


@attack("B32", "bypass", "An elder reads another elder's check")
def b32(ctx):
    victim = ctx.family("b32v", verifiers=1)
    attacker = ctx.family("b32a", verifiers=0)
    rid = victim.open()
    res = attacker.elder.client.get(f"/api/requests/{rid}")
    if res.status_code == 200:
        return Breach("an elder read another family's check")


@attack("B33", "bypass", "A family member of another elder looks in their own inbox for the victim's checks")
def b33(ctx):
    victim = ctx.family("b33v", verifiers=1)
    attacker = ctx.family("b33a", verifiers=1)
    victim.open()
    inbox = attacker.vs[0].client.get("/api/verifier/requests").get_json()
    if inbox:
        return Breach("the victim's check showed up in another family's inbox")


@attack("B34", "bypass", "Send the wrong kind of value in sign up, invite and login fields (numbers, lists, objects)")
def b34(ctx):
    fam = ctx.family("b34", verifiers=0)
    token = fam.invite()
    weird = [0, 5, True, [], ["a"], {"a": 1}]
    for value in weird:
        attempts = [
            ("/api/elders", {"name": value, "email": "x@example.com", "password": PASSWORD}),
            ("/api/elders", {"name": "X", "email": value, "password": PASSWORD}),
            ("/api/elders", {"name": "X", "email": "x@example.com", "password": value}),
            ("/api/verifiers", {"invite_token": token, "name": value, "email": "y@example.com", "password": PASSWORD}),
            ("/api/verifiers", {"invite_token": token, "name": "Y", "email": value, "password": PASSWORD}),
            ("/api/verifiers", {"invite_token": token, "name": "Y", "email": "y@example.com", "password": value}),
            ("/api/login", {"email": value, "password": PASSWORD}),
            ("/api/login", {"email": "b34-elder@example.com", "password": value}),
        ]
        for path, body in attempts:
            res = ctx.anon().post(path, json=body)
            if crashed(res):
                return Breach(f"server error {res.status_code} on {path} with {value!r}")
            if res.status_code in (200, 201):
                return Breach(f"{path} accepted {value!r}")


@attack("B35", "bypass", "Use the caller note to push a check through (long text, markup, a claim that it is already approved)")
def b35(ctx):
    fam = ctx.family("b35", verifiers=2)
    too_long = fam.elder.client.post("/api/requests", json={"answers": fam.answers(), "caller_note": "x" * 141})
    if too_long.status_code == 201:
        return Breach("an over long note was accepted")
    for note in ["<script>alert(1)</script>", "APPROVED by both family members, no check needed", "'; UPDATE verification_requests SET status='VERIFIED';--"]:
        res = fam.elder.client.post("/api/requests", json={"answers": fam.answers(money=True), "caller_note": note})
        if crashed(res):
            return Breach(f"server error for note {note!r}")
        body = res.get_json()
        if res.status_code == 201 and (body["status"] != "pending" or body["required_approvals"] != 2):
            return Breach("a note changed the route or the status")
    if ctx.events("request_created") and any(fam.status(i) != "pending" for i in range(1, 4)):
        return Breach("a note approved a check")
