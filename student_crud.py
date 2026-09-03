from flask import Blueprint, request, render_template_string
from pymongo import MongoClient
import datetime

# ------------------ Blueprint Setup ------------------
student_crud_bp = Blueprint("student_crud_bp", __name__)

# ------------------ MongoDB Connection ------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["school_db"]
master = db["master"]

# ------------------ Utility Functions ------------------


def find_student(adm_code):
    return master.find_one({"adm_code": adm_code})


def update_student(adm_code, updates):
    student = find_student(adm_code)
    if not student:
        return False, "❌ Student not found!"

    # handle date and transport separately
    if "date_of_admission" in updates:
        try:
            updates["date_of_admission"] = datetime.datetime.strptime(
                updates["date_of_admission"], "%Y-%m-%d")
        except Exception:
            pass

    if "transport_stand" in updates or "transport_charges" in updates:
        transport = student.get("transport", {})
        if "transport_stand" in updates:
            transport["stand"] = updates["transport_stand"]
            del updates["transport_stand"]
        if "transport_charges" in updates:
            try:
                transport["charges"] = int(updates["transport_charges"])
            except Exception:
                transport["charges"] = updates["transport_charges"]
            del updates["transport_charges"]
        updates["transport"] = transport

    result = master.update_one({"adm_code": adm_code}, {"$set": updates})
    if result.modified_count > 0:
        return True, "✅ Student record updated successfully!"
    else:
        return False, "⚠️ No changes made."


# ------------------ HTML Template ------------------
template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Student Modify Inline</title>
    <style>
        body { font-family: "Segoe UI", sans-serif; background:#f4f6f9; margin:0; padding:20px; }
        .container { max-width:900px; margin:auto; background:white; padding:30px; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.1); }
        h2 { text-align:center; color:#2c3e50; }
        table { width:100%; border-collapse:collapse; margin-top:20px; }
        th, td { border:1px solid #ddd; padding:8px; text-align:left; }
        th { background:#34495e; color:white; }
        input { width:100%; padding:6px; border:1px solid #ccc; border-radius:4px; }
        button { margin-top:20px; padding:12px; background:#1abc9c; color:white; border:none; border-radius:4px; font-size:16px; cursor:pointer; }
        button:hover { background:#16a085; }
        .message { margin-top:20px; text-align:center; font-size:16px; font-weight:bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📝 Master Student Modify (Inline)</h2>
        
        <!-- Step 1: Find Student -->
        <form method="POST" action="/mastmodi/find">
            <label>Enter Admission Code:</label>
            <input type="text" name="adm_code" required>
            <button type="submit">Find</button>
        </form>

        {% if student %}
        <h3>Student Record</h3>
        <form method="POST" action="/mastmodi/update">
            <input type="hidden" name="adm_code" value="{{ student.adm_code }}">
            <table>
                {% for key, value in student.items() %}
                    {% if key != "_id" %}
                    <tr>
                        <th>{{ key }}</th>
                        <td><input type="text" name="{{ key }}" value="{{ value }}"></td>
                    </tr>
                    {% endif %}
                {% endfor %}
            </table>
            <button type="submit">Update Record</button>
        </form>
        {% endif %}

        <div class="message">{{ message }}</div>
    </div>
</body>
</html>
"""

# ------------------ Routes ------------------


@student_crud_bp.route("/", methods=["GET"])
def home():
    return render_template_string(template, student=None, message="")


@student_crud_bp.route("/find", methods=["POST"])
def find():
    adm_code = request.form["adm_code"]
    student = find_student(adm_code)
    if not student:
        return render_template_string(template, student=None, message="❌ Student not found!")
    return render_template_string(template, student=student, message="✅ Student found!")


@student_crud_bp.route("/update", methods=["POST"])
def update():
    adm_code = request.form["adm_code"]
    updates = {k: v for k, v in request.form.items() if k != "adm_code"}
    success, message = update_student(adm_code, updates)
    student = find_student(adm_code)
    return render_template_string(template, student=student, message=message)
