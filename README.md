# Orbital — Product Engineering Take-Home

Welcome! This is a take-home assessment for a Product Engineering role at Orbital.

You've been given a working baseline application: a document Q&A tool for commercial real estate lawyers. Users upload legal documents (leases, title reports, environmental assessments) and ask questions about them. The AI assistant answers questions grounded in the document content.

The app works, but it has limitations. Your job is to extend it.

---

## Submission

**Loom walkthrough (2–3 min):** https://www.loom.com/share/9bd2aa7945f9474fb429a3dae33454eb

**What I built:**

- **Part 1 — Multi-document conversations.** A conversation now holds any number
  of documents. Upload more at any time via the attach button; switch between
  them with the document tabs in the reader panel; ask questions that span and
  attribute across every uploaded file. Existing documents persist when new ones
  are added.
- **Part 2 — Verifiable citations + an uncertainty signal.** Answers come with
  citation chips (document + page) that are **verified against the source text**,
  not just displayed — click one to jump the reader to that page. When a quote
  can't be found it's flagged as *unverified*, and when the answer isn't grounded
  in the documents the response is banner-warned instead of presented as fact.

The reasoning, the data behind Part 2, and what I'd do next are in
[`DECISIONS.md`](./DECISIONS.md). The supporting data analysis is reproducible in
[`analysis/`](./analysis/ANALYSIS.md) — run `python analysis/usage_analysis.py`.

---

## Setup

### Prerequisites
- Docker and Docker Compose
- just (command runner) — install via `brew install just` or `cargo install just`

That's it. Everything else runs inside containers.

### Getting Started

1. Clone this repository

2. Run the setup command:
```
just setup
```
   This copies `.env.example` to `.env` and builds the Docker images.

3. Add your Anthropic API key to `.env`:
```
ANTHROPIC_API_KEY=your_key_here
```
   We've provided an API key in the task email. You can also use your own.

4. Start everything:
```
just dev
```
   This starts PostgreSQL, the FastAPI backend (port 8000), and the React frontend (port 5173).
   Database migrations run automatically when the backend starts — no separate step needed.

5. Open http://localhost:5173 in your browser.

Your local `backend/src/` and `frontend/src/` directories are mounted into the containers —
edit files normally on your machine and changes hot-reload automatically.

### Sample Documents

We've included sample legal documents in `sample-docs/` for testing.

### Project Structure

- `frontend/` — React frontend (Vite + Tailwind + shadcn/Radix UI)
- `backend/` — FastAPI backend (Python 3.12 + SQLAlchemy + PydanticAI)
- `alembic/` — Database migrations
- `data/` — Product analytics and customer feedback (for Part 2)
- `sample-docs/` — Sample PDF documents for testing

### Useful Commands

- `just dev` — Start full stack (Postgres + backend + frontend)
- `just stop` — Stop all services
- `just reset` — Stop everything and clear database
- `just check` — Run all linters and type checks
- `just fmt` — Format all code
- `just db-init` — Run database migrations
- `just db-shell` — Open a psql shell
- `just shell-backend` — Shell into backend container
- `just logs-backend` — Tail backend logs
