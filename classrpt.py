# classrpt.py
import os
from flask import Blueprint, request, render_template_string
from pymongo import MongoClient
from db import master_collection


# ------------------ Blueprint Setup ------------------
classrpt_bp = Blueprint("classrpt_bp", __name__)

# ------------------ Templates ------------------

# Input Form
form_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Class Report Input</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; background:#f4f6f7; display:flex; justify-content:center; align-items:center; height:100vh; }
        .box { background:white; padding:30px; border-radius:8px; box-shadow:0 0 10px rgba(0,0,0,0.2); width:350px; }
        h2 { text-align:center; margin-bottom:20px; }
        input[type=text] { width:100%; padding:10px; margin:8px 0; border:1px solid #ccc; border-radius:4px; }
        input[type=submit] { width:32%; padding:10px; background:#1abc9c; color:white; border:none; border-radius:4px; cursor:pointer; margin-top:10px; }
        input[type=submit]:hover { background:#16a085; }
        .btn-row { display:flex; justify-content:space-between; }
    </style>
</head>
<body>
    <div class="box">
        <h2>Class Report</h2>
        <form method="POST">
            <label>Class:</label>
            <input type="text" name="class" placeholder="e.g. 1st" required>
            <label>Section:</label>
            <input type="text" name="sec" placeholder="e.g. A" required>
            <div class="btn-row">
                <input type="submit" name="action" value="Class Wise Report">
                <input type="submit" name="action" value="Total Student in School">
                <input type="submit" name="action" value="Transport Report">
            </div>
        </form>
    </div>
</body>
</html>
"""

# Class Wise Report Template
report_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Class Report</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; background:#f4f6f7; padding:20px; }
        table { border-collapse: collapse; width: 100%; background:white; }
        th, td { border:1px solid #ccc; padding:8px; text-align:left; }
        th { background:#2c3e50; color:white; }
        h2 { margin-bottom:20px; }
        .total-row { font-weight:bold; background:#dfe6e9; }
    </style>
</head>
<body>
    <h2>Class Report: {{ class_name }} - Section {{ section }}</h2>
    <table>
        <tr>
            <th>Adm Code</th><th>Name</th><th>Father</th><th>Mother</th>
            <th>Category</th><th>Address</th><th>Contact</th>
            <th>Admission Fee</th><th>Annual Fee</th><th>Exam Fee</th>
            <th>Tuition Fee</th><th>Total Fee</th><th>Paid Fee</th><th>Balance</th>
        </tr>
        {% for s in students %}
        <tr>
            <td>{{ s['adm_code'] }}</td>
            <td>{{ s['student_name'] }}</td>
            <td>{{ s['father_name'] }}</td>
            <td>{{ s['mother_name'] }}</td>
            <td>{{ s['catg'] }}</td>
            <td>{{ s['address'] }}</td>
            <td>{{ s['contact'] }}</td>
            <td>{{ s['admission_fee'] }}</td>
            <td>{{ s['annual_fee'] }}</td>
            <td>{{ s['exam_fee'] }}</td>
            <td>{{ s['tuition_fee'] }}</td>
            <td>{{ s['total_fee'] }}</td>
            <td>{{ s['paid_fee'] }}</td>
            <td>{{ s['balance_fee'] }}</td>
        </tr>
        {% endfor %}
        <tr class="total-row">
            <td colspan="11">Grand Totals</td>
            <td>{{ total_fee }}</td>
            <td>{{ paid_fee }}</td>
            <td>{{ balance_fee }}</td>
        </tr>
    </table>
    <p><b>Total Students:</b> {{ students|length }}</p>
</body>
</html>
"""

# Total Student Report Template
count_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Total Students</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; background:#f4f6f7; padding:20px; }
        table { border-collapse: collapse; width: 60%; background:white; margin:auto; }
        th, td { border:1px solid #ccc; padding:8px; text-align:center; }
        th { background:#2c3e50; color:white; }
        h2 { text-align:center; margin-bottom:20px; }
        .total-row { font-weight:bold; background:#dfe6e9; }
    </style>
</head>
<body>
    <h2>Total Students in School</h2>
    <table>
        <tr><th>Class</th><th>Section</th><th>Count</th></tr>
        {% for row in counts %}
        <tr>
            <td>{{ row['_id']['class'] }}</td>
            <td>{{ row['_id']['sec'] }}</td>
            <td>{{ row['count'] }}</td>
        </tr>
        {% endfor %}
        <tr class="total-row">
            <td colspan="2">Grand Total</td>
            <td>{{ grand_total }}</td>
        </tr>
    </table>
</body>
</html>
"""

# Transport Report Template
transport_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Transport Report</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; background:#f4f6f7; padding:20px; }
        table { border-collapse: collapse; width: 100%; background:white; }
        th, td { border:1px solid #ccc; padding:8px; text-align:left; }
        th { background:#2c3e50; color:white; }
        h2 { margin-bottom:20px; }
        .total-row { font-weight:bold; background:#dfe6e9; }
    </style>
</head>
<body>
    <h2>Transport Report: {{ class_name }} - Section {{ section }}</h2>
    <table>
        <tr>
            <th>Adm Code</th><th>Name</th><th>Father</th>
            <th>Transport Stand</th><th>Transport Charges</th>
        </tr>
        {% for s in students %}
        <tr>
            <td>{{ s['adm_code'] }}</td>
            <td>{{ s['student_name'] }}</td>
            <td>{{ s['father_name'] }}</td>
            <td>{{ s['transport_stand'] }}</td>
            <td>{{ s['transport_charges'] }}</td>
        </tr>
        {% endfor %}
        <tr class="total-row">
            <td colspan="4">Grand Total Transport Charges</td>
            <td>{{ total_charges }}</td>
        </tr>
    </table>
    <p><b>Total Students:</b> {{ students|length }}</p>
</body>
</html>
"""

# ------------------ Backend Logic ------------------


@classrpt_bp.route("/", methods=["GET", "POST"])
def class_report():
    if request.method == "POST":
        action = request.form["action"]

        # -------- Class Wise Report --------
        if action == "Class Wise Report":
            class_name = request.form["class"]
            section = request.form["sec"]
            students = list(master_collection.find(
                {"class": class_name, "sec": section}))

            total_fee = sum(float(s.get("total_fee", 0)) for s in students)
            paid_fee = sum(float(s.get("paid_fee", 0)) for s in students)
            balance_fee = sum(float(s.get("balance_fee", 0)) for s in students)

            return render_template_string(
                report_template,
                class_name=class_name,
                section=section,
                students=students,
                total_fee=total_fee,
                paid_fee=paid_fee,
                balance_fee=balance_fee
            )

        # -------- Total Student Report --------
        elif action == "Total Student in School":
            pipeline = [
                {"$group": {"_id": {"class": "$class", "sec": "$sec"}, "count": {"$sum": 1}}},
                {"$sort": {"_id.class": 1, "_id.sec": 1}}
            ]
            counts = list(master_collection.aggregate(pipeline))
            grand_total = sum(row["count"] for row in counts)

            return render_template_string(count_template, counts=counts, grand_total=grand_total)

        # -------- Transport Report --------
        elif action == "Transport Report":
            class_name = request.form["class"]
            section = request.form["sec"]
            students = list(master_collection.find(
                {"class": class_name, "sec": section}))

            # सिर्फ़ transport_charges का grand total निकालना
            total_charges = sum(s.get("transport_charges", 0)
                                for s in students)

            return render_template_string(
                transport_template,
                class_name=class_name,
                section=section,
                students=students,
                total_charges=total_charges
            )
    # Agar GET request hai to form show karo
    return render_template_string(form_template)
