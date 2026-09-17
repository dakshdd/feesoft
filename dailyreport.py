from flask import Blueprint, request, render_template_string
from datetime import datetime, timedelta
from db import tran_collection

dailyreport_bp = Blueprint("dailyreport_bp", __name__)

layout = """<!DOCTYPE html><html><head><title>Daily Report</title><style>
body{font-family:"Segoe UI";margin:0}.container{max-width:98%;margin:20px auto;background:#fff;padding:20px;border-radius:10px;box-shadow:0 4px 10px #ddd;overflow-x:auto}
h2{color:#2c3e50}input{padding:8px;border:1px solid #ccc;border-radius:5px}button{padding:8px 15px;background:#1abc9c;color:#fff;border:0;border-radius:5px;cursor:pointer;margin:3px}
table{border-collapse:collapse;width:100%;margin-top:20px;font-size:14px;white-space:nowrap}th,td{border:1px solid #ddd;padding:8px;text-align:center}th{background:#2c3e50;color:#fff}
tr:nth-child(even){background:#f9f9f9}.total-row{font-weight:bold;background:#d1f7d1!important}.cancelled{background:#ffcccc!important;color:#900;font-weight:bold}.month-total{font-weight:bold}
</style></head><body><div class="container">{{content|safe}}</div></body></html>"""


def safe_int(v):
    try:
        return int(float(v or 0))
    except:
        return 0


@dailyreport_bp.route("/", methods=["GET", "POST"])
def daily_report():
    if request.method == "POST":
        date = request.form.get("report_date")
        typ = request.form.get("report_type", "combined")

        try:
            start = datetime.strptime(date, "%Y-%m-%d")
            q = {"date": {"$gte": start, "$lt": start+timedelta(days=1)}}
            if typ in ("cash", "online"):
                q["payment_mode"] = typ.title()
            records = list(tran_collection.find(q).sort("date", 1))
        except Exception as e:
            return render_template_string(layout, content=f"<h2>Error: {e}</h2>")

        if not records:
            return render_template_string(layout, content=f"<h2>No {typ} transactions found for {date}</h2>")

        exclude = {
            "_id", "receipt_no", "payment_id", "adm_code", "student_name",
            "class", "section", "month", "paid", "balance", "payment_mode",
            "date", "status", "total", "month_total", "month total"
        }

        heads = set()

        for r in records:
            for k, v in r.items():
                key = str(k).lower().replace("_", " ").strip()

                # Remove calculated/non-fee fields
                if k in exclude or key in {
                    "total", "month total", "grand total",
                    "paid", "balance", "balance advance"
                }:
                    continue

                try:
                    float(v)
                    heads.add(k)
                except:
                    pass

        heads = sorted(heads)

        name = {"cash": "Cash", "online": "Online",
                "combined": "Combined"}.get(typ, "Combined")

        html = f"<h2>{name} Report for {date}</h2><table><tr>"
        html += "<th>Receipt No</th><th>Adm No</th><th>Name</th><th>Class</th><th>Section</th>"
        html += "".join(f"<th>{h.replace('_', ' ').title()}</th>" for h in heads)
        html += "<th>Month Total</th></tr>"

        totals = {h: 0 for h in heads}
        grand = 0

        for r in records:
            mt = sum(safe_int(r.get(h)) for h in heads)
            cls = "cancelled" if str(
                r.get("status", "")).upper() == "CANCEL" else ""

            html += f"<tr class='{cls}'>"
            html += f"<td>{r.get('receipt_no', '')}</td>"
            html += f"<td>{r.get('adm_code', '')}</td>"
            html += f"<td>{r.get('student_name', '')}</td>"
            html += f"<td>{r.get('class', '')}</td>"
            html += f"<td>{r.get('section', '')}</td>"

            for h in heads:
                v = safe_int(r.get(h))
                html += f"<td>{v}</td>"
                totals[h] += v

            html += f"<td class='month-total'>{mt}</td></tr>"
            grand += mt

        html += "<tr class='total-row'><td colspan='5'>NET TOTAL</td>"
        html += "".join(f"<td>{totals[h]}</td>" for h in heads)
        html += f"<td>{grand}</td></tr></table>"

        return render_template_string(layout, content=html)

    form = """<h2>📅 Datewise Daily Report</h2>
    <form method="POST">
    <label>Select Date:</label>
    <input type="date" name="report_date" required>
    <button name="report_type" value="cash">Cash Report</button>
    <button name="report_type" value="online">Online Report</button>
    <button name="report_type" value="combined">Combined Report</button>
    </form>"""

    return render_template_string(layout, content=form)
