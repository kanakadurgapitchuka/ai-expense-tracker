from pymongo import MongoClient

MongoClient("mongodb+srv://kanakadurgapitchuka999_db_user:UPsfxBaDDHOpKDc5@cluster0.gxymtsz.mongodb.net/")
db = client["ai_expense_tracker"]

users_col = db["users"]
expenses_col = db["expenses"]
budgets_col = db["budgets"]   
