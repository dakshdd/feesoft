import os
from pymongo import MongoClient, errors

# ------------------ MongoDB Connection ------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

try:
    # Atlas ke liye TLS enable karo
    client = MongoClient(MONGO_URI, tls=True)

    # --- School DB ---
    school_db = client["school_db"]
    master_collection = school_db["master"]
    counters = school_db["counters"]

    # --- Transport DB ---
    transport_db = client["transport_db"]
    transport_collection = transport_db["stand_name"]

    # --- Transactions DB ---
    tran_db = client["tran"]
    tran_collection = tran_db["transactions"]

    users_collection = school_db["users"]

    # Index creation safe check
    try:
        tran_collection.create_index(
            [("adm_code", 1), ("month", 1)], unique=True)
    except Exception as e:
        print(f"⚠️ Index creation failed: {e}")

except errors.ServerSelectionTimeoutError as e:
    print(f"❌ MongoDB connection failed: {e}")
    master, counters, transport_collection, tran_collection = None, None, None, None
