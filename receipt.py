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
        body { font-family:"Segoe UI",sans-serif; margin:0; background:#f4f6f9; }
        .container { max-width:900px; margin:40px auto; background:white; padding:30px;
                     border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,.1); }
        h2 { color:#2c3e50; margin-bottom:20px; }
        form { margin-bottom:20px; }
        input[type=text] { padding:10px; width:250px; border:1px solid #ccc; border-radius:5px; }
        button { padding:10px 20px; background:#1abc9c; color:white;
                 border:0; border-radius:5px; cursor:pointer; }
        button:hover { background:#16a085; }
        table { border-collapse:collapse; width:100%; margin-top:20px; }
        th,td { border:1px solid #ddd; padding:12px; text-align:center; }
        th { background:#2c3e50; color:white; }
        tr:nth-child(even) { background:#f9f9f9; }
        tr:hover { background:#eafaf9; }
        a.print-btn { background:#3498db; color:white; padding:6px 12px;
                      border-radius:5px; text-decoration:none; }
    </style>
</head>
<body>
    <div class="container">{{ content|safe }}</div>
</body>
</html>
"""


def prepare_receipt(receipt):
    """Combine transaction data with student's master details.
       Receipt always shows the values saved at payment time.
    """

    student = master_collection.find_one({
        "adm_code": receipt.get("adm_code", "")
    }) or {}

    data = dict(receipt)

    school = get_school()

    data["school_name"] = school.get("school_name", "") if school else ""
    data["school_address"] = school.get("address", "") if school else ""
    data["school_phone"] = school.get("phone", "") if school else ""

    # Student Details (master se update)
    data["student_name"] = student.get(
        "student_name",
        data.get("student_name", "")
    )

    data["student_class"] = student.get(
        "class",
        data.get("class", "")
    )

    data["father_name"] = student.get(
        "father_name",
        data.get("father_name", "")
    )

    data["section"] = student.get(
        "section",
        data.get("section", "")
    )

    # Payment Mode
    data["payment_mode"] = data.get(
        "payment_mode",
        data.get("mode", "Cash")
    )

    # ✅ Receipt ke fee heads transaction se hi lo.
    data["admission_fee"] = float(data.get("admission_fee", 0) or 0)
    data["annual_fee"] = float(data.get("annual_fee", 0) or 0)
    data["tuition_fee"] = float(data.get("tuition_fee", 0) or 0)
    data["transport_fee"] = float(data.get("transport_fee", 0) or 0)
    data["devl_fee"] = float(data.get("devl_fee", 0) or 0)
    data["eclass"] = float(data.get("eclass", 0) or 0)
    data["science"] = float(data.get("science", 0) or 0)
    data["computer"] = float(data.get("computer", 0) or 0)
    data["kgarten"] = float(data.get("kgarten", 0) or 0)

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

        receipt = prepare_receipt(receipt)

        return render_template(
            "receipt.html",
            **receipt
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

        table_html = (
            f"<h2>Receipts for Admission No: {adm_code}</h2>"
            "<table>"
            "<tr>"
            "<th>ID</th>"
            "<th>Month</th>"
            "<th>Date</th>"
            "<th>Paid</th>"
            "<th>Balance</th>"
            "<th>Action</th>"
            "</tr>"
        )

        for r in receipts:

            table_html += (
                f"<tr>"
                f"<td>{str(r.get('_id'))[:6]}</td>"
                f"<td>{r.get('month', '')}</td>"
                f"<td>{r.get('date', '')}</td>"
                f"<td>{r.get('paid', 0)}</td>"
                f"<td>{r.get('balance', 0)}</td>"
                f"<td>"
                f"<a class='print-btn' "
                f"href='/receipts/print/{r.get('_id')}' "
                f"target='_blank'>🖨️ Print</a>"
                f"</td>"
                f"</tr>"
            )

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

    receipt = prepare_receipt(receipt)

    return render_template(
        "receipt.html",
        **receipt
    )
