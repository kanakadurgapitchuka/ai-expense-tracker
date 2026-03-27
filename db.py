from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://kanakadurgapitchuka999_db_user:UPsfxBaDDHOpKDc5@cluster0.gxymtsz.mongodb.net/ai_expense_tracker?retryWrites=true&w=majority",
    serverSelectionTimeoutMS=5000  # 🔥 important
)

db = client["ai_expense_tracker"]

users_col = db["users"]
expenses_col = db["expenses"]
budgets_col = db["budgets"]
