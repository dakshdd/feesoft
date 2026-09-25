from flask import Blueprint, request, render_template, render_template_string
from bson.objectid import ObjectId
from db import master_collection, tran_collection, get_school

studledg_bp = Blueprint("studledg_bp", __name__)

base_layout = """
<!DOCTYPE html>
<html>
<head>
<title>Student Ledger</title>
<style>
body{font-family:"Segoe UI",sans-serif;margin:0;background:#0000ff00}
.container{max-width:900px;margin:40px auto;background:white;padding:30px;border-radius:10px;box-shadow:0 4px 10px #0002}
h2{color:#2c3e50;margin-bottom:20px}
form{margin-bottom:20px}
input{padding:10px;width:250px;border:1px solid #ccc;border-radius:5px}
button{padding:10px 20px;background:#1abc9c;color:white;border:0;border-radius:5px;cursor:pointer}
table{border-collapse:collapse;width:100%;margin-top:20px}
th,td{border:1px solid #ddd;padding:12px;text-align:center}
th{background:#2c3e50;color:white}
tr:nth-child(even){background:#f9f9f9}
.print-btn{background:#3498db;color:white;padding:6px 12px;border-radius:5px;text-decoration:none}
.school{text-align:center;margin-bottom:20px}
.school h1{margin:0;color:#2c3e50;font-size:24px}
.school p{margin:3px;color:#555}
</style>
</head>
<body>
<div class="container">
{{ content|safe }}
</div>
</body>
</html>
"""


@studledg_bp.route("/", methods=["GET", "POST"])
def ledger_home():

    school = get_school() or {}
    school_name = school.get("school_name", "")
    address = school.get("address", "")
    phone = school.get("phone", "")

    header = f"""
    <div class="school">
        <h1>🏫 {school_name}</h1>
        <p>📍 {address} | 📞 {phone}</p>
    </div>
    """

    if request.method == "POST":

        adm_code = request.form.get("admission_no", "").strip()

        records = list(
            tran_collection.find({"adm_code": adm_code}).sort("date", 1)
        )

        if not records:
            return render_template_string(
                base_layout,
                content=header +
                f"<h2>No ledger found for Admission No: {adm_code}</h2>"
            )

        table = f"""
        {header}
        <h2>📒 Ledger - {adm_code}</h2>
        <table>
        <tr>
            <th>Receipt No</th>
            <th>Month</th>
            <th>Date</th>
            <th>Total Fee</th>
            <th>Paid</th>
            <th>Balance</th>
            <th>Action</th>
        </tr>
        """

        for r in records:
            table += f"""
            <tr>
                <td>{r.get('receipt_no', '')}</td>
                <td>{r.get('month', '')}</td>
                <td>{r.get('date', '')}</td>
                <td>{r.get('total_fee', 0)}</td>
                <td>{r.get('paid', 0)}</td>
                <td>{r.get('balance', 0)}</td>
                <td>
                    <a class="print-btn"
                       href="/studledg/print/{r.get('_id')}"
                       target="_blank">🖨️ Print</a>
                </td>
            </tr>
            """

        table += "</table>"

        return render_template_string(base_layout, content=table)

    form = f"""
    {header}
    <h2>📒 Student Ledger</h2>
    <form method="POST">
        <label>Admission Number:</label>
        <input type="text" name="admission_no"
               placeholder="e.g. ADM-0019" required>
        <button type="submit">Show Ledger</button>
    </form>
    """

    return render_template_string(base_layout, content=form)


@studledg_bp.route("/print/<tran_id>")
def print_transaction(tran_id):

    try:
        record = tran_collection.find_one({"_id": ObjectId(tran_id)})
    except Exception:
        return "<h2>Invalid transaction ID format</h2>"

    if not record:
        return "<h2>Transaction not found</h2>"

    student = master_collection.find_one({
        "adm_code": record.get("adm_code", "")
    }) or {}

    school = get_school() or {}

    return render_template(
        "receipt.html",

        school_name=school.get("school_name", ""),
        school_address=school.get("address", ""),
        school_phone=school.get("phone", ""),

        receipt_no=record.get("receipt_no", ""),
        adm_code=record.get("adm_code", ""),

        student_name=record.get(
            "student_name", student.get("student_name", "")
        ),

        student_class=record.get(
            "student_class", student.get("class", "")
        ),

        section=record.get(
            "section", student.get("section", "")
        ),

        father_name=record.get(
            "father_name", student.get("father_name", "")
        ),

        date=record.get("date", ""),
        month=record.get("month", ""),

        payment_mode=record.get(
            "payment_mode", record.get("mode", "Cash")
        ),

        remark=record.get("remark", ""),
        paid=record.get("paid", 0),
        balance=record.get("balance", 0),

        admission_fee=record.get("admission_fee", 0),
        annual_fee=record.get("annual_fee", 0),

        tuition_fee=record.get(
            "tuition_fee", student.get("tuition_fee", 0)
        ),

        transport_fee=record.get(
            "transport_fee",
            round(float(student.get("transport_total", 0) or 0) / 10.5, 2)
        ),

        devl_fee=record.get(
            "devl_fee",
            round(float(student.get("devl_fee", 0) or 0) / 12, 2)
        ),

        eclass=record.get(
            "eclass",
            round(float(student.get("eclass", 0) or 0) / 12, 2)
        ),

        science=record.get(
            "science",
            round(float(student.get("science", 0) or 0) / 12, 2)
        ),

        computer=record.get(
            "computer",
            round(float(student.get("computer", 0) or 0) / 12, 2)
        ),

        kgarten=record.get(
            "kgarten",
            round(float(student.get("kgarten", 0) or 0) / 12, 2)
        )
    )
