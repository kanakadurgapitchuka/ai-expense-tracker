from flask import Flask, render_template, request, redirect, session, send_file
from db import users_col, expenses_col
from bson.objectid import ObjectId
from datetime import datetime
from ai_model import predict_category_wise
from openpyxl import Workbook
import io
import random
import os

print(os.listdir("static/images"))
app = Flask(__name__)
app.secret_key = "supersecretkey123"

DEFAULT_CATEGORIES = [
    "Groceries", "Bills", "Travel", "Food",
    "Shopping", "Hospital", "School",
    "College Fee", "Others"
]

# ================= HOME =================
@app.route("/")
def home():
    return render_template("home.html")

# ================= ABOUT =================
@app.route("/about")
def about():
    return render_template("about.html")

# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        if users_col.find_one({"username": username}):
            return "User already exists!"

        user_id = "U" + str(random.randint(1000, 9999))

        users_col.insert_one({
            "user_id": user_id,
            "username": username,
            "password": password,
            "budgets": {}
        })

        session["welcome_user"] = username
        return redirect("/login")

    return render_template("register.html")

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    welcome = session.pop("welcome_user", None)

    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        user = users_col.find_one({"username": username})

        if user and user["password"] == password:
            session["user_id"] = user["user_id"]
            return redirect("/dashboard")

        return "Invalid credentials"

    return render_template("login.html", welcome=welcome)

# ================= SET BUDGET =================
@app.route("/set_budget", methods=["GET", "POST"])
def set_budget():
    if "user_id" not in session:
        return redirect("/login")

    user = users_col.find_one({"user_id": session["user_id"]})
    budgets = user.get("budgets", {})

    if request.method == "POST":
        category = request.form["category"]
        amount = float(request.form["amount"])
        month = request.form["month"]

        if month not in budgets:
            budgets[month] = {}

        budgets[month][category] = amount

        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"budgets": budgets}}
        )

        session["success_msg"] = f"Budget set for {category} ({month})!"
        return redirect("/dashboard")

    return render_template("set_budget.html", categories=DEFAULT_CATEGORIES)

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    selected_month = request.args.get("month")

    if not selected_month:
        selected_month = datetime.now().strftime("%Y-%m")

    user = users_col.find_one({"user_id": session["user_id"]})
    budgets = user.get("budgets", {})

    expenses = list(expenses_col.find({
        "user_id": session["user_id"]
    }))

    for e in expenses:
        e["_id"] = str(e["_id"])

    # ===== CATEGORY TOTALS =====
    category_totals = {}
    for e in expenses:
        if e.get("date", "").startswith(selected_month):
            cat = e.get("category", "Others")
            amt = float(e.get("amount", 0))
            category_totals[cat] = category_totals.get(cat, 0) + amt
    top_category = None
    if category_totals:
        top_category = max(category_totals, key=category_totals.get)

    # ===== MONTHLY TOTALS =====
    monthly_totals = {}
    for e in expenses:
        date = e.get("date", "")
        if date:
            month = date[:7]
            monthly_totals[month] = monthly_totals.get(month, 0) + float(e["amount"])

    sorted_months = sorted(monthly_totals.keys())
    month_labels = sorted_months
    month_data = [monthly_totals[m] for m in sorted_months]
    
    # ===== CURRENT MONTH BUDGET =====
    current_month = datetime.now().strftime("%Y-%m")
    month_budget = budgets.get(selected_month, {})

    # ===== SMART SUGGESTION =====
    suggestion = None
    if sorted_months:
        latest_month = selected_month
        monthly_category_spent = {}

        for e in expenses:
            if e.get("date", "").startswith(latest_month):
                cat = e.get("category", "Others")
                monthly_category_spent[cat] = monthly_category_spent.get(cat, 0) + float(e["amount"])

        if monthly_category_spent:
            exceeded_categories = []
            for cat, spent in monthly_category_spent.items():
                budget = float(month_budget.get(cat, 0))

                if budget > 0 and spent > budget:
                    exceeded_categories.append(cat)

            if exceeded_categories:
                suggestion = f"You exceeded your budget in {', '.join(exceeded_categories)}. Try to reduce spending next month."

            else:
                highest_category = max(monthly_category_spent, key=monthly_category_spent.get)
                highest_amount = monthly_category_spent[highest_category]
                suggestion = f"You spent more on {highest_category} (₹{round(highest_amount,2)}). Try to optimize this category."

    # ===== AI PREDICTION =====

    filtered_expenses = [
    e for e in expenses
    if e.get("date", "").startswith(selected_month)
    ]

    category_predictions = {}   # 👉 always initialize

    try:
        category_predictions = predict_category_wise(expenses)
    except:
        pass   # 👉 nothing, already empty dict

