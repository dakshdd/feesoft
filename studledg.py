from flask import Blueprint, request, render_template, render_template_string, url_for
from bson.objectid import ObjectId
from db import master_collection, tran_collection, get_school

studledg_bp = Blueprint("studledg_bp", __name__)

LAYOUT = """
<!doctype html><html><head><title>Student Ledger</title>
<style>
body{font-family:Segoe UI;margin:0;background:#f5f7fb}
.container{max-width:95%;margin:20px auto;background:#fff;padding:18px;border-radius:8px;
box-shadow:0 2px 8px #ddd;overflow:auto}
.school{text-align:center;border-bottom:1px solid #ddd;padding-bottom:8px}
.school h1{margin:0;color:#2c3e50;font-size:22px}
.school p{margin:2px;color:#666;font-size:12px}
h2{color:#2c3e50;font-size:18px}
input{padding:8px;width:220px;border:1px solid #ccc;border-radius:4px}
button,.print{padding:7px 12px;border:0;border-radius:4px;background:#1abc9c;
color:#fff;text-decoration:none;cursor:pointer}
table{border-collapse:collapse;width:100%;margin-top:15px;font-size:12px;white-space:nowrap}
th,td{border:1px solid #ddd;padding:6px;text-align:center}
th{background:#2c3e50;color:#fff}
tr:nth-child(even){background:#fafafa}
.print{background:#3498db}
.total{font-weight:bold;background:#d8f5d8!important}
</style></head><body><div class="container">{{content|safe}}</div></body></html>
"""

HEADS = [
    ("admission_fee", "Admission"),
    ("annual_fee", "Annual"),
    ("tuition_fee", "Tuition"),
    ("transport_fee", "Transport"),
    ("devl_fee", "Development"),
    ("eclass", "E-Class"),
    ("science", "Science"),
    ("computer", "Computer"),
    ("kgarten", "K.Garten")
]


def num(v):
    try:
        return float(v or 0)
    except:
        return 0


def fmt(v):
    v = num(v)
    return str(int(v)) if v == int(v) else f"{v:.2f}"


def school_header():
    s = get_school() or {}
    return f"""
    <div class="school">
        <h1>🏫 {s.get('school_name', '')}</h1>
        <p>{s.get('address', '')}</p>
        {f"<p>📞 {s.get('phone')}</p>" if s.get('phone') else ""}
    </div>
    """


def payment_values(r):
    paid = num(r.get("amount_paid",
                     r.get("paid_amount",
                           r.get("paid", 0))))

    balance = num(r.get("balance_amount",
                        r.get("balance", 0)))

    late = num(r.get("late_fee",
                     r.get("auto_late_fee", 0)))

    return paid, balance, late


def head_values(r):
    ht = r.get("head_totals") or {}
    return {
        k: num(ht.get(k, r.get(k, 0)))
        for k, _ in HEADS
    }


