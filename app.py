# app.py
import os
import json
import secrets
import string
from datetime import datetime
from flask import Blueprint, Flask, request, render_template_string, redirect, url_for, flash
from pymongo import ASCENDING, ReturnDocument
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from db import master_collection, counters_collection, transport_collection, tran_collection, school_collection

master_bp = Blueprint("master_bp", __name__)
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

if counters_collection.count_documents({"_id": "adm_code"}) == 0:
    counters_collection.insert_one({"_id": "adm_code", "seq": 0})

master_collection.create_index([("adm_code", ASCENDING)], unique=True)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

with open("fee_data.json", "r", encoding="utf-8") as f:
    fee_data = json.load(f)


def get_next_adm_code():
    x = counters_collection.find_one_and_update(
        {"_id": "adm_code"},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    return x["seq"]


FORM_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>STUDENT MASTER ENTRY</title>
<style>
body{font-family:'Segoe UI',sans-serif;margin:20px;background:#f3f8ff}
form{background:#fff;padding:30px;border-radius:10px;box-shadow:0 4px 12px #0002;max-width:1400px;margin:auto}
h1{text-align:center;color:#2563eb;margin-bottom:20px}
.row{display:flex;flex-wrap:wrap;gap:20px;margin-bottom:16px}
.field{flex:1;min-width:220px;display:flex;flex-direction:column}
.field.amount{flex:0 0 120px;min-width:120px;max-width:120px}
.field.amount input{text-align:center}
label{font-size:14px;margin-bottom:6px;font-weight:700;color:#374151}
input,select{padding:8px;border:1px solid #ccc;border-radius:6px;font-size:14px}
input[readonly]{background:#f9fafb}
button{padding:12px 20px;border:0;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer;font-size:15px;font-weight:600;margin-top:10px}
button:hover{background:#1e40af}
button:disabled{background:#9ca3af;cursor:not-allowed}
</style>
</head>
<body>

<h1>STUDENT MASTER ENTRY</h1>

<form method="post" action="{{ url_for('master_bp.save_master') }}" enctype="multipart/form-data">

<div class="row">
<div class="field"><label>Student Name</label><input name="student_name" required></div>
<div class="field"><label>Student Photo</label><input type="file" name="photo" accept="image/*"></div>
</div>

<div class="row">
<div class="field"><label>Class</label>
<select id="class" name="class" required>
<option value="">-- Select Class --</option>
{% for c in fee_data %}<option value="{{ c }}">{{ c }}</option>{% endfor %}
</select>
</div>

<div class="field"><label>Section</label>
<select name="sec" required>
<option value="">-- Select Section --</option><option>A</option><option>B</option><option>C</option>
</select>
</div>

<div class="field"><label>Category</label>
<select name="catg" required>
<option value="">-- Select Category --</option>
<option>GEN</option><option>EWS</option><option>STAFF</option><option>MANAG</option>
</select>
</div>

<div class="field"><label>Gender</label>
<select name="gender" required>
<option value="">-- Select Gender --</option><option>Male</option><option>Female</option>
</select>
</div>
</div>

<div class="row">
{% for id,label in [('eclass','E-Class'),('science','Science'),('computer','Computer'),('kgarten','K.Garten')] %}
<div class="field amount"><label>{{ label }}</label><input type="number" id="{{ id }}" name="{{ id }}" value="0" min="0"></div>
{% endfor %}
</div>

<div class="row">
<div class="field amount"><label>Admission Fee</label><input id="admission_fee" name="admission_fee"></div>
<div class="field amount"><label>Annual Fee</label><input id="annual_fee" name="annual_fee"></div>
<div class="field amount"><label>Development Fee</label><input id="devl_fee" name="devl_fee"></div>
</div>

<div class="row">
<div class="field amount"><label>Discount On Tuition</label><input id="discount" name="discount" type="number" min="0" value="0"></div>
<div class="field amount"><label>Tuition Fee / Month</label><input id="tuition_fee" name="tuition_fee" readonly></div>
</div>

<div class="row">
<div class="field"><label>Father Name</label><input name="father_name" required></div>
<div class="field"><label>Mother Name</label><input name="mother_name" required></div>
</div>

<div class="row">
<div class="field"><label>Address</label><input name="address"></div>
<div class="field"><label>Contact Number</label><input name="contact"></div>
<div class="field"><label>Date of Admission</label><input type="date" name="doa"></div>
</div>

<div class="row">
<div class="field"><label>Transport Stand</label>
<select name="transport" required>
<option value="">-- Select Transport --</option>
{% for t in transports %}<option value="{{ t.stand }}">{{ t.stand }} (₹{{ t.charges }})</option>{% endfor %}
</select>
</div>
</div>

<button type="submit" id="saveBtn">Save Student</button>
</form>

<script>
const feeData={{ fee_data|tojson }};
const cls=document.getElementById("class");
const discount=document.getElementById("discount");

function tuition(){
    let f=feeData[cls.value];
    if(!f)return;
    let t=Number(f.tuition)||0,d=Number(discount.value)||0;
    document.getElementById("tuition_fee").value=Math.max(t-d,0);
}

cls.addEventListener("change",()=>{
    let f=feeData[cls.value];
    if(!f)return;
    document.getElementById("admission_fee").value=f.admission||0;
    document.getElementById("annual_fee").value=f.annual||0;
    document.getElementById("devl_fee").value=f.development||0;
    tuition();
});

discount.addEventListener("input",tuition);

document.querySelector("form").addEventListener("submit",e=>{
    let b=document.getElementById("saveBtn");
    if(b.disabled){e.preventDefault();return}
    b.disabled=true;
    b.innerText="Saving...";
});
</script>

</body>
</html>
"""


@master_bp.route("/", methods=["GET"])
def index():
    transports = list(transport_collection.find(
        {}, {"_id": 0, "stand": 1, "charges": 1}))
    return render_template_string(FORM_HTML, transports=transports, fee_data=fee_data)


@master_bp.route("/save", methods=["POST"])
def save_master():

    adm_code = f"ADM-{get_next_adm_code():04d}"

    alphabet = string.ascii_letters+string.digits
    plain_password = "".join(secrets.choice(alphabet) for _ in range(6))

    photo_file = request.files.get("photo")
    photo_filename = None

    if photo_file and photo_file.filename:
        filename = secure_filename(photo_file.filename)
        photo_filename = f"{adm_code}_{filename}"
        photo_file.save(os.path.join(
            app.config["UPLOAD_FOLDER"], photo_filename))

    doa = request.form.get("doa")
    if doa:
        try:
            doa = datetime.strptime(doa, "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
            pass

    transport_selected = request.form.get("transport")
    transport_doc = transport_collection.find_one(
        {"stand": transport_selected}, {"_id": 0})
    transport_stand = transport_doc["stand"] if transport_doc else None
    transport_charges = transport_doc["charges"] if transport_doc else 0

    admission_fee = int(request.form.get("admission_fee") or 0)
    annual_fee = int(request.form.get("annual_fee") or 0)
    devl_fee = int(request.form.get("devl_fee") or 0)
    tuition_fee = int(request.form.get("tuition_fee") or 0)
    discount = int(request.form.get("discount") or 0)

    eclass = int(request.form.get("eclass") or 0)*12
    science = int(request.form.get("science") or 0)*12
    computer = int(request.form.get("computer") or 0)*12
    kgarten = int(request.form.get("kgarten") or 0)*12

    tuition_total = tuition_fee*12
    devl_fee = devl_fee*12
    transport_total = transport_charges*10.5

    total_fee = (
        admission_fee+annual_fee+devl_fee +
        tuition_total+transport_total +
        eclass+science+computer+kgarten
    )

    doc = {
        "adm_code": adm_code,
        "student_name": request.form.get("student_name"),
        "class": request.form.get("class"),
        "sec": request.form.get("sec"),
        "catg": request.form.get("catg"),
        "gender": request.form.get("gender"),
        "father_name": request.form.get("father_name"),
        "mother_name": request.form.get("mother_name"),
        "address": request.form.get("address"),
        "contact": request.form.get("contact"),
        "doa": doa,
        "photo": photo_filename,
        "transport_stand": transport_stand,
        "transport_charges": transport_charges,
        "admission_fee": admission_fee,
        "annual_fee": annual_fee,
        "devl_fee": devl_fee,
        "discount": discount,
        "tuition_fee": tuition_fee,
        "tuition_total": tuition_total,
        "transport_total": transport_total,
        "total_fee": total_fee,
        "paid_fee": 0,
        "balance_fee": total_fee,
        "password_hash": generate_password_hash(plain_password),
        "eclass": eclass,
        "science": science,
        "computer": computer,
        "kgarten": kgarten
    }

    try:
        master_collection.insert_one(doc)
        return redirect(url_for("master_bp.receipt", adm_code=adm_code, plain_password=plain_password))
    except Exception as e:
        flash(f"Error: {e}", "error")
        return redirect(url_for("master_bp.index"))


RECEIPT_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Admission Details</title>
<style>
body{font-family:'Segoe UI',sans-serif;margin:20px;background:#f9fafb}
.card{background:#fff;padding:20px;border-radius:10px;box-shadow:0 4px 12px #0002;max-width:650px;margin:auto}
h1{text-align:center;color:#111827;font-size:28px;margin:0}
h2{text-align:center;color:#2563eb;font-size:18px;margin:5px 0 15px}
.photo{text-align:center;margin:15px}.photo img{width:120px;height:120px;object-fit:cover;border-radius:8px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ccc;padding:8px;text-align:left}
th{background:#f3f4f6}
td:last-child,th:last-child{text-align:right}
.total td{font-weight:bold;background:#eef2f7}
.balance td{font-weight:bold}
</style>
</head>
<body>

<div class="card">

<h1>{{ school.school_name if school else "" }}</h1>
<h2>{{ school.address if school else "" }}</h2>
<h2 style="color:#111827">Admission Details</h2>

{% if student.photo %}
<div class="photo">
<img src="{{ url_for('static',filename='uploads/' ~ student.photo) }}">
</div>
{% endif %}

<p><strong>Admission Code:</strong> {{ student.adm_code }}</p>
<p><strong>Student Name:</strong> {{ student.student_name }}</p>
<p><strong>Class:</strong> {{ student.class }} - {{ student.sec }}</p>
<p><strong>Category:</strong> {{ student.catg }}</p>
<p><strong>Transport:</strong> {{ student.transport_stand }} (₹{{ student.transport_charges }} per month)</p>
<p><strong>Login Password:</strong> {{ plain_password }}</p>

<table>
<tr><th>Fee Type</th><th>Amount (₹)</th></tr>

{% if student.admission_fee %}<tr><td>Admission Fee</td><td>{{ student.admission_fee }}</td></tr>{% endif %}
{% if student.annual_fee %}<tr><td>Annual Fee</td><td>{{ student.annual_fee }}</td></tr>{% endif %}
{% if student.devl_fee %}<tr><td>Development Fee</td><td>{{ student.devl_fee }}</td></tr>{% endif %}
{% if student.discount %}<tr><td>Discount Per Month on Tuition Fee</td><td>{{ student.discount }}</td></tr>{% endif %}
{% if student.tuition_total %}<tr><td>Tuition Fee (12 months after discount)</td><td>{{ student.tuition_total }}</td></tr>{% endif %}
{% if student.transport_total %}<tr><td>Transport Fee (10.5 months)</td><td>{{ student.transport_total }}</td></tr>{% endif %}
{% if student.eclass %}<tr><td>E-Class</td><td>{{ student.eclass }}</td></tr>{% endif %}
{% if student.science %}<tr><td>Science</td><td>{{ student.science }}</td></tr>{% endif %}
{% if student.computer %}<tr><td>Computer</td><td>{{ student.computer }}</td></tr>{% endif %}
{% if student.kgarten %}<tr><td>K.Garten</td><td>{{ student.kgarten }}</td></tr>{% endif %}

<tr class="total"><td>Total</td><td>{{ student.total_fee }}</td></tr>
<tr><td>Paid</td><td>{{ student.paid_fee }}</td></tr>
<tr class="balance"><td>Balance</td><td>{{ student.balance_fee }}</td></tr>
</table>

</div>
</body>
</html>
"""


@master_bp.route("/receipt/<adm_code>/<plain_password>")
def receipt(adm_code, plain_password):

    student = master_collection.find_one({"adm_code": adm_code})

    if not student:
        flash("Student not found", "error")
        return redirect(url_for("master_bp.index"))

    school = school_collection.find_one()

    return render_template_string(
        RECEIPT_HTML,
        student=student,
        plain_password=plain_password,
        school=school
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
