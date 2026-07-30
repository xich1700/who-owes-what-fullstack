# Who owes what? — Full-stack rebuild

A group's shared expenses — no spreadsheets, no account required for
everyone, no ads. This is a full-stack rebuild of the original
Streamlit prototype (who-owes-what), built with a proper separated
frontend and backend to reflect a more production-style architecture.

This project was developed during a hackathon based on the
organizer's problem statement and provided context. The
implementation was created through AI-assisted coding, with me
leading the requirements, prompting, testing, and iterative
refinement.

## Architecture

- Backend (backend/) - FastAPI + SQLAlchemy + SQLite, with JWT
  authentication. Exposes a REST API covering groups, people,
  expenses (equal and weighted splits), repayments, settlement
  math, a rule-based natural-language expense parser, AI-powered
  receipt scanning, and public view-only share links.
- Frontend (frontend/) - React (Vite), talking to the backend
  over HTTP with a JWT bearer token stored client-side.

Unlike the original Streamlit version, the frontend and backend are
fully separate services that communicate over a REST API - closer
to how a real product team would structure this.

## Running it

Backend:
cd backend
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000

Interactive API docs: http://localhost:8000/docs

Frontend (in a separate terminal):
cd frontend
npm install
npm run dev

App: http://localhost:5173

Both need to be running at the same time.

## Testing the backend

cd backend
.venv\Scripts\pip.exe install requests
.venv\Scripts\python.exe test_backend.py

## Receipt scanning

Optional. Needs your own Anthropic API key (from console.anthropic.com),
entered in the app itself - it's never written to disk or the database.
