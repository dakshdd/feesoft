import os
from pymongo import MongoClient, errors

# ------------------ MongoDB URI ------------------
# Prefer environment variable (Render/Deployment), fallback to localhost
LOCAL_URI = "mongodb://localhost:27017/"
ATLAS_URI = "mongodb+srv://dakshdd_db_user:Dhanjal01@cluster0.luwfblh.mongodb.net/school_db?retryWrites=true&w=majority"

MONGO_URI = os.getenv("MONGO_URI", LOCAL_URI)

# ------------------ Default Collections ------------------
master_collection = None
counters_collection = None
users_collection = None
students_collection = None
transport_collection = None
tran_collection = None

# Aliases for backward compatibility
tran_col = None
master_col = None

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

    # ------------------ TRANSPORT DATABASE ------------------
    transport_db = client["transport_db"]
    transport_collection = transport_db["stand_name"]

    # ------------------ TRANSACTION DATABASE ------------------
    tran_db = client["tran"]
    tran_collection = tran_db["transactions"]

    # ------------------ Aliases ------------------
    tran_col = tran_collection
    master_col = master_collection

    # Backward compatibility
    master = master_collection
    counters = counters_collection
    transport = transport_collection
    tran = tran_collection

    # ------------------ Index ------------------
    try:
        tran_collection.create_index(
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
