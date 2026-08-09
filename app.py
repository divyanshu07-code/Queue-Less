import os
import sqlite3
from datetime import datetime
from functools import wraps
from statistics import mean

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DATABASE = os.environ.get("QUEUELESS_DB", os.path.join(os.path.dirname(__file__), "queue.db"))
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

SERVICES = ["College Office", "Canteen", "Clinic", "Library"]
SERVICE_ICONS = {
    "College Office": "building",
    "Canteen": "utensils",
    "Clinic": "stethoscope",
    "Library": "book",
}

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Return a request-scoped SQLite connection (avoids leaking connections)."""
    if "db" not in g:
        conn = sqlite3.connect(DATABASE, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT NOT NULL,
            token INTEGER NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'waiting',
            joined_at TEXT NOT NULL,
            serving_at TEXT,
            served_at TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_service_status ON queues(service, status)")
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "message": "Admin login required."}), 401
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.get("/admin/login")
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin"))
    return render_template("admin_login.html")


@app.post("/api/admin/login")
def admin_login_post():
    data = request.get_json(silent=True) or {}
    if data.get("password") == ADMIN_PASSWORD:
        session["is_admin"] = True
        session.permanent = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Incorrect password."}), 401


@app.post("/api/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def next_token(service):
    db = get_db()
    row = db.execute("SELECT MAX(token) AS max_token FROM queues WHERE service=?", (service,)).fetchone()
    return (row["max_token"] or 0) + 1


def avg_serve_minutes(service):
    """Average real serving duration for a counter, from its last 20
    completed tickets. Falls back to a 3-minute default with zero samples
    when a counter has no history yet (e.g. right after a reset)."""
    db = get_db()
    rows = db.execute(
        """
        SELECT serving_at, served_at
        FROM queues
        WHERE service=? AND served_at IS NOT NULL AND serving_at IS NOT NULL
        ORDER BY id DESC LIMIT 20
        """,
        (service,),
    ).fetchall()

    durations = []
    for r in rows:
        try:
            start = datetime.fromisoformat(r["serving_at"])
            end = datetime.fromisoformat(r["served_at"])
            seconds = (end - start).total_seconds()
            if 15 <= seconds <= 3600:
                durations.append(seconds / 60)
        except (TypeError, ValueError):
            pass

    if durations:
        return mean(durations), len(durations)
    return 3.0, 0


def estimate_wait(service, ahead, currently_serving_elapsed=None):
    """Estimate wait time in minutes for one waiting student, using real
    service-history averages. If someone is currently being served, subtract
    the time already spent serving them from the first slot's estimate so
    the number doesn't jump the instant a person reaches the counter."""
    avg, _ = avg_serve_minutes(service)
    total = avg * ahead

    if currently_serving_elapsed is not None:
        total += max(0.0, avg - currently_serving_elapsed)

    return max(1, round(total)) if (ahead > 0 or currently_serving_elapsed is not None) else 0


def traffic_level(waiting):
    if waiting == 0:
        return "clear"
    if waiting <= 3:
        return "low"
    if waiting <= 7:
        return "moderate"
    return "high"


def operational_recommendation(level, waiting, clearing_minutes):
    if level == "clear":
        return "All caught up — no action needed."
    if level == "low":
        return "Steady flow. Keep calling tokens as they come."
    if level == "moderate":
        return (
            f"Line is building — {waiting} waiting, about {clearing_minutes} min to clear. "
            "Consider pulling in a second staff member if one's free."
        )
    return (
        f"Backlog forming — {waiting} students waiting, about {clearing_minutes} min to clear "
        "at the current pace. Open a second counter or call for backup now."
    )


def serving_elapsed_minutes(service):
    db = get_db()
    row = db.execute(
        "SELECT serving_at FROM queues WHERE service=? AND status='serving' ORDER BY id DESC LIMIT 1",
        (service,),
    ).fetchone()
    if not row or not row["serving_at"]:
        return None
    try:
        started = datetime.fromisoformat(row["serving_at"])
        return max(0.0, (datetime.now() - started).total_seconds() / 60)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html", services=SERVICES, icons=SERVICE_ICONS)


