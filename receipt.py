import os
from flask import Blueprint, request, render_template, render_template_string
from pymongo import MongoClient
from bson.objectid import ObjectId
from markupsafe import escape

# ------------------ Blueprint Setup ------------------
receipt_bp = Blueprint("receipt_bp", __name__)

# ------------------ MongoDB Connection ------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

client = MongoClient(MONGO_URI)
db = client["tran"]   # database name
tran_collection = db["transactions"]   # collection name

# ------------------ Base Layout ------------------
base_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>Re-Print Receipts</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; margin:0; background:#f4f6f9; }
        .container { max-width:900px; margin:40px auto; background:white; padding:30px; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.1); }
        h2 { color:#2c3e50; margin-bottom:20px; }
        form { margin-bottom:20px; }
        input[type=text] { padding:10px; width:250px; border:1px solid #ccc; border-radius:5px; }
        button { padding:10px 20px; background:#1abc9c; color:white; border:none; border-radius:5px; cursor:pointer; }
        button:hover { background:#16a085; }
        table { border-collapse: collapse; width: 100%; margin-top:20px; }
        th, td { border:1px solid #ddd; padding:12px; text-align:center; }
        th { background:#2c3e50; color:white; }
        tr:nth-child(even) { background:#f9f9f9; }
        tr:hover { background:#eafaf9; }
        a.print-btn { background:#3498db; color:white; padding:6px 12px; border-radius:5px; text-decoration:none; }
        a.print-btn:hover { background:#2980b9; }
    </style>
</head>
<body>
    <div class="container">
        {{ content|safe }}
    </div>
</body>
</html>
"""

# ------------------ Routes ------------------

# ✅ Home route with Receipt No search box


@receipt_bp.route("/home", methods=["GET", "POST"])
def receipt_home():
    if request.method == "POST":
        receipt_no = escape(request.form.get("receipt_no"))
        receipt = tran_collection.find_one({"receipt_no": receipt_no})

        if not receipt:
            return render_template_string(base_layout,
                                          content=f"<h2>No receipt found for Receipt No: {receipt_no}</h2>")

        # ✅ Use existing receipt.html template with safe defaults
        return render_template("receipt.html", **receipt)

    form_html = """
        <h2>🔎 Re-Print by Receipt No</h2>
        <form method="POST">
            <label>Receipt Number:</label>
            <input type="text" name="receipt_no" placeholder="e.g. REC-00001" required>
            <button type="submit">Search & Print</button>
        </form>
    """
    return render_template_string(base_layout, content=form_html)


# ✅ Search by Admission No
@receipt_bp.route("/", methods=["GET", "POST"])
def receipts_home():
    if request.method == "POST":
        adm_code = escape(request.form.get("admission_no"))
        receipts = list(tran_collection.find({"adm_code": adm_code}))

        if not receipts:
            return render_template_string(base_layout,
                                          content=f"<h2>No receipts found for Admission No: {adm_code}</h2>")

        table_html = f"<h2>Receipts for Admission No: {adm_code}</h2><table>"
        table_html += "<tr><th>ID</th><th>Month</th><th>Date</th><th>Paid</th><th>Balance</th><th>Action</th></tr>"
        for r in receipts:
            table_html += f"<tr><td>{str(r.get('_id'))[:6]}</td><td>{r.get('month')}</td><td>{r.get('date')}</td><td>{r.get('paid')}</td><td>{r.get('balance')}</td>"
            table_html += f"<td><a class='print-btn' href='/receipts/print/{r.get('_id')}' target='_blank'>🖨️ Print</a></td></tr>"
        table_html += "</table>"

        return render_template_string(base_layout, content=table_html)

    form_html = """
        <h2>🔎 Re-Print by Admission No</h2>
        <form method="POST">
            <label>Admission Number:</label>
            <input type="text" name="admission_no" placeholder="e.g. ADM-0019" required>
            <button type="submit">Search</button>
        </form>
    """
    return render_template_string(base_layout, content=form_html)


# ✅ Print by ObjectId
@receipt_bp.route("/print/<receipt_id>")
def print_receipt(receipt_id):
    try:
        receipt = tran_collection.find_one({"_id": ObjectId(receipt_id)})
    except Exception:
        return "<h2>Invalid receipt ID format</h2>"

    if not receipt:
        return "<h2>Receipt not found</h2>"

    # ✅ Use same receipt.html template with safe defaults
    return render_template("receipt.html", **receipt)
