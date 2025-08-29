from flask import Flask, redirect, request, render_template, url_for
import json
import os

# Instantiate Flask
app = Flask(__name__)

DATA_FILE = "data/transactions.json"

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

# Load transactions from JSON file (if exists), else start with default
def load_transactions():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return [
        {'id': 1, 'date': '2023-06-01', 'amount': 100},
        {'id': 2, 'date': '2023-06-02', 'amount': -200},
        {'id': 3, 'date': '2023-06-03', 'amount': 300}
    ]

# Save transactions to JSON
def save_transactions():
    with open(DATA_FILE, "w") as f:
        json.dump(transactions, f, indent=4)

transactions = load_transactions()

# ---------------- CRUD ROUTES ---------------- #

@app.route("/")
def get_transactions():
    return render_template("transactions.html", transactions=transactions)

@app.route("/add", methods=["GET", "POST"])
def add_transaction():
    if request.method == 'POST':
        transaction = {
            'id': transactions[-1]['id'] + 1 if transactions else 1, 
            'date': request.form['date'],
            'amount': float(request.form['amount'])
        }
        transactions.append(transaction)
        save_transactions()  # save immediately
        return redirect(url_for("get_transactions"))
    return render_template("form.html")

@app.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    if request.method == 'POST':
        date = request.form['date']
        amount = float(request.form['amount'])
        for transaction in transactions:
            if transaction['id'] == transaction_id:
                transaction['date'] = date
                transaction['amount'] = amount
                save_transactions()  # save immediately
                break
        return redirect(url_for("get_transactions"))

    for transaction in transactions:
        if transaction['id'] == transaction_id:
            return render_template("edit.html", transaction=transaction)
    return {"message": "Transaction not found"}, 404

@app.route("/delete/<int:transaction_id>")
def delete_transaction(transaction_id):
    global transactions
    transactions = [t for t in transactions if t['id'] != transaction_id]
    save_transactions()  # save immediately
    return redirect(url_for("get_transactions"))

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8181)
