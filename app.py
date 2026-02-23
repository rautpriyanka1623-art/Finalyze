from flask import Flask, render_template, request, redirect, session, url_for, flash
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "finalyze_secret_key"

DB_PATH = "data/expenses.db"

# Ensure data folder exists
if not os.path.exists("data"):
    os.makedirs("data")

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Users table
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")
    # Expenses table
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        category TEXT,
        description TEXT,
        amount REAL
    )""")
    # Budget table
    c.execute("""CREATE TABLE IF NOT EXISTS budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL
    )""")
    conn.commit()
    conn.close()

init_db()

# Helper to get DB connection
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- Authentication --------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            flash("Signup successful! Please login.", "success")
            return redirect("/login")
        except sqlite3.IntegrityError:
            flash("Username already exists!", "danger")
    return render_template("signup.html")

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
            return redirect("/")
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        username = request.form["username"]
        new_password = generate_password_hash(request.form["password"])
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE users SET password=? WHERE username=?", (new_password, username))
        if c.rowcount == 0:
            flash("Username not found!", "danger")
        else:
            flash("Password updated! Login now.", "success")
        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("forgot.html")

# -------------------- Dashboard --------------------

@app.route("/", methods=["GET", "POST"])
def home():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]

    conn = get_db()
    c = conn.cursor()

    # Handle budget update
    if request.method == "POST" and "budget" in request.form:
        amount = float(request.form["budget"])
        # Check if budget exists
        c.execute("SELECT * FROM budget WHERE user_id=?", (user_id,))
        if c.fetchone():
            c.execute("UPDATE budget SET amount=? WHERE user_id=?", (amount, user_id))
        else:
            c.execute("INSERT INTO budget (user_id, amount) VALUES (?,?)", (user_id, amount))
        conn.commit()

    # Fetch budget
    c.execute("SELECT * FROM budget WHERE user_id=?", (user_id,))
    budget_row = c.fetchone()
    budget = budget_row["amount"] if budget_row else 0

    # Fetch expenses
    c.execute("SELECT * FROM expenses WHERE user_id=?", (user_id,))
    expenses = c.fetchall()

    # Category totals
    category_totals = {}
    for e in expenses:
        category_totals[e["category"]] = category_totals.get(e["category"], 0) + e["amount"]

    # Monthly summary
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_expenses = [e for e in expenses if datetime.strptime(e["date"], "%Y-%m-%d").month == current_month
                        and datetime.strptime(e["date"], "%Y-%m-%d").year == current_year]
    total_spent = sum(e["amount"] for e in monthly_expenses)
    remaining_budget = budget - total_spent

    # Highest category
    highest_category = max(category_totals, key=category_totals.get) if category_totals else None

    conn.close()
    return render_template("index.html",
                           expenses=expenses,
                           category_totals=category_totals,
                           total_spent=total_spent,
                           remaining_budget=remaining_budget,
                           highest_category=highest_category,
                           budget=budget)

# -------------------- Expense CRUD --------------------

@app.route("/add", methods=["POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]

    date = request.form["date"]
    category = request.form["category"]
    description = request.form["description"]
    amount = float(request.form["amount"])

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO expenses (user_id,date,category,description,amount) VALUES (?,?,?,?,?)",
              (user_id,date,category,description,amount))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/edit/<int:expense_id>", methods=["GET","POST"])
def edit_expense(expense_id):
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]

    conn = get_db()
    c = conn.cursor()

    if request.method=="POST":
        date = request.form["date"]
        category = request.form["category"]
        description = request.form["description"]
        amount = float(request.form["amount"])
        c.execute("""UPDATE expenses SET date=?, category=?, description=?, amount=? 
                     WHERE id=? AND user_id=?""",
                  (date, category, description, amount, expense_id, user_id))
        conn.commit()
        conn.close()
        return redirect("/")

    c.execute("SELECT * FROM expenses WHERE id=? AND user_id=?", (expense_id, user_id))
    expense = c.fetchone()
    conn.close()
    if not expense:
        flash("Expense not found!", "danger")
        return redirect("/")
    return render_template("edit.html", expense=expense)

@app.route("/delete/<int:expense_id>")
def delete_expense(expense_id):
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id, user_id))
    conn.commit()
    conn.close()
    return redirect("/")

# -------------------- Run App --------------------

if __name__=="__main__":
    app.run(debug=False, host="0.0.0.0")