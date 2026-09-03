import os
from pymongo import MongoClient

# Environment variable se URI lo, default localhost
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

# Connection
client = MongoClient(MONGO_URI, tls=True)

# --- School DB ---
school_db = client["school_db"]
master = school_db["master"]
counters = school_db["counters"]

# --- Transport DB ---
transport_db = client["transport_db"]
transport_collection = transport_db["stand_name"]

# --- Transactions DB ---
tran_db = client["tran"]
tran_col = tran_db["transactions"]
