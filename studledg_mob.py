from flask import Blueprint, request, render_template, render_template_string
from bson.objectid import ObjectId
from db import master_collection, tran_collection, get_school

studledg_mob_bp = Blueprint("studledg_mob_bp", __name__)

base_layout = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student Ledger</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:12px;font-family:Segoe UI,Arial,sans-serif;background:#f5f7fb;color:#263238}
.container{max-width:1000px;margin:10px auto;background:#fff;padding:18px;border-radius:14px;box-shadow:0 4px 15px #0001}
.school{text-align:center;margin-bottom:15px}
.school h1{margin:0;color:#3949ab;font-size:21px}
.school p{margin:3px;color:#78909c;font-size:12px}
.header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:15px;flex-wrap:wrap}
.title{font-size:22px;font-weight:700}
.sub{font-size:12px;color:#78909c}
.adm{background:#eef2ff;color:#3949ab;padding:9px 13px;border-radius:9px;font-size:13px}
.summary{display:flex;gap:8px;margin:12px 0;flex-wrap:wrap}
.card{flex:1;min-width:120px;background:#f8f9ff;padding:10px;border-radius:9px}
.label{font-size:11px;color:#78909c}
.value{font-size:17px;font-weight:700;color:#3949ab}
.table-wrap{overflow-x:auto}
table{width:100%;min-width:700px;border-collapse:collapse}
th{background:#3949ab;color:white;padding:10px;font-size:12px}
td{padding:9px;text-align:center;border-bottom:1px solid #eee;font-size:12px}
tr:nth-child(even){background:#fafafa}
.print{background:#3498db;color:white;padding:6px 10px;border-radius:6px;text-decoration:none;font-size:11px}
.no-record{background:#fff8e1;padding:15px;border-radius:9px;text-align:center}
.error{background:#ffebee;color:#c62828;padding:15px;border-radius:9px;text-align:center}
@media(max-width:600px){
.container{padding:12px}.title{font-size:19px}.adm{width:100%}
}
</style>
</head>
<body>
<div class="container">{{ content|safe }}</div>
</body>
</html>
"""


def num(value):
    try:
        return float(value or 0)
    except:
        return 0.0


@studledg_mob_bp.route("/studledg_mob", methods=["GET", "POST"])
def ledger_home():

    adm_code = request.args.get("adm_code", "").strip().upper()

    if request.method == "POST":
        adm_code = request.form.get("admission_no", "").strip().upper()

    school = get_school() or {}
    school_name = school.get("school_name", "")
    address = school.get("address", "")
    phone = school.get("phone", "")

    school_header = f"""
    <div class="school">
        <h1>🏫 {school_name}</h1>
        <p>{address}{(" | 📞 " + phone) if phone else ""}</p>
    </div>
    """

    if not adm_code:
        return render_template_string(
            base_layout,
            content=school_header + """
            <div class="header">
                <div>
                    <div class="title">📒 Student Ledger</div>
                    <div class="sub">Fee transaction history</div>
                </div>
            </div>
            <div class="error">
                Admission Code is required.<br>
                Please open Student Ledger from the School App.
            </div>
            """
        )

    try:
        records = list(
            tran_collection.find(
                {"adm_code": adm_code}
            ).sort("date", 1)
        )
    except Exception as e:
        return render_template_string(
            base_layout,
            content=school_header + f"""
            <div class="error">
                Unable to load ledger.<br>{str(e)}
            </div>
            """
        )

    if not records:
        return render_template_string(
            base_layout,
            content=school_header + f"""
            <div class="header">
                <div>
                    <div class="title">📒 Student Ledger</div>
                    <div class="sub">Fee transaction history</div>
                </div>
                <div class="adm">
                    Admission No: <strong>{adm_code}</strong>
                </div>
            </div>
            <div class="no-record">
                No ledger records found for <strong>{adm_code}</strong>
            </div>
            """
        )

    total_paid = sum(num(r.get("paid")) for r in records)

    latest = records[-1]
    total_balance = num(latest.get("balance", 0))

    rows = ""

    for r in records:

        month_total = num(
            r.get(
                "month_total",
                r.get("total_fee", 0)
            )
        )

        paid = num(r.get("paid"))
        balance = num(r.get("balance"))

        rows += f"""
        <tr>
            <td>{r.get('receipt_no', '')}</td>
            <td>{r.get('month', '')}</td>
            <td>{r.get('date', '')}</td>
            <td>₹{month_total:,.2f}</td>
            <td>₹{paid:,.2f}</td>
            <td>₹{balance:,.2f}</td>
            <td>
                <a class="print"
                   href="/studledg_mob/print/{r.get('_id')}"
                   target="_blank">🖨️ Print</a>
            </td>
        </tr>
        """

    content = f"""
    {school_header}

    <div class="header">
        <div>
            <div class="title">📒 Student Ledger</div>
            <div class="sub">Fee transaction history</div>
        </div>

        <div class="adm">
            Admission No: <strong>{adm_code}</strong>
        </div>
    </div>

    <div class="summary">

        <div class="card">
            <div class="label">Transactions</div>
            <div class="value">{len(records)}</div>
        </div>

        <div class="card">
            <div class="label">Total Paid</div>
            <div class="value">₹{total_paid:,.2f}</div>
        </div>

        <div class="card">
            <div class="label">Current Balance</div>
            <div class="value">₹{total_balance:,.2f}</div>
        </div>

    </div>

    <div class="table-wrap">
    <table>
        <tr>
            <th>Receipt</th>
            <th>Month</th>
            <th>Date</th>
            <th>Monthly Fee</th>
            <th>Paid</th>
            <th>Balance</th>
            <th>Action</th>
        </tr>
        {rows}
    </table>
    </div>
    """

    return render_template_string(
        base_layout,
        content=content
    )


@studledg_mob_bp.route("/studledg_mob/print/<tran_id>")
def print_transaction(tran_id):

    try:
        record = tran_collection.find_one({
            "_id": ObjectId(tran_id)
        })
    except Exception:
        return "<h2>Invalid transaction ID</h2>"

    if not record:
        return "<h2>Transaction not found</h2>"

    student = master_collection.find_one({
        "adm_code": record.get("adm_code", "")
    }) or {}

    school = get_school() or {}

    def fee(name, default=0, divisor=None):

        value = record.get(name)

        if value is not None:
            return value

        value = student.get(name, default) or default

        if divisor:
            return round(num(value) / divisor, 2)

        return value

    return render_template(
        "receipt.html",

        school_name=school.get("school_name", ""),
        school_address=school.get("address", ""),
        school_phone=school.get("phone", ""),

        receipt_no=record.get("receipt_no", ""),
        adm_code=record.get("adm_code", ""),

        student_name=record.get(
            "student_name",
            student.get("student_name", "")
        ),

        student_class=record.get(
            "student_class",
            student.get("class", "")
        ),

        section=record.get(
            "section",
            student.get("sec", "")
        ),

        father_name=record.get(
            "father_name",
            student.get("father_name", "")
        ),

        date=record.get("date", ""),
        month=record.get("month", ""),

        payment_mode=record.get(
            "payment_mode",
            record.get("mode", "Cash")
        ),

        remark=record.get("remark", ""),

        paid=record.get("paid", 0),
        balance=record.get("balance", 0),

        admission_fee=record.get("admission_fee", 0),
        annual_fee=record.get("annual_fee", 0),

        tuition_fee=fee("tuition_fee"),

        transport_fee=fee(
            "transport_fee",
            num(student.get("transport_total", 0)) / 12
        ),

        devl_fee=fee(
            "devl_fee",
            num(student.get("devl_fee", 0)) / 12
        ),

        eclass=fee(
            "eclass",
            num(student.get("eclass", 0)) / 12
        ),

        science=fee(
            "science",
            num(student.get("science", 0)) / 12
        ),

        computer=fee(
            "computer",
            num(student.get("computer", 0)) / 12
        ),

        kgarten=fee(
            "kgarten",
            num(student.get("kgarten", 0)) / 12
        )
    )
