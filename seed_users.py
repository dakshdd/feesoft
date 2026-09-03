# seed_users.py
import os
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# ✅ MongoDB connectionimport os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["school_db"]
users_collection = db["users"]


# ✅ Seed users
users = [
    {
        "username": "admin2",
        "password_hash": generate_password_hash("admin123"),
        "role": "admin"
    },
    {
        "username": "teacher1",
        "password_hash": generate_password_hash("teachpass"),
        "role": "teacher"
    }
]

# ✅ Insert users (skip if already exists)
for user in users:
    if not users_collection.find_one({"username": user["username"]}):
        users_collection.insert_one(user)
        print(f"✔ User '{user['username']}' created.")
    else:
        print(f"ℹ User '{user['username']}' already exists.")

print("✅ Seeding complete.")
