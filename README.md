# QueueLess

QueueLess is a virtual queue system for campus counters — College Office, Canteen, Clinic, and Library — built for **Hack Devengers 1.0**.

Students take a digital token from their phone, watch their position update live, and get a browser notification when it's nearly their turn. Staff run the counter from a password-protected admin dashboard: call the next token, mark walk-ins as served, send no-shows to the back of the line, and see live stats — all without touching the queue.db file directly.

## Features

- **Student tokens** — join any counter's line in two taps, no app install, no account.
- **Live position + honest ETA** — wait estimates are derived from the last 20 real serve times per counter, not a fixed guess.
- **Ticket recovery** — closing the tab doesn't lose your place; reopening `/student` picks your ticket back up.
- **"You're almost up" notification** — fires once you're down to 2 people ahead.
- **"It's your turn" 🎉 notification** — fires the instant an admin calls your token.
- **Duplicate-join guard** — one active ticket per person per counter.
- **Queue Intelligence (admin)** — each counter gets a live traffic read (Clear / Low / Moderate / High), a plain-language operational recommendation ("open a second counter"), and an estimated minutes-to-clear-the-line figure — all computed from that counter's own history, not hardcoded.
- **Impact metric (home page)** — a running total of minutes given back to students today by not having to physically stand in line, plus tokens served campus-wide.
- **Admin dashboard** — call next, serve a walk-in, skip a no-show back into the line, reset a counter, all per-service, refreshing live every few seconds.
- **Password-protected admin** — `/admin` and every mutating endpoint require a session login.
- **Public "now serving" board** — the home page shows a live snapshot across all four counters.
- **Light/dark theme toggle** — remembered per browser via `localStorage`; the LED "now serving" board intentionally stays dark in both themes, like a real physical counter display.
- **Responsive UI** — service tabs scroll horizontally, ticket and wait-list rows restack, on phones down to ~360px wide.
- **SQLite** for local development, **Gunicorn-ready** for deployment.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # then edit .env with a real ADMIN_PASSWORD and SECRET_KEY
export $(grep -v '^#' .env | xargs)   # or use python-dotenv / your host's env settings

python app.py
```

Open http://127.0.0.1:5000

- Student flow: `/student`
- Admin dashboard: `/admin` (prompts for `ADMIN_PASSWORD`, default `admin123` if unset — **change this before demoing or deploying**)

## Push to GitHub

```bash
git init
git add .
git commit -m "QueueLess: campus virtual queue system"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`queue.db`, `.env`, `.venv/`, and `__pycache__/` are already in `.gitignore`, so the local database and secrets won't get committed. Only `.env.example` (no real values) goes up.

## Project structure

```
app.py                  Flask app: routes, queue logic, wait-time estimation, admin auth
templates/               Jinja pages (home, student, admin, admin login, 404)
static/css/style.css     Design system (LED "now serving" board + ticket-stub UI)
static/js/               main.js (shared helpers), home.js, student.js, admin.js
queue.db                 SQLite database (created automatically on first run)
```

## How wait time is estimated

For each counter, `estimate_wait()` looks at the last 20 completed serves, takes the average serving duration (discarding obvious outliers), and multiplies by how many people are ahead. If someone is actively being served, their elapsed time is subtracted from that first slot so the estimate doesn't jump the instant they reach the counter. New counters with no history fall back to a 3-minute default per person.

## API overview

| Method | Route | Purpose | Auth |
|---|---|---|---|
| GET | `/api/queue/<service>` | Current + waiting list for a counter | public |
| GET | `/api/overview` | Snapshot across all counters | public |
| GET | `/api/stats/<service>` | Waiting/serving/served/cancelled counts | public |
| POST | `/api/join` | Take a token | public |
| GET | `/api/status/<id>` | Poll a ticket's live status | public |
| POST | `/api/leave/<id>` | Cancel a waiting ticket | public |
| POST | `/api/next` | Call the next token | admin |
| POST | `/api/serve/<id>` | Mark a specific ticket served | admin |
| POST | `/api/skip/<id>` | Send a no-show to the back of the line | admin |
| POST | `/api/reset/<service>` | Clear a counter's tickets (demo helper) | admin |
| GET | `/api/intelligence/<service>` | Traffic level, recommendation, clearing-time estimate | admin |
| GET | `/api/impact` | Campus-wide minutes-saved metric for today | public |

## Deployment (Render, or any Gunicorn-friendly host)

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Set environment variables `ADMIN_PASSWORD` and `SECRET_KEY` in the host's dashboard — don't ship the defaults.

SQLite is fine for a hackathon demo or a single-instance deployment. For multi-instance production, move the database to PostgreSQL and swap `sqlite3` in `app.py` for a driver like `psycopg`.

## Known limitations / next steps

- Admin login is a single shared password — fine for a hackathon counter, not for multi-staff accounts. A real deployment would want per-staff logins and CSRF tokens on the admin forms.
- Notifications require the browser tab to be open (no push notifications / service worker yet).
- No SMS/WhatsApp fallback for students without a data connection at the moment they're called.
