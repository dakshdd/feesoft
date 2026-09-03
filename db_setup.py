from pymongo import MongoClient
from werkzeug.security import generate_password_hash

client = MongoClient("mongodb://localhost:27017/")
db = client["school_db"]
users = db["users"]

users.insert_one({
    "username": "manjeet",
    "password_hash": generate_password_hash("auto_face"),
    "role": "admin"
})
print("User inserted successfully!")