@studledg_bp.route("/", methods=["GET", "POST"])
def ledger_home():

    header = school_header()

    if request.method == "POST":

        adm = request.form.get("admission_no", "").strip()

        records = list(
            tran_collection.find({"adm_code": adm}).sort("date", 1)
        )

        if not records:
            return render_template_string(
                LAYOUT,
                content=header + f"<h2>No ledger found for {adm}</h2>"
            )

        first = records[0]

        html = header + f"""
        <h2>📒 Student Ledger — {adm}</h2>
        <b>Student:</b> {first.get('student_name', '')}
        &nbsp; | &nbsp;
        <b>Class:</b> {first.get('class', first.get('student_class', ''))}
        &nbsp; | &nbsp;
        <b>Section:</b> {first.get('section', '')}

        <table><tr>
        <th>Receipt</th><th>Month</th><th>Date</th>
        <th>Fee Total</th><th>Late Fee</th><th>Paid</th>
        <th>Balance</th><th>Mode</th><th>Print</th>
        </tr>
        """

        fee_t = late_t = paid_t = 0

        for r in records:

            fee = num(r.get("month_total", r.get("total_fee", 0)))
            paid, balance, late = payment_values(r)

            fee_t += fee
            late_t += late
            paid_t += paid

            dt = r.get("date", "")
            if hasattr(dt, "strftime"):
                dt = dt.strftime("%d-%m-%Y %I:%M %p")

            purl = url_for(
                "studledg_bp.print_transaction",
                tran_id=str(r["_id"])
            )

            html += f"""
            <tr>
            <td>{r.get('receipt_no', '')}</td>
            <td>{r.get('month') or r.get('months') or r.get('selected_month') or r.get('selected_months') or ''}</td>
            <td>{dt}</td>
            <td>{fmt(fee)}</td>
            <td>{fmt(late)}</td>
            <td><b>{fmt(paid)}</b></td>
            <td>{fmt(balance)}</td>
            <td>{r.get('payment_mode', r.get('mode', ''))}</td>
            <td><a class="print" href="{purl}" target="_blank">🖨️ Print</a></td>
            </tr>
            """

        html += f"""
        <tr class="total">
        <td colspan="3">TOTAL</td>
        <td>{fmt(fee_t)}</td>
        <td>{fmt(late_t)}</td>
        <td>{fmt(paid_t)}</td>
        <td>-</td><td>-</td><td>-</td>
        </tr></table>
        """

        return render_template_string(LAYOUT, content=html)

    return render_template_string(
        LAYOUT,
        content=school_header() + """
        <h2>📒 Student Ledger</h2>
        <form method="POST">
        <b>Admission No:</b>
        <input name="admission_no" placeholder="ADM-0123" required>
        <button>Show Ledger</button>
        </form>
        """
    )


@studledg_bp.route("/print/<tran_id>")
def print_transaction(tran_id):

    try:
        r = tran_collection.find_one({"_id": ObjectId(tran_id)})
    except:
        return "<h2>Invalid transaction ID</h2>"

    if not r:
        return "<h2>Transaction not found</h2>"

    s = get_school() or {}

    student = master_collection.find_one({
        "adm_code": r.get("adm_code", "")
    }) or {}

    heads = head_values(r)
    paid, balance, late = payment_values(r)

    fee_total = num(
        r.get(
            "month_total",
            sum(heads.values())
        )
    )

    dt = r.get("date", "")
    if hasattr(dt, "strftime"):
        dt = dt.strftime("%d-%m-%Y %I:%M %p")

    return render_template(
        "receipt.html",

        # SCHOOL
        school_name=s.get("school_name", ""),
        school_address=s.get("address", ""),
        school_phone=s.get("phone", ""),

        # STUDENT
        receipt_no=r.get("receipt_no", ""),
        adm_code=r.get("adm_code", ""),
        student_name=r.get(
            "student_name",
            student.get("student_name", "")
        ),
        student_class=r.get(
            "class",
            r.get("student_class", student.get("class", ""))
        ),
        section=r.get(
            "section",
            student.get("sec", student.get("section", ""))
        ),
        father_name=r.get(
            "father_name",
            student.get("father_name", "")
        ),

        # PAYMENT
        date=dt,
        month=r.get("month", ""),
        payment_mode=r.get(
            "payment_mode",
            r.get("mode", "Cash")
        ),
        remark=r.get("remark", ""),

        # TOTALS - ALL COMPATIBLE NAMES
        paid=paid,
        paid_amount=paid,
        amount_paid=paid,
        balance=balance,
        balance_amount=balance,
        month_total=fee_total,
        total_fee=fee_total,

        # LATE FEE
        late_fee=late,
        auto_late_fee=num(r.get("auto_late_fee", 0)),

        # COMPLETE HEADS
        head_totals=heads,
        admission_fee=heads["admission_fee"],
        annual_fee=heads["annual_fee"],
        tuition_fee=heads["tuition_fee"],
        transport_fee=heads["transport_fee"],
        devl_fee=heads["devl_fee"],
        eclass=heads["eclass"],
        science=heads["science"],
        computer=heads["computer"],
        kgarten=heads["kgarten"],
    )
