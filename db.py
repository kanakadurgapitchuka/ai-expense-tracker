from pymongo import MongoClient

# ✅ client ni assign cheyali
client = MongoClient("mongodb+srv://kanakadurgapitchuka999_db_user:UPsfxBaDDHOpKDc5@cluster0.gxymtsz.mongodb.net/")

# database
db = client["ai_expense_tracker"]

# collections
users_col = db["users"]
expenses_col = db["expenses"]
budgets_col = db["budgets"]
