import os
from flask import Blueprint, request, render_template_string
from pymongo import MongoClient

# ------------------ Blueprint Setup ------------------
transport_bp = Blueprint("transport_bp", __name__)

# ✅ MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client["transport_db"]
stand_collection = db["stand_name"]
# ------------------ HTML Template ------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Transport Module</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; background:#f4f6f9; margin:0; padding:0; }
        .container { width:60%; margin:40px auto; background:white; padding:30px; border-radius:8px; 
                     box-shadow:0 4px 10px rgba(0,0,0,0.1); }
        h2 { color:#2c3e50; margin-bottom:20px; }
        form { margin-bottom:30px; }
        label { display:inline-block; width:120px; font-weight:bold; }
        input { width:200px; padding:6px; border:1px solid #ccc; border-radius:4px; font-size:14px; }
        button { margin-top:15px; padding:8px 16px; background:#1abc9c; color:white; border:none; 
                 border-radius:4px; cursor:pointer; font-size:14px; }
        button:hover { background:#16a085; }
        table { width:100%; border-collapse:collapse; margin-top:20px; }
        th, td { padding:10px; text-align:left; border-bottom:1px solid #ddd; font-size:14px; }
        th { background:#34495e; color:white; }
        tr:hover { background:#f1f1f1; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚍 Transport Management</h2>
        <form method="POST">
            <label>Stand Name:</label>
            <input type="text" name="stand" required><br><br>
            <label>Charges:</label>
            <input type="number" name="charges" required><br><br>
            <button type="submit">➕ Add Transport</button>
        </form>

        <h3>📋 All Transport Records</h3>
        <table>
            <tr><th>Stand</th><th>Charges</th></tr>
            {% for rec in records %}
            <tr>
                <td>{{ rec.stand }}</td>
                <td>{{ rec.charges }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

# ------------------ Routes ------------------


@transport_bp.route("/", methods=["GET", "POST"])
def transport_home():
    if request.method == "POST":
        stand = request.form.get("stand")
        charges = request.form.get("charges")
        if stand and charges:
            stand_collection.insert_one(
                {"stand": stand, "charges": int(charges)})

    records = list(stand_collection.find({}, {"_id": 0}))
    return render_template_string(HTML_TEMPLATE, records=records)
