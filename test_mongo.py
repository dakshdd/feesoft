from pymongo import MongoClient
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["school_db"]
    print("MongoDB connected, DB name:", db.name)
except Exception as e:
    print("MongoDB connection failed:", e)
