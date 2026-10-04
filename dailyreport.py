from flask import Blueprint, request, render_template_string
from db import tran_collection, get_school
from datetime import datetime, timedelta

dailyreport_bp = Blueprint("dailyreport_bp", __name__)

HEADS = {
    "admission_fee": "Admission",
    "annual_fee": "Annual",
    "tuition_fee": "Tuition",
    "transport_fee": "Transport",
    "devl_fee": "Development",
    "eclass": "E-Class",
    "science": "Science",
    "computer": "Computer",
    "kgarten": "K.Garten"
}

CSS = """
<style>
body{font-family:Segoe UI;margin:0;background:#f5f7fb;color:#222}
.container{max-width:98%;margin:15px auto;background:#fff;padding:15px;border-radius:8px;
box-shadow:0 2px 8px #ddd;overflow:auto}
.school{text-align:center;border-bottom:1px solid #ddd;padding-bottom:8px}
.school h1{margin:0;font-size:22px;color:#2c3e50}
.school p{margin:2px;color:#666;font-size:12px}
h2{font-size:18px;color:#2c3e50}
input{padding:7px;border:1px solid #ccc;border-radius:4px}
button{padding:7px 12px;border:0;border-radius:4px;background:#1abc9c;color:white;
cursor:pointer;margin:2px}
table{border-collapse:collapse;width:100%;margin-top:15px;font-size:12px;white-space:nowrap}
th,td{border:1px solid #ddd;padding:6px;text-align:center}
th{background:#2c3e50;color:#fff}
tr:nth-child(even){background:#fafafa}
.total{font-weight:bold;background:#d8f5d8!important}
.cancel{background:#ffd6d6!important;color:#900;font-weight:bold}
.paid{font-weight:bold}
</style>
"""

LAYOUT = """
<!doctype html><html><head>
<title>Daily Report</title>{{css|safe}}
</head><body><div class="container">{{content|safe}}</div></body></html>
"""


def num(v):
    try:
        return float(v or 0)
    except:
        return 0


def fmt(v):
    v = num(v)
    return str(int(v)) if v == int(v) else f"{v:.2f}"


def header():
    s = get_school() or {}
    return f"""
    <div class="school">
        <h1>🏫 {s.get('school_name', '')}</h1>
        <p>{s.get('address', '')}</p>
        {f"<p>📞 {s.get('phone')}</p>" if s.get('phone') else ""}
    </div>
    """


def head_value(r, key):
    ht = r.get("head_totals") or {}

    if key in ht:
        return num(ht[key])

    aliases = {
        "admission_fee": ["admission", "admission_fee"],
        "annual_fee": ["annual", "annual_fee"],
        "tuition_fee": ["tuition", "tuition_fee"],
        "transport_fee": ["transport", "transport_fee"],
        "devl_fee": ["devl", "development", "development_fee"],
        "eclass": ["eclass", "e_class", "eclass_fee"],
        "science": ["science", "science_fee"],
        "computer": ["computer", "computer_fee"],
        "kgarten": ["kgarten", "k_garten", "kgarten_fee"]
    }

    for k in aliases.get(key, []):
        if k in r:
            return num(r[k])

    return 0


@dailyreport_bp.route("/", methods=["GET", "POST"])
def daily_report():

    hd = header()

    if request.method == "POST":

        date = request.form.get("report_date")
        typ = request.form.get("report_type", "combined")

        try:
            d = datetime.strptime(date, "%Y-%m-%d")

            q = {
                "date": {
                    "$gte": d,
                    "$lt": d + timedelta(days=1)
                }
            }

            if typ == "cash":
                q["payment_mode"] = "Cash"
            elif typ == "online":
                q["payment_mode"] = "Online"

            records = list(
                tran_collection.find(q).sort("date", 1)
            )

        except Exception as e:
            return render_template_string(
                LAYOUT, css=CSS,
                content=hd+f"<h2>Error: {e}</h2>"
            )

        if not records:
            return render_template_string(
                LAYOUT, css=CSS,
                content=hd +
                f"<h2>No {typ.title()} transactions found for {date}</h2>"
            )

        totals = {k: 0 for k in HEADS}
        fee_total = 0
        late_total = 0
        paid_total = 0
        balance_total = 0

        title = {
            "cash": "Cash",
            "online": "Online",
            "combined": "Combined"
        }.get(typ, "Combined")

        cols = [
            "Receipt", "Adm No", "Student",
            "Class", "Sec", "Month"
        ]

        html = hd + f"""
        <h2>📅 {title} Daily Report — {date}</h2>
        <table>
        <tr>
        {''.join(f'<th>{c}</th>' for c in cols)}
        {''.join(f'<th>{v}</th>' for v in HEADS.values())}
        <th>Fee Total</th>
        <th>Late Fee</th>
        <th>Paid</th>
        <th>Balance</th>
        <th>Mode</th>
        </tr>
        """

        for r in records:

            cancelled = str(r.get("status", "")).upper() == "CANCEL"
            cls = "cancel" if cancelled else ""

            row_fee = 0

            html += f"<tr class='{cls}'>"

            html += f"""
            <td>{r.get('receipt_no', '')}</td>
            <td>{r.get('adm_code', '')}</td>
            <td>{r.get('student_name', '')}</td>
            <td>{r.get('class', '')}</td>
            <td>{r.get('section', r.get('sec', ''))}</td>
            <td>{r.get('month', '')}</td>
            """

            for key in HEADS:

                v = head_value(r, key)
                row_fee += v

                html += f"<td>{fmt(v)}</td>"

                if not cancelled:
                    totals[key] += v

            late = num(r.get("late_fee", 0))

            # ONLY PAID AMOUNT
            paid = num(r.get("paid_amount", 0))

            # fallback only for old records
            if "paid_amount" not in r:
                paid = num(r.get("amount_paid", r.get("paid", 0)))

            fee = num(r.get("month_total", row_fee))

            balance = num(
                r.get(
                    "balance_amount",
                    r.get("balance", 0)
                )
            )

            html += f"""
            <td><b>{fmt(fee)}</b></td>
            <td>{fmt(late)}</td>
            <td class="paid">{fmt(paid)}</td>
            <td>{fmt(balance)}</td>
            <td>{r.get('payment_mode', '')}</td>
            </tr>
            """

            if not cancelled:
                fee_total += fee
                late_total += late
                paid_total += paid
                balance_total += balance

        html += f"""
        <tr class="total">
            <td colspan="6">NET TOTAL</td>
            {''.join(
            f'<td>{fmt(totals[k])}</td>'
            for k in HEADS
        )}
            <td>{fmt(fee_total)}</td>
            <td>{fmt(late_total)}</td>
            <td>{fmt(paid_total)}</td>
            <td>{fmt(balance_total)}</td>
            <td>-</td>
        </tr>
        </table>
        """

        return render_template_string(
            LAYOUT,
            css=CSS,
            content=html
        )

    form = hd + """
    <h2>📅 Datewise Daily Report</h2>

    <form method="POST">
        <label><b>Date:</b></label>
        <input type="date" name="report_date" required>

        <button name="report_type" value="cash">Cash</button>
        <button name="report_type" value="online">Online</button>
        <button name="report_type" value="combined">Combined</button>
    </form>
    """

    return render_template_string(
        LAYOUT,
        css=CSS,
        content=form
    )
