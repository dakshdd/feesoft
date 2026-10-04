from flask import Blueprint, request, render_template, render_template_string
from bson.objectid import ObjectId
from markupsafe import escape
from db import master_collection, tran_collection, get_school

receipt_bp = Blueprint("receipt_bp", __name__)

base_layout = """
<!DOCTYPE html>
<html>
<head>
<title>Re-Print Receipts</title>
<style>
body{font-family:"Segoe UI",sans-serif;margin:0;background:#f4f6f9}
.container{max-width:900px;margin:40px auto;background:#fff;padding:30px;
border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,.1)}
h2{color:#2c3e50;margin-bottom:20px}
form{margin-bottom:20px}
input[type=text]{padding:10px;width:250px;border:1px solid #ccc;border-radius:5px}
button{padding:10px 20px;background:#1abc9c;color:#fff;border:0;border-radius:5px;cursor:pointer}
table{border-collapse:collapse;width:100%;margin-top:20px}
th,td{border:1px solid #ddd;padding:10px;text-align:center}
th{background:#2c3e50;color:#fff}
tr:nth-child(even){background:#f9f9f9}
a.print-btn{background:#3498db;color:#fff;padding:6px 12px;border-radius:5px;text-decoration:none}
</style>
</head>
<body><div class="container">{{content|safe}}</div></body>
</html>
"""


def prepare_receipt(receipt):
    student = master_collection.find_one({
        "adm_code": receipt.get("adm_code", "")
    }) or {}

    data = dict(receipt)
    school = get_school() or {}

    # ---------------- MONTH FIX ----------------
    months = data.get("months") or []

    if not months and data.get("month"):
        months = [data.get("month")]

    if not months and data.get("month_details"):
        months = list(data.get("month_details", {}).keys())

    months = [str(m) for m in months if m]

    data["months"] = months
    data["selected_month"] = ", ".join(months) if months else "N/A"
    # --------------------------------------------

    data.update({
        "school_name": school.get("school_name", ""),
        "school_address": school.get("address", ""),
        "school_phone": school.get("phone", ""),
        "student_name": student.get(
            "student_name", data.get("student_name", "")
        ),
        "student_class": student.get(
            "class", data.get("class", "")
        ),
        "father_name": student.get(
            "father_name", data.get("father_name", "")
        ),
        "section": student.get(
            "section", data.get("section", "")
        ),
        "payment_mode": data.get(
            "payment_mode",
            data.get("mode", "Cash")
        )
    })

    for key in [
        "admission_fee", "annual_fee", "tuition_fee",
        "transport_fee", "devl_fee", "eclass",
        "science", "computer", "kgarten"
    ]:
        data[key] = float(data.get(key, 0) or 0)

    paid_amount = float(
        data.get("paid_amount", data.get("paid", 0)) or 0
    )

    amount_paid = float(
        data.get("amount_paid", 0) or 0
    )

    balance_amount = float(
        data.get("balance_amount", data.get("balance", 0)) or 0
    )

    # Fallback for old receipts
    if not amount_paid:
        details = data.get("month_details") or {}

        if details:
            amount_paid = round(sum(
                float(x.get("total", 0) or 0)
                for x in details.values()
            ), 2)

    if not balance_amount and amount_paid:
        balance_amount = max(
            round(amount_paid - paid_amount, 2), 0
        )

    data["amount_paid"] = amount_paid
    data["paid_amount"] = paid_amount
    data["balance_amount"] = balance_amount

    return data


@receipt_bp.route("/home", methods=["GET", "POST"])
def receipt_home():
    if request.method == "POST":
        receipt_no = escape(
            request.form.get("receipt_no", "").strip()
        )

        receipt = tran_collection.find_one({
            "receipt_no": str(receipt_no)
        })

        if not receipt:
            return render_template_string(
                base_layout,
                content=f"<h2>No receipt found for Receipt No: {receipt_no}</h2>"
            )

        return render_template(
            "receipt.html",
            **prepare_receipt(receipt)
        )

    form_html = """
    <h2>🔎 Re-Print by Receipt No</h2>
    <form method="POST">
        <label>Receipt Number:</label>
        <input type="text" name="receipt_no"
               placeholder="e.g. REC-00001" required>
        <button type="submit">Search & Print</button>
    </form>
    """

    return render_template_string(
        base_layout,
        content=form_html
    )


@receipt_bp.route("/", methods=["GET", "POST"])
def receipts_home():
    if request.method == "POST":

        adm_code = escape(
            request.form.get("admission_no", "").strip()
        )

        receipts = list(
            tran_collection.find({
                "adm_code": str(adm_code)
            }).sort("date", -1)
        )

        if not receipts:
            return render_template_string(
                base_layout,
                content=f"<h2>No receipts found for Admission No: {adm_code}</h2>"
            )

        table_html = """
        <h2>Receipts for Admission No: {}</h2>
        <table>
        <tr>
            <th>ID</th>
            <th>Month</th>
            <th>Date</th>
            <th>Paid</th>
            <th>Balance</th>
            <th>Action</th>
        </tr>
        """.format(adm_code)

        for r in receipts:

            months = r.get("months") or []

            if not months and r.get("month"):
                months = [r.get("month")]

            if not months and r.get("month_details"):
                months = list(
                    r.get("month_details", {}).keys()
                )

            month_text = ", ".join(
                str(m) for m in months if m
            ) or "N/A"

            table_html += f"""
            <tr>
                <td>{str(r.get('_id'))[:6]}</td>
                <td>{month_text}</td>
                <td>{r.get('date', '')}</td>
                <td>₹{float(r.get('paid_amount', r.get('paid', 0)) or 0):.2f}</td>
                <td>₹{float(r.get('balance_amount', r.get('balance', 0)) or 0):.2f}</td>
                <td>
                    <a class="print-btn"
                       href="/receipts/print/{r.get('_id')}"
                       target="_blank">🖨️ Print</a>
                </td>
            </tr>
            """

        table_html += "</table>"

        return render_template_string(
            base_layout,
            content=table_html
        )

    form_html = """
    <h2>🔎 Re-Print by Admission No</h2>
    <form method="POST">
        <label>Admission Number:</label>
        <input type="text" name="admission_no"
               placeholder="e.g. ADM-0019" required>
        <button type="submit">Search</button>
    </form>
    """

    return render_template_string(
        base_layout,
        content=form_html
    )


@receipt_bp.route("/print/<receipt_id>")
def print_receipt(receipt_id):

    try:
        receipt = tran_collection.find_one({
            "_id": ObjectId(receipt_id)
        })
    except Exception:
        return "<h2>Invalid receipt ID format</h2>"

    if not receipt:
        return "<h2>Receipt not found</h2>"

    return render_template(
        "receipt.html",
        **prepare_receipt(receipt)
    )