# 👉 ALWAYS defined (important)
    total_prediction = abs(sum(category_predictions.values())) if category_predictions else 0

    # ===== CURRENT MONTH BUDGET =====
    current_month = datetime.now().strftime("%Y-%m")
    month_budget = budgets.get(selected_month, {})

    # ===== REPORT =====
    report = []
    for cat in DEFAULT_CATEGORIES:
        budget = float(month_budget.get(cat, 0))
        spent = float(category_totals.get(cat, 0))

        status = "Exceeded" if (budget > 0 and spent > budget) else "Within"

        report.append({
            "category": cat,
            "spent": round(spent, 2),
            "budget": round(budget, 2),
            "status": status
        })

    pie_labels = [r["category"] for r in report if r["spent"] > 0]
    pie_data = [r["spent"] for r in report if r["spent"] > 0]

    total_spent = sum(category_totals.values())
    total_budget = sum(float(v) for v in month_budget.values())

    total_savings = max(total_budget - total_spent, 0)

# ===== SAVINGS PERCENTAGE =====
    savings_percentage = max((total_savings / total_budget) * 100, 0) if total_budget > 0 else 0

    success_msg = session.pop("success_msg", None)
    warning_msg = session.pop("warning_msg", None)
    error_msg = session.pop("error_msg", None)

    return render_template(
    "dashboard.html",
    report=report,
    total=round(total_spent, 2),
    total_budget=round(total_budget, 2),
    savings=round(total_savings, 2),
    savings_percentage=round(savings_percentage, 2),
    expenses=expenses,
    labels=month_labels,
    spent_data=month_data,
    predicted=round(abs(total_prediction), 2),
    pie_labels=pie_labels,
    pie_data=pie_data,
    success_msg=success_msg,
    warning_msg=warning_msg,
    error_msg=error_msg,
    suggestion=suggestion,
    selected_month=selected_month,
    top_category=top_category
)

# ================= ADD EXPENSE =================
@app.route("/add_expense", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        category = request.form["category"]
        amount = float(request.form["amount"])
        date = request.form["date"]

        expense_month = date[:7]

        user = users_col.find_one({"user_id": session["user_id"]})
        budgets = user.get("budgets", {})
        month_budget = budgets.get(expense_month, {})

        if category not in month_budget:
            session["warning_msg"] = f"No budget set for {category} in {expense_month}!"
            return redirect("/dashboard")

        expenses_col.insert_one({
            "user_id": session["user_id"],
            "date": date,
            "time": datetime.now().strftime("%H:%M"),
            "category": category,
            "amount": amount
        })

        session["success_msg"] = "Expense added successfully!"

        # Exceed Check
        user_expenses = [
            e for e in expenses_col.find({
                "user_id": session["user_id"],
                "category": category
            })
            if e.get("date", "").startswith(expense_month)
        ]

        # 🔔 80% Alert
    if budget > 0 and total_spent >= 0.8 * budget and total_spent < budget:
        session["warning_msg"] = f"You have used 80% of your budget for {category}!"

# 🔴 100% Used (NEW ADD)
    elif total_spent == budget:
        session["success_msg"] = f"You have fully used your budget for {category} (100%)!"

# ❌ Exceeded
    elif total_spent > budget:
        session["error_msg"] = f"Budget exceeded for {category} ({expense_month})!"

        return redirect("/dashboard")

    return render_template("add_expense.html")

# ================= DELETE =================
@app.route("/delete/<id>")
def delete_expense(id):
    expenses_col.delete_one({
        "_id": ObjectId(id),
        "user_id": session["user_id"]
    })
    session["success_msg"] = "Expense deleted successfully!"
    return redirect("/dashboard")

# ================= UPDATE =================
@app.route("/update/<id>", methods=["GET", "POST"])
def update_expense(id):
    expense = expenses_col.find_one({
        "_id": ObjectId(id),
        "user_id": session["user_id"]
    })

    if request.method == "POST":
        expenses_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "category": request.form["category"],
                "amount": float(request.form["amount"]),
                "date": request.form["date"]
            }}
        )
        session["success_msg"] = "Expense updated successfully!"
        return redirect("/dashboard")

    return render_template("update_expense.html", expense=expense)

# ================= EXPORT TO EXCEL =================
@app.route("/export_excel")
def export_excel():

    if "user_id" not in session:
        return redirect("/login")

    expenses = list(expenses_col.find({
        "user_id": session["user_id"]
    }))

    wb = Workbook()
    ws = wb.active
    ws.title = "Expenses Report"

    # Headers
    ws.append(["Category", "Amount (₹)", "Date", "Time"])

    # Data
    for e in expenses:
        ws.append([
            e.get("category"),
            e.get("amount"),
            e.get("date"),
            e.get("time")
        ])

    # Save to memory
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name="Expense_Report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=False, port=5001)
