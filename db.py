from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["ai_expense_tracker"]

users_col = db["users"]
expenses_col = db["expenses"]
budgets_col = db["budgets"]   