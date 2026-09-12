import os
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Agar Render par ENV variable set hai
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/school_db")

client = MongoClient(MONGO_URI)
db = client["school_db"]   # 👈 yahan DB name explicitly diya
users_collection = db["users"]

# Default admin user
username = "admin"
password = "admin123"

existing = users_collection.find_one({"username": username})
if existing:
    print("Admin user already exists:", existing)
else:
    users_collection.insert_one({
        "username": username,
        "password_hash": generate_password_hash(password),  # 👈 field name fix
        "role": "admin"
    })
    print("✅ Admin user created successfully")
