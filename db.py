import os
from pymongo import MongoClient, errors

# ------------------ MongoDB URI ------------------
LOCAL_URI = "mongodb://localhost:27017/"
ATLAS_URI = "mongodb+srv://dakshdd_db_user:dhanjal01@cluster0.w9rs06v.mongodb.net/school_db?retryWrites=true&w=majority"

MONGO_URI = os.getenv("MONGO_URI", ATLAS_URI)

# ------------------ Collections ------------------
master_collection = None
counters_collection = None
users_collection = None
students_collection = None
fees_collection = None
transactions_collection = None

# Aliases for backward compatibility
master_col = None
tran_col = None
tran_db = None

try:
    # ------------------ Connect ------------------
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000
    )

    # Test connection
    client.admin.command("ping")
    print(f"✅ MongoDB Connected Successfully → {MONGO_URI}")

    # ------------------ SCHOOL DATABASE ------------------
    school_db = client["school_db"]

    master_collection = school_db["master"]
    counters_collection = school_db["counters"]
    users_collection = school_db["users"]
    students_collection = school_db["students"]
    fees_collection = school_db["fees"]
    transactions_collection = school_db["transactions"]

    # ------------------ Aliases ------------------
    master_col = master_collection
    tran_col = transactions_collection
    tran_db = transactions_collection   # ab tran bhi school_db ke andar hi hai

    # ------------------ Index ------------------
    try:
        transactions_collection.create_index(
            [("adm_code", 1), ("month", 1)],
            unique=True
        )
        print("✅ Transaction index verified")
    except Exception as e:
        print(f"⚠️ Index creation skipped: {e}")

except errors.ServerSelectionTimeoutError as e:
    print(f"❌ MongoDB connection failed: {e}")

except Exception as e:
    print(f"❌ Unexpected MongoDB error: {e}")
