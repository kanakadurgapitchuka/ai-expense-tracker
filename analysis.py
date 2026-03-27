from db import expenses_col

def calculate_total(user_id):
    expenses = list(expenses_col.find({"user_id": user_id}))
    return sum(exp["amount"] for exp in expenses)

def check_budget(total, budget):
    if total == 0:
        return ""
    elif total > budget:
        return "⚠ Warning! Your expenses exceeded the budget."
    else:
        return "✅ Your expenses are within the budget."

def get_expenses(user_id):
    return list(expenses_col.find({"user_id": user_id}))

def budget_status(total, budget):
    if total > budget:
        return "exceeded"
    else:
        return "within"