@app.route("/student")
def student():
    return render_template("student.html", services=SERVICES, icons=SERVICE_ICONS)


@app.route("/admin")
@login_required
def admin():
    return render_template("admin.html", services=SERVICES, icons=SERVICE_ICONS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@app.get("/api/queue/<service>")
def queue(service):
    if service not in SERVICES:
        return jsonify({"success": False, "message": "Invalid service."}), 400

    db = get_db()
    current = db.execute(
        """
        SELECT token, name, serving_at FROM queues
        WHERE service=? AND status='serving'
        ORDER BY id DESC LIMIT 1
        """,
        (service,),
    ).fetchone()
    waiting = db.execute(
        """
        SELECT id, token, name, joined_at FROM queues
        WHERE service=? AND status='waiting'
        ORDER BY token
        """,
        (service,),
    ).fetchall()

    return jsonify(
        {
            "success": True,
            "service": service,
            "current": current["token"] if current else 0,
            "current_name": current["name"] if current else None,
            "waiting": [dict(r) for r in waiting],
            "count": len(waiting),
        }
    )


@app.post("/api/join")
def join():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()[:60]
    service = (data.get("service") or "").strip()

    if not name:
        return jsonify({"success": False, "message": "Enter your name."}), 400
    if service not in SERVICES:
        return jsonify({"success": False, "message": "Choose a valid service."}), 400

    db = get_db()

    # Prevent a person from holding two active tickets for the same counter.
    existing = db.execute(
        """
        SELECT id, token FROM queues
        WHERE service=? AND name=? AND status IN ('waiting', 'serving')
        ORDER BY id DESC LIMIT 1
        """,
        (service, name),
    ).fetchone()
    if existing:
        return jsonify(
            {
                "success": False,
                "message": f"{name} already has an active token (#{existing['token']}) for {service}.",
                "existing_id": existing["id"],
            }
        ), 409

    token = next_token(service)
    now = datetime.now().isoformat(timespec="seconds")
    cur = db.execute(
        """
        INSERT INTO queues(service, token, name, status, joined_at)
        VALUES (?, ?, ?, 'waiting', ?)
        """,
        (service, token, name, now),
    )
    db.commit()
    queue_id = cur.lastrowid

    ahead = db.execute(
        "SELECT COUNT(*) AS c FROM queues WHERE service=? AND status='waiting' AND token<?",
        (service, token),
    ).fetchone()["c"]

    elapsed = serving_elapsed_minutes(service)

    return jsonify(
        {
            "success": True,
            "id": queue_id,
            "token": token,
            "service": service,
            "name": name,
            "ahead": ahead,
            "estimated_minutes": estimate_wait(service, ahead, elapsed),
        }
    )


@app.get("/api/status/<int:queue_id>")
def status(queue_id):
    db = get_db()
    row = db.execute("SELECT * FROM queues WHERE id=?", (queue_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "message": "Queue ticket not found."}), 404

    current = db.execute(
        "SELECT token FROM queues WHERE service=? AND status='serving' ORDER BY id DESC LIMIT 1",
        (row["service"],),
    ).fetchone()

    if row["status"] == "waiting":
        ahead = db.execute(
            "SELECT COUNT(*) AS c FROM queues WHERE service=? AND status='waiting' AND token<?",
            (row["service"], row["token"]),
        ).fetchone()["c"]
        elapsed = serving_elapsed_minutes(row["service"])
        return jsonify(
            {
                "success": True,
                "status": "waiting",
                "token": row["token"],
                "service": row["service"],
                "name": row["name"],
                "ahead": ahead,
                "current": current["token"] if current else 0,
                "estimated_minutes": estimate_wait(row["service"], ahead, elapsed),
            }
        )

    return jsonify(
        {
            "success": True,
            "status": row["status"],
            "token": row["token"],
            "service": row["service"],
            "name": row["name"],
            "ahead": 0,
            "current": current["token"] if current else row["token"],
            "estimated_minutes": 0,
        }
    )


@app.post("/api/leave/<int:queue_id>")
def leave(queue_id):
    db = get_db()
    row = db.execute("SELECT status FROM queues WHERE id=?", (queue_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "message": "Ticket not found."}), 404
    if row["status"] != "waiting":
        return jsonify({"success": False, "message": "This ticket can no longer be cancelled."}), 400

    db.execute("UPDATE queues SET status='cancelled' WHERE id=?", (queue_id,))
    db.commit()
    return jsonify({"success": True})


@app.get("/api/stats/<service>")
def stats(service):
    if service not in SERVICES:
        return jsonify({"success": False, "message": "Invalid service."}), 400

    db = get_db()
    row = db.execute(
        """
        SELECT
            SUM(CASE WHEN status='waiting' THEN 1 ELSE 0 END) AS waiting,
            SUM(CASE WHEN status='serving' THEN 1 ELSE 0 END) AS serving,
            SUM(CASE WHEN status='served' THEN 1 ELSE 0 END) AS served,
            SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) AS cancelled
        FROM queues WHERE service=?
        """,
        (service,),
    ).fetchone()

    return jsonify(
        {
            "success": True,
            "service": service,
            "waiting": row["waiting"] or 0,
            "serving": row["serving"] or 0,
            "served": row["served"] or 0,
            "cancelled": row["cancelled"] or 0,
        }
    )


@app.get("/api/impact")
def impact():
    """Campus-wide 'what did the virtual queue actually save people' metric:
    total minutes students spent free to go about their day instead of
    physically standing in line, today, across every counter."""
    db = get_db()
    today_prefix = datetime.now().strftime("%Y-%m-%d")
    rows = db.execute(
        """
        SELECT joined_at, serving_at FROM queues
        WHERE serving_at IS NOT NULL AND substr(joined_at, 1, 10) = ?
        """,
        (today_prefix,),
    ).fetchall()

    total_minutes = 0.0
    count = 0
    for r in rows:
        try:
            joined = datetime.fromisoformat(r["joined_at"])
            serving = datetime.fromisoformat(r["serving_at"])
            minutes = (serving - joined).total_seconds() / 60
            if minutes > 0:
                total_minutes += minutes
                count += 1
        except (TypeError, ValueError):
            pass

    return jsonify(
        {
            "success": True,
            "minutes_saved": round(total_minutes),
            "tokens_served": count,
        }
    )


@app.get("/api/overview")
def overview():
    """Snapshot across every service, used for the public home/board view."""
    db = get_db()
    out = {}
    for service in SERVICES:
        row = db.execute(
            """
            SELECT
                SUM(CASE WHEN status='waiting' THEN 1 ELSE 0 END) AS waiting,
                MAX(CASE WHEN status='serving' THEN token END) AS current
            FROM queues WHERE service=?
            """,
            (service,),
        ).fetchone()
        out[service] = {"waiting": row["waiting"] or 0, "current": row["current"] or 0}
    return jsonify({"success": True, "services": out})


# ---------------------------------------------------------------------------
# Admin API (mutating actions require login)
# ---------------------------------------------------------------------------

@app.get("/api/intelligence/<service>")
@login_required
def intelligence(service):
    """Admin-only: traffic classification, an operational recommendation,
    and an estimated time to clear the current line, all derived from real
    service history rather than fixed guesses."""
    if service not in SERVICES:
        return jsonify({"success": False, "message": "Invalid service."}), 400

    db = get_db()
    waiting = db.execute(
        "SELECT COUNT(*) AS c FROM queues WHERE service=? AND status='waiting'", (service,)
    ).fetchone()["c"]

    avg, samples = avg_serve_minutes(service)
    elapsed = serving_elapsed_minutes(service)

    clearing = avg * waiting
    if elapsed is not None:
        clearing += max(0.0, avg - elapsed)
    clearing_minutes = round(clearing) if (waiting > 0 or elapsed is not None) else 0

    level = traffic_level(waiting)
    recommendation = operational_recommendation(level, waiting, clearing_minutes)

    return jsonify(
        {
            "success": True,
            "service": service,
            "waiting": waiting,
            "traffic_level": level,
            "avg_minutes": round(avg, 1),
            "sample_size": samples,
            "clearing_minutes": clearing_minutes,
            "recommendation": recommendation,
        }
    )


@app.post("/api/next")
@login_required
def call_next():
    data = request.get_json(silent=True) or {}
    service = data.get("service")
    if service not in SERVICES:
        return jsonify({"success": False, "message": "Invalid service."}), 400

    db = get_db()
    now = datetime.now().isoformat(timespec="seconds")

    db.execute(
        "UPDATE queues SET status='served', served_at=? WHERE service=? AND status='serving'",
        (now, service),
    )

    person = db.execute(
        "SELECT id, token, name FROM queues WHERE service=? AND status='waiting' ORDER BY token LIMIT 1",
        (service,),
    ).fetchone()

    if not person:
        db.commit()
        return jsonify({"success": False, "message": "No one is waiting."})

    db.execute("UPDATE queues SET status='serving', serving_at=? WHERE id=?", (now, person["id"]))
    db.commit()

    return jsonify({"success": True, "token": person["token"], "name": person["name"]})


@app.post("/api/serve/<int:queue_id>")
@login_required
def serve(queue_id):
    db = get_db()
    row = db.execute("SELECT status FROM queues WHERE id=?", (queue_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "message": "Ticket not found."}), 404
    if row["status"] not in ("waiting", "serving"):
        return jsonify({"success": False, "message": "This ticket is already closed."}), 400

    now = datetime.now().isoformat(timespec="seconds")
    if row["status"] == "waiting":
        # Mark it as having briefly entered serving so wait-time stats stay honest.
        db.execute("UPDATE queues SET status='serving', serving_at=? WHERE id=?", (now, queue_id))
    db.execute("UPDATE queues SET status='served', served_at=? WHERE id=?", (now, queue_id))
    db.commit()
    return jsonify({"success": True})


@app.post("/api/skip/<int:queue_id>")
@login_required
def skip(queue_id):
    """Send a no-show back to the end of the line instead of losing their ticket."""
    db = get_db()
    row = db.execute("SELECT service, status FROM queues WHERE id=?", (queue_id,)).fetchone()
    if not row:
        return jsonify({"success": False, "message": "Ticket not found."}), 404
    if row["status"] not in ("waiting", "serving"):
        return jsonify({"success": False, "message": "This ticket is already closed."}), 400

    new_token = next_token(row["service"])
    db.execute(
        "UPDATE queues SET token=?, status='waiting', serving_at=NULL WHERE id=?",
        (new_token, queue_id),
    )
    db.commit()
    return jsonify({"success": True, "new_token": new_token})


@app.post("/api/reset/<service>")
@login_required
def reset_service(service):
    """Demo helper: clear a service's queue back to empty."""
    if service not in SERVICES:
        return jsonify({"success": False, "message": "Invalid service."}), 400
    db = get_db()
    db.execute("DELETE FROM queues WHERE service=?", (service,))
    db.commit()
    return jsonify({"success": True})


@app.errorhandler(404)
def not_found(_err):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Not found."}), 404
    return render_template("404.html"), 404


init_db()

if __name__ == "__main__":
    if ADMIN_PASSWORD == "admin123":
        print("⚠  Using default admin password 'admin123' — set ADMIN_PASSWORD env var before deploying.")
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_mode, host="0.0.0.0", port=port)
