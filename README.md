# CallBack

A calm second check before you act. CallBack is a risk based, invite only verification tool that helps an older adult check a suspicious call with a trusted family member before sending money or sharing personal information. Built as a Georgia Tech PUBP 6727 Cybersecurity Practicum capstone project.

## Current status

This repo is being built in stages that match the project proposal timeline.

- Visual direction and all core screens: done
- Chunk 1, invite only enrollment: done, with tests
- Chunk 2, risk scoring and routing (six questions, server side routing): done, with tests
- Chunk 3, verification requests and approve/decline (single and two-person, timeout to Unable to Verify): done, with tests
- Chunk 4, panic alert: not started yet
- Chunk 5, evaluation: not started yet

The screens now run against the real backend: an elder signs up, invites family members, answers the six risk questions, and each family member approves or declines on their own device. The elder's screen shows the result.

Still to do from the roadmap (Phase 4 and later): TOTP, rate limiting, replay-proof signed approval tokens, audit event logging, and the 30 bypass / 20 compromise adversarial scripts. Passwords are hashed with Argon2id and sessions are signed HttpOnly cookies, but there is no login rate limiting yet.

## How a check works

1. The elder answers six yes/no questions (wording lives in `backend/app/risk.py`).
2. The server decides the route. Money requested OR personal/account info requested means two family members must approve. Anything else needs one. All six answers are stored. A route sent by the client is ignored.
3. Family members see the request in their inbox and approve or decline.
4. Two-person requests need two different people. The same person answering twice is rejected.
5. Any decline ends it as Denied. If nobody finishes in time (5 minutes by default) it ends as Unable to Verify. It is never turned into an approval, and a finished request cannot be changed.

## Project structure

```
backend/   Flask REST API
frontend/  React (Vite) and Tailwind CSS
```

## Running the backend

```
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python run.py
```

The API runs on http://localhost:5001.

Run the test suite with:

```
./venv/bin/python -m pytest app/tests/ -q
```

This includes all 64 combinations of the six risk answers, and scripted attempts to break the two-person rule (same person twice, one compromised account, expired and replayed responses).

## Running the frontend

```
cd frontend
npm install
npm run dev
```

The app runs on http://localhost:5173. It forwards `/api` to the backend on port 5001, so start the backend first and keep both running.

To try it on a phone on the same Wi-Fi, start the frontend with `npm run dev -- --host` and open the Network address it prints.

To try the full flow you need three sessions: the elder, and two family members who join with invite links. Use one normal window and two private/incognito windows (or different browsers), because each login is a separate cookie.

## Design

Built as a Progressive Web App, installed to the home screen, so it feels like a real app without needing native iOS or Android development. The UI follows an accessibility first direction for older adults: large tap targets, one action per screen, high contrast text, and minimal wording.
