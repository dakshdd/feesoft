# studledg_mob.py

import os
from flask import Blueprint, request, render_template, render_template_string
from pymongo import MongoClient
from bson.objectid import ObjectId
from db import master_collection

# studledg_bp = Blueprint("studledg_bp", __name__)
studledg_mob_bp = Blueprint("studledg_mob_bp", __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
tran_collection = client["tran"]["transactions"]


# ---------------------------------------------------------
# Common Layout
# ---------------------------------------------------------

base_layout = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student Ledger</title>
<style>
*{box-sizing:border-box}
body{
    margin:0;padding:12px;
    font-family:Segoe UI,Arial,sans-serif;
    background:#f5f7fb;color:#263238
}
.container{
    max-width:1000px;margin:10px auto;
    background:#fff;padding:18px;
    border-radius:14px;
    box-shadow:0 4px 15px rgba(0,0,0,.08)
}
.header{
    display:flex;justify-content:space-between;
    align-items:center;gap:10px;
    margin-bottom:15px;flex-wrap:wrap
}
.title{font-size:22px;font-weight:700}
.sub{font-size:12px;color:#78909c}
.adm{
    background:#eef2ff;color:#3949ab;
    padding:9px 13px;border-radius:9px;
    font-size:13px
}
.summary{
    display:flex;gap:8px;
    margin:12px 0;flex-wrap:wrap
}
.card{
    flex:1;min-width:120px;
    background:#f8f9ff;
    padding:10px;border-radius:9px
}
.label{font-size:11px;color:#78909c}
.value{font-size:17px;font-weight:700;color:#3949ab}
.table-wrap{overflow-x:auto}
table{
    width:100%;min-width:700px;
    border-collapse:collapse
}
th{
    background:#3949ab;color:white;
    padding:10px;font-size:12px
}
td{
    padding:9px;text-align:center;
    border-bottom:1px solid #eee;
    font-size:12px
}
tr:nth-child(even){background:#fafafa}
.print{
    background:#3498db;color:white;
    padding:6px 10px;border-radius:6px;
    text-decoration:none;font-size:11px
}
.no-record{
    background:#fff8e1;
    padding:15px;border-radius:9px;
    text-align:center
}
.error{
    background:#ffebee;color:#c62828;
    padding:15px;border-radius:9px;
    text-align:center
}
@media(max-width:600px){
    .container{padding:12px}
    .title{font-size:19px}
    .adm{width:100%}
}
</style>
</head>
<body>
<div class="container">
{{ content|safe }}
</div>
</body>
</html>
"""


# ---------------------------------------------------------
# Ledger
# ---------------------------------------------------------

# @studledg_bp.route("/", methods=["GET", "POST"])
@studledg_mob_bp.route("/studledg_mob", methods=["GET", "POST"])
def ledger_home():

    adm_code = request.args.get("adm_code", "").strip()

    if request.method == "POST":
        adm_code = request.form.get("admission_no", "").strip()

    if not adm_code:
        return render_template_string(
            base_layout,
            content="""
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

    records = list(
        tran_collection.find({"adm_code": adm_code}).sort("date", 1)
    )

    if not records:
        return render_template_string(
            base_layout,
            content=f"""
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

    total_paid = sum(
        float(r.get("paid", 0) or 0)
        for r in records
        if str(r.get("paid", 0) or 0).replace(".", "", 1).isdigit()
    )

    total_balance = sum(
        float(r.get("balance", 0) or 0)
        for r in records
        if str(r.get("balance", 0) or 0).replace(".", "", 1).isdigit()
    )

    rows = ""

    for r in records:
        rows += f"""
        <tr>
            <td>{r.get('receipt_no', '')}</td>
            <td>{r.get('month', '')}</td>
            <td>{r.get('date', '')}</td>
            <td>₹{r.get('total_fee', 0)}</td>
            <td>₹{r.get('paid', 0)}</td>
            <td>₹{r.get('balance', 0)}</td>
            <td>
                <a class="print"
                   href="/studledg_mob/print/{r.get('_id')}"
                   target="_blank">
                   🖨️ Print
                </a>
            </td>
        </tr>
        """

    content = f"""
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
            <div class="label">Balance</div>
            <div class="value">₹{total_balance:,.2f}</div>
        </div>

    </div>

    <div class="table-wrap">
    <table>
        <tr>
            <th>Receipt</th>
            <th>Month</th>
            <th>Date</th>
            <th>Total Fee</th>
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


# ---------------------------------------------------------
# Print Receipt
# ---------------------------------------------------------

# @studledg_bp.route("/print/<tran_id>")
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

    def fee(name, default=0, divisor=None):
        value = record.get(name)

        if value is not None:
            return value

        value = student.get(name, default) or default

        if divisor:
            return round(float(value) / divisor, 2)

        return value

    return render_template(
        "receipt.html",

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
            student.get("section", "")
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
            round(float(student.get("transport_total", 0) or 0) / 10.5, 2)
        ),

        devl_fee=fee(
            "devl_fee",
            round(float(student.get("devl_fee", 0) or 0) / 12, 2)
        ),

        eclass=fee(
            "eclass",
            round(float(student.get("eclass", 0) or 0) / 12, 2)
        ),

        science=fee(
            "science",
            round(float(student.get("science", 0) or 0) / 12, 2)
        ),

        computer=fee(
            "computer",
            round(float(student.get("computer", 0) or 0) / 12, 2)
        ),

        kgarten=fee(
            "kgarten",
            round(float(student.get("kgarten", 0) or 0) / 12, 2)
        )
    )
