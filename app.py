from flask import Flask, redirect, request, render_template, url_for
import json
import os
import threading
from pathlib import Path

app = Flask(__name__)

# --- Paths (robust when using `flask run`) ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "transactions.json"

# --- Concurrency guard (per-process) ---
_file_lock = threading.Lock()

# --- Defaults ---
DEFAULT_TRANSACTIONS = [
    {'id': 1, 'date': '2023-06-01', 'amount': 100},
    {'id': 2, 'date': '2023-06-02', 'amount': -200},
    {'id': 3, 'date': '2023-06-03', 'amount': 300},
]

def _normalize_record(item, fallback_id):
    """
    Ensure each record has correct keys/types.
    """
    if not isinstance(item, dict):
        return None
    try:
        id_ = int(item.get('id', fallback_id))
        date = str(item.get('date', ''))
        amount = float(item.get('amount', 0))
        return {'id': id_, 'date': date, 'amount': amount}
    except (TypeError, ValueError):
        return None

def load_transactions():
    """
    Robust loader:
    - Uses script-relative path (works with `flask run`)
    - Handles missing/empty/corrupted JSON
    - Validates structure and normalizes records
    """
    with _file_lock:
        if not DATA_FILE.exists() or DATA_FILE.stat().st_size == 0:
            # First run: create file with defaults for convenience
            _atomic_save(DEFAULT_TRANSACTIONS)
            return DEFAULT_TRANSACTIONS.copy()

        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # Corrupted file → fall back and rewrite a clean file
            _atomic_save(DEFAULT_TRANSACTIONS)
            return DEFAULT_TRANSACTIONS.copy()

        if not isinstance(data, list):
            # Unexpected structure → reset to defaults
            _atomic_save(DEFAULT_TRANSACTIONS)
            return DEFAULT_TRANSACTIONS.copy()

        cleaned = []
        for i, item in enumerate(data, start=1):
            norm = _normalize_record(item, fallback_id=i)
            if norm is not None:
                cleaned.append(norm)

        # If file had junk and we cleaned it, write back the sanitized version
        if cleaned != data:
            _atomic_save(cleaned)

        return cleaned

def _atomic_save(data):
    """
    Atomic write to avoid partial/corrupt files.
    """
    tmp = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DATA_FILE)  # atomic on POSIX & modern Windows

def save_transactions():
    with _file_lock:
        _atomic_save(transactions)

def next_id():
    return (max((int(t.get('id', 0)) for t in transactions), default=0) + 1)

# Load on startup
transactions = load_transactions()

# ---------------- CRUD ROUTES ---------------- #

@app.route("/")
def get_transactions():
    return render_template("transactions.html", transactions=transactions)

@app.route("/add", methods=["GET", "POST"])
def add_transaction():
    if request.method == 'POST':
        transaction = {
            'id': next_id(),
            'date': request.form['date'],
            'amount': float(request.form['amount']),
        }
        transactions.append(transaction)
        save_transactions()
        return redirect(url_for("get_transactions"))
    return render_template("form.html")

@app.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    if request.method == 'POST':
        date = request.form['date']
        amount = float(request.form['amount'])
        for t in transactions:
            if t['id'] == transaction_id:
                t['date'] = date
                t['amount'] = amount
                save_transactions()
                break
        return redirect(url_for("get_transactions"))

    for t in transactions:
        if t['id'] == transaction_id:
            return render_template("edit.html", transaction=t)
    return {"message": "Transaction not found"}, 404

@app.route("/delete/<int:transaction_id>")
def delete_transaction(transaction_id):
    # mutate in place to avoid losing references
    idx = next((i for i, t in enumerate(transactions) if t['id'] == transaction_id), None)
    if idx is not None:
        transactions.pop(idx)
        save_transactions()
    return redirect(url_for("get_transactions"))

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8181)
