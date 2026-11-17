# Attack results

Each row is one attack run against a fresh copy of the app. DEFENDED means the attack failed and the audit log recorded it where it should.

Totals: 52 defended, 10 gap

## Bypass attacks (35)

| ID | Attack | Result | In audit log | Notes |
|---|---|---|---|---|
| B01 | Create a family member account with no invite | DEFENDED | n/a |  |
| B02 | Join with a made up invite code | DEFENDED | yes |  |
| B03 | Join with odd invite values (empty, huge, wrong types) | DEFENDED | n/a |  |
| B04 | Join using injection style invite codes | DEFENDED | n/a |  |
| B05 | Reuse an invite that was already used | DEFENDED | yes |  |
| B06 | Join with an expired invite | DEFENDED | yes |  |
| B07 | A family member tries to invite more people | DEFENDED | yes |  |
| B08 | One elder makes an invite for a different elder's family | DEFENDED | yes |  |
| B09 | Sign up as an elder but ask to be a family member of someone | DEFENDED | n/a |  |
| B10 | Redeem my own invite but claim to belong to the victim's family | DEFENDED | n/a |  |
| B11 | Approve a check with a member of another family | DEFENDED | yes |  |
| B12 | Answer a check without being logged in | DEFENDED | yes |  |
| B13 | The elder approves their own check | DEFENDED | yes |  |
| B14 | Approve without sending a code | DEFENDED | yes |  |
| B15 | Approve with a code from someone else's authenticator | DEFENDED | yes |  |
| B16 | Approve with malformed codes (letters, wrong length, numbers, fullwidth and Arabic digits) | DEFENDED | n/a |  |
| B17 | Reuse a code that was already used (replay) | DEFENDED | yes |  |
| B18 | Use a code from the past (older than the allowed window) | DEFENDED | yes |  |
| B19 | Use a code from the future | DEFENDED | yes |  |
| B20 | One person approves a two-person check twice | DEFENDED | yes |  |
| B21 | Approve a two-person check when only one family member exists | DEFENDED | n/a |  |
| B22 | Decline, then flip to approve | DEFENDED | yes |  |
| B23 | Approve a check that someone else already declined | DEFENDED | yes |  |
| B24 | Approve a check after it ran out of time | DEFENDED | yes |  |
| B25 | Change a finished check by answering again | DEFENDED | yes |  |
| B26 | Send my own route and approval count to downgrade a risky check | DEFENDED | n/a |  |
| B27 | Hide the risky answers with extra or renamed fields | DEFENDED | n/a |  |
| B28 | Send answers that are not true or false ("false", 0, null) | DEFENDED | n/a |  |
| B29 | Send odd decision values (APPROVE, lists, true, empty) | DEFENDED | n/a |  |
| B30 | Send an answer in a form the server does not expect (not JSON) | DEFENDED | n/a |  |
| B31 | Read or answer a check that does not exist | DEFENDED | n/a |  |
| B32 | An elder reads another elder's check | DEFENDED | n/a |  |
| B33 | A family member of another elder looks in their own inbox for the victim's checks | DEFENDED | n/a |  |
| B34 | Send the wrong kind of value in sign up, invite and login fields (numbers, lists, objects) | DEFENDED | n/a |  |
| B35 | Use the caller note to push a check through (long text, markup, a claim that it is already approved) | DEFENDED | n/a |  |

## Compromise attacks (27)

| ID | Attack | Result | In audit log | Notes |
|---|---|---|---|---|
| C01 | Stolen password of a family member who has not finished authenticator setup | GAP | n/a | with only the password, the attacker took over the unfinished authenticator setup and approved. Only possible before the real person finishes setup |
| C02 | Stolen password of a set up family member: guess the approval code | DEFENDED | yes |  |
| C03 | Use a stolen password to lock the real family member out of approving | GAP | n/a | wrong guesses lock the account's approvals for about 15 minutes, which also blocks the real person. Accepted trade-off for stopping code guessing |
| C04 | One family member fully compromised (password and phone) on a two-person check | DEFENDED | yes |  |
| C05 | Compromised family member tries elder only actions | DEFENDED | yes |  |
| C06 | Compromised family member reads the activity log | DEFENDED | yes |  |
| C07 | Two family members fully compromised on a two-person check | GAP | n/a | an attacker holding two different family members' passwords and phones can approve. That is the limit of the two-person rule |
| C08 | Elder account compromised: add fake family members and approve | GAP | n/a | whoever controls the elder's account can invite their own people and approve. Not stopped today |
| C09 | Forge a login cookie with a wrong guess of the signing key | DEFENDED | n/a |  |
| C10 | Forge a login cookie using the signing key that was in the public source code | DEFENDED | n/a |  |
| C11 | Reuse a copied login cookie after the person signed out | GAP | n/a | a copied cookie still works after sign out until it expires (sessions are signed cookies, not stored on the server) |
| C12 | Guess a family member's password at login | DEFENDED | yes |  |
| C13 | Try thousands of different emails from one place (credential stuffing) | DEFENDED | yes |  |
| C14 | Lock a real person out of logging in by guessing their password | GAP | n/a | wrong guesses lock that account's login for about 15 minutes, which also blocks the real person |
| C15 | Tell whether an email has an account from the login response | DEFENDED | n/a |  |
| C16 | Tell whether an email has an account from the sign up response | GAP | n/a | sign up says an email is already taken, which confirms that person has an account. Low risk, common trade-off |
| C17 | Look for passwords, hashes or authenticator secrets in what the server sends back | DEFENDED | n/a |  |
| C18 | Add, change or delete activity log entries through the API | DEFENDED | n/a |  |
| C19 | Edit the activity log directly in the database | DEFENDED | n/a |  |
| C20 | Delete log entries from the middle of the log to hide an attack | DEFENDED | n/a |  |
| C21 | Delete the newest log entries so the last thing that happened disappears | GAP | n/a | removing only the newest entries leaves a chain that still checks out, because nothing after them points back. Fix: copy the latest fingerprint somewhere else from time to time |
| C22 | Edit a log entry and rewrite every fingerprint after it (database access only) | DEFENDED | n/a |  |
| C23 | Change a check to approved directly in the database | GAP | n/a | the app trusts the database: it shows approved, though the log has no approvals for it. The mismatch is visible in the log but not checked automatically |
| C24 | Make a request on the elder's behalf from another website (cross-site post) | DEFENDED | n/a |  |
| C25 | Ask from an untrusted website origin and see if the server allows it | DEFENDED | n/a |  |
| C26 | Capture an approval request and send the exact same one again | DEFENDED | yes |  |
| C27 | Coached elder: a scammer talks the elder into answering no to every risk question | GAP | n/a | if the elder is coached to answer no, the check needs only one family member. The six questions are only as honest as the elder's answers. The caller note and the family member's own call back are the backstop |
