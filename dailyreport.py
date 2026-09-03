import os
from flask import Blueprint, request, render_template_string
from pymongo import MongoClient
from datetime import datetime, timedelta

# ------------------ Blueprint Setup ------------------
dailyreport_bp = Blueprint("dailyreport_bp", __name__)

# ------------------ MongoDB Connection ------------------
MONGO_URI = os.environ.get("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["tran"]   # database name
tran_collection = db["transactions"]   # collection name
# ------------------ Base Layout ------------------
base_layout = """
<!DOCTYPE html>
<html>
<head>
    <title>Datewise Daily Report</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; margin:0; background:#0000ff00; }
        .container { max-width:95%; margin:20px auto; background:white; padding:20px; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.1); }
        h2 { color:#2c3e50; margin-bottom:20px; }
        form { margin-bottom:20px; }
        input[type=date] { padding:8px; border:1px solid #ccc; border-radius:5px; }
        button { padding:8px 15px; background:#1abc9c; color:white; border:none; border-radius:5px; cursor:pointer; margin-right:5px; }
        button:hover { background:#16a085; }
        table { border-collapse: collapse; width: 100%; margin-top:20px; font-size:14px; }
        th, td { border:1px solid #ddd; padding:8px; text-align:center; }
        th { background:#2c3e50; color:white; }
        tr:nth-child(even) { background:#f9f9f9; }
        tr:hover { background:#eafaf9; }
        .total-row { font-weight:bold; background:#d1f7d1; }
        .cancelled { background:#ffcccc; color:#900; font-weight:bold; }
    </style>
</head>
<body>
    <div class="container">
        {{ content|safe }}
    </div>
</body>
</html>
"""

# ------------------ Utility ------------------


def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0

# ------------------ Routes ------------------


@dailyreport_bp.route("/", methods=["GET", "POST"])
def daily_report():
    if request.method == "POST":
        report_date = request.form.get("report_date")
        report_type = request.form.get("report_type")

        try:
            start = datetime.strptime(report_date, "%Y-%m-%d")
            end = start + timedelta(days=1)

            query = {"date": {"$gte": start, "$lt": end}}
            if report_type == "cash":
                query["payment_mode"] = "Cash"
            elif report_type == "online":
                query["payment_mode"] = "Online"

            records = list(tran_collection.find(query).sort("date", 1))

        except Exception as e:
            return render_template_string(base_layout,
                                          content=f"<h2>Error: {str(e)}</h2>")

        if not records:
            return render_template_string(base_layout,
                                          content=f"<h2>No {report_type} transactions found for {report_date}</h2>")

        # ✅ Collect numeric heads dynamically
        fee_heads = set()
        for r in records:
            for k, v in r.items():
                if k not in ["_id", "receipt_no", "payment_id", "adm_code",
                             "student_name", "class", "section", "month",
                             "paid", "balance", "payment_mode", "date", "status"]:
                    if isinstance(v, (int, float)):
                        fee_heads.add(k)
        fee_heads = sorted(fee_heads)

        # ✅ Table header
        table_html = f"<h2>{report_type.capitalize()} Report for {report_date}</h2><table>"
        table_html += "<tr><th>Receipt No</th><th>Adm No</th><th>Name</th><th>Class</th><th>Section</th>"
        for h in fee_heads:
            table_html += f"<th>{h.replace('_', ' ').title()}</th>"
        table_html += "<th>Total</th><th>Paid</th><th>Balance/Advance</th></tr>"

        # ✅ Totals accumulator
        totals = {h: 0 for h in fee_heads}
        grand_total = paid_total = balance_total = 0

        # ✅ Each receipt row
        for r in records:
            row_total = sum(safe_int(r.get(h, 0)) for h in fee_heads)
            paid_val = safe_int(r.get("paid", 0))
            balance_val = safe_int(r.get("balance", 0))

            # cancelled highlight
            row_class = "cancelled" if str(
                r.get("status")).upper() == "CANCEL" else ""

            table_html += f"<tr class='{row_class}'><td>{r.get('receipt_no')}</td><td>{r.get('adm_code')}</td><td>{r.get('student_name')}</td><td>{r.get('class')}</td><td>{r.get('section')}</td>"
            for h in fee_heads:
                val = safe_int(r.get(h, 0))
                table_html += f"<td>{val}</td>"
                totals[h] += val
            table_html += f"<td>{row_total}</td><td>{paid_val}</td><td>{balance_val}</td></tr>"

            grand_total += row_total
            paid_total += paid_val
            balance_total += balance_val

        # ✅ Net Total row
        table_html += "<tr class='total-row'><td colspan='5'>NET TOTAL</td>"
        for h in fee_heads:
            table_html += f"<td>{totals[h]}</td>"
        table_html += f"<td>{grand_total}</td><td>{paid_total}</td><td>{balance_total}</td></tr>"
        table_html += "</table>"

        return render_template_string(base_layout, content=table_html)

    # Form with 3 buttons
    form_html = """
        <h2>📅 Datewise Daily Report</h2>
        <form method="POST">
            <label>Select Date:</label>
            <input type="date" name="report_date" required>
            <button type="submit" name="report_type" value="cash">Cash Report</button>
            <button type="submit" name="report_type" value="online">Online Report</button>
            <button type="submit" name="report_type" value="combined">Combined Report</button>
        </form>
    """
    return render_template_string(base_layout, content=form_html)
