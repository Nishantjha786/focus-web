import sqlite3
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from pathlib import Path
from flask import Flask, jsonify, request, render_template, g

TZ = ZoneInfo("Asia/Kolkata")
DB_PATH = Path("focus.db")
DEFAULT_TARGET = 120  # minutes/day

app = Flask(__name__)

# ---------- DB helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        g.db.execute("""
          CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
          )
        """)
        g.db.commit()
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def get_value(key, default=None):
    cur = get_db().execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    return (row[0] if row else default)

def set_value(key, value):
    db = get_db()
    db.execute("""
      INSERT INTO settings(key,value) VALUES(?,?)
      ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, str(value)))
    db.commit()

def get_int(key, default=0):
    v = get_value(key, None)
    return int(v) if v is not None else default

def today_str():
    return datetime.now(TZ).date().isoformat()

def ensure_initialized():
    if get_value("initialized") is None:
        set_value("balance", 0)
        set_value("target", DEFAULT_TARGET)
        set_value("last_applied", today_str())  # don't charge on first run
        set_value("initialized", 1)

def apply_missed_daily_charges():
    """Catch up daily target deductions for days the app was offline."""
    ensure_initialized()
    last = get_value("last_applied")
    if not last:
        set_value("last_applied", today_str())
        return
    last_d = date.fromisoformat(last)
    today_d = date.fromisoformat(today_str())
    if today_d > last_d:
        days = (today_d - last_d).days
        target = get_int("target", DEFAULT_TARGET)
        new_balance = get_int("balance", 0) - target * days
        set_value("balance", new_balance)
        set_value("last_applied", today_str())

@app.before_request
def _apply_on_every_request():
    # Also handles the nightly charge implicitly if a request comes after midnight.
    apply_missed_daily_charges()

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state")
def api_state():
    bal = get_int("balance", 0)
    tgt = get_int("target", DEFAULT_TARGET)
    need = max(0, -bal)
    return jsonify({
        "balance": bal,
        "target": tgt,
        "need": need,
        "today": today_str(),
        "last_applied": get_value("last_applied", today_str())
    })

@app.route("/api/work", methods=["POST"])
def api_work():
    try:
        mins = int(request.json.get("minutes", 0))
    except:
        return jsonify({"error": "Invalid minutes"}), 400
    new_bal = get_int("balance", 0) + mins
    set_value("balance", new_bal)
    return jsonify({"ok": True, "balance": new_bal})

@app.route("/api/relax", methods=["POST"])
def api_relax():
    try:
        mins = int(request.json.get("minutes", 0))
    except:
        return jsonify({"error": "Invalid minutes"}), 400
    new_bal = get_int("balance", 0) - mins
    set_value("balance", new_bal)
    return jsonify({"ok": True, "balance": new_bal})

@app.route("/api/target", methods=["GET", "POST"])
def api_target():
    if request.method == "GET":
        return jsonify({"target": get_int("target", DEFAULT_TARGET)})
    try:
        tgt = int(request.json.get("target"))
        if tgt <= 0:
            return jsonify({"error": "Target must be > 0"}), 400
    except:
        return jsonify({"error": "Invalid target"}), 400
    set_value("target", tgt)
    return jsonify({"ok": True, "target": tgt})

if __name__ == "__main__":
    # Local dev server
    app.run(host="0.0.0.0", port=8000, debug=True)
