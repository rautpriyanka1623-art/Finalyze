from flask import Flask, render_template, request, redirect, session, flash
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "finalyze_secret_key"

DB_PATH = "data/expenses.db"

if not os.path.exists("data"):
    os.makedirs("data")

# ------------------ Initialize DB ------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create users table with budget column
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        budget REAL DEFAULT 150000
    )
    """)

    # Create expenses table
    c.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        category TEXT,
        amount REAL
    )
    """)

    # Add budget column to existing users table if missing
    try:
        c.execute("ALTER TABLE users ADD COLUMN budget REAL DEFAULT 150000")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ------------------ Routes ------------------
@app.route("/")
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        else:
            flash("Invalid credentials")

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        conn = get_db()
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect("/login")
        except:
            flash("Username already exists")

    return render_template("signup.html")

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        username = request.form["username"]
        new_password = generate_password_hash(request.form["new_password"])

        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
        conn.commit()
        conn.close()

        flash("Password updated. Please login.")
        return redirect("/login")

    return render_template("forgot.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM expenses WHERE user_id=?", (session["user_id"],))
    expenses = c.fetchall()
    conn.close()

    return render_template("dashboard.html", expenses=expenses)

# ------------------ Fixed Expenses Route ------------------
@app.route("/expenses", methods=["GET", "POST"])
def expenses_page():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    # ---------- Handle Total Budget form ----------
    if request.method == "POST":
        try:
            total_budget_input = float(request.form["total_budget"])
            c.execute("UPDATE users SET budget=? WHERE id=?", (total_budget_input, session["user_id"]))
            conn.commit()
        except Exception as e:
            print("Error updating budget:", e)

    # ---------- Fetch expenses ----------
    c.execute("SELECT * FROM expenses WHERE user_id=?", (session["user_id"],))
    expenses = c.fetchall()

    # ---------- Fetch user's total budget ----------
    c.execute("SELECT budget FROM users WHERE id=?", (session["user_id"],))
    row = c.fetchone()
    total_budget = row["budget"] if row and row["budget"] else 150000

    conn.close()

    # ---------- Calculate totals ----------
    total_expense = sum(float(e["amount"]) for e in expenses)
    highest_expense = max([float(e["amount"]) for e in expenses], default=0)
    remaining_expense = total_budget - total_expense

    return render_template(
        "expenses.html",
        expenses=expenses,
        total_budget=total_budget,
        total_expense=total_expense,
        highest_expense=highest_expense,
        remaining_expense=remaining_expense
    )
# ----------------------------------------------------------

@app.route("/add", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        date = request.form["date"]
        category = request.form["category"]
        amount = request.form["amount"]

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO expenses (user_id, date, category, amount) VALUES (?, ?, ?, ?)",
            (session["user_id"], date, category, amount),
        )
        conn.commit()
        conn.close()

        return redirect("/expenses")

    return render_template("add_expense.html")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()

    if request.method == "POST":
        date = request.form["date"]
        category = request.form["category"]
        amount = request.form["amount"]

        c.execute("""
        UPDATE expenses
        SET date=?, category=?, amount=?
        WHERE id=? AND user_id=?
        """, (date, category, amount, id, session["user_id"]))

        conn.commit()
        conn.close()
        return redirect("/expenses")

    c.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (id, session["user_id"]))
    expense = c.fetchone()
    conn.close()

    return render_template("edit_expense.html", expense=expense)

@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (id, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/expenses")

if __name__ == "__main__":
    app.run(debug=True)