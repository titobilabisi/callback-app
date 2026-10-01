# CallBack

A calm second check before you act. CallBack is a risk based, invite only verification tool that helps an older adult check a suspicious call with a trusted family member before sending money or sharing personal information. Built as a Georgia Tech PUBP 6727 Cybersecurity Practicum capstone project.

## Current status

This repo is being built in stages that match the project proposal timeline.

- Visual direction and all core screens: done
- Chunk 1, invite only enrollment: done, with a passing test suite
- Chunk 2, risk scoring and routing: not started yet
- Chunk 3, timed single use verification and approve/decline: not started yet
- Chunk 4, panic alert: not started yet
- Chunk 5, evaluation: not started yet

The frontend currently uses mock data to demonstrate the full click through experience (all 11 screens). The real backend logic is being wired in chunk by chunk, matching the project timeline.

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

The API runs on http://localhost:5000.

Run the test suite with:

```
./venv/bin/python -m pytest app/tests/ -q
```

## Running the frontend

```
cd frontend
npm install
npm run dev
```

The app runs on http://localhost:5173.

## Design

Built as a Progressive Web App, installed to the home screen, so it feels like a real app without needing native iOS or Android development. The UI follows an accessibility first direction for older adults: large tap targets, one action per screen, high contrast text, and minimal wording.
