from pymongo import MongoClient, errors
import os
import json
import secrets
import string
from datetime import datetime
from flask import Blueprint, Flask, request, render_template_string, redirect, url_for, flash
from pymongo import MongoClient, ASCENDING, ReturnDocument, errors
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from db import (
    master_collection,
    counters_collection,
    transport_collection,
    tran_collection,
)

# ------------------ Blueprint Setup ------------------
master_bp = Blueprint("master_bp", __name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")


# Ensure counter exists
if counters_collection.count_documents({"_id": "adm_code"}) == 0:
    counters_collection.insert_one({"_id": "adm_code", "seq": 0})

# Create unique index
master_collection.create_index([("adm_code", ASCENDING)], unique=True)

# Upload folder
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# --- Load fee_data.json ---
with open("fee_data.json", "r", encoding="utf-8") as f:
    fee_data = json.load(f)

# --- Helper function ---


def get_next_adm_code():
    counter = counters_collection.find_one_and_update(
        {"_id": "adm_code"},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER,
        upsert=True
    )
    return counter["seq"]


# --- HTML Form Template ---
FORM_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>STUDENT MASTER ENTRY</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; margin: 20px; background::#0000ff60; }
    form { background:#fff; padding:30px; border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.1); max-width:1400px; margin:auto; }
    h1 { text-align:center; color:#2563eb; margin-bottom:20px; }
    .row { display:flex; flex-wrap:wrap; gap:20px; margin-bottom:16px; }
    .field { flex:1; min-width:250px; display:flex; flex-direction:column; }
    label { font-size:14px; margin-bottom:6px; font-weight:700; color:#374151; }
    input, select { padding:8px; border:1px solid #ccc; border-radius:6px; font-size:14px; }
    input[readonly] { background:#f9fafb; }
    button { padding:12px 20px; border:none; border-radius:6px; background:#2563eb; color:#fff; cursor:pointer; font-size:15px; font-weight:600; margin-top:10px; }
    button:hover { background:#1e40af; }
  </style>
</head>
<body>
  <h1>STUDENT MASTER ENTRY</h1>

  <form method="post" action="{{ url_for('master_bp.save_master') }}" enctype="multipart/form-data">

    <!-- Basic Info -->
    <div class="row">
      <div class="field"><label for="student_name">Student Name</label><input id="student_name" name="student_name" required></div>
      <div class="field"><label for="photo">Student Photo</label><input type="file" id="photo" name="photo" accept="image/*"></div>
    </div>

    <!-- Class/Section/Category -->
    <div class="row">
      <div class="field"><label for="class">Class</label>
        <select id="class" name="class" required>
          <option value="">-- Select Class --</option>
          {% for class_name, fees in fee_data.items() %}
            <option value="{{ class_name }}">{{ class_name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="field"><label for="sec">Section</label>
        <select id="sec" name="sec" required>
          <option value="">-- Select Section --</option>
          <option value="A">A</option><option value="B">B</option><option value="C">C</option>
        </select>
      </div>
      <div class="field"><label for="catg">Category</label>
        <select id="catg" name="catg" required>
          <option value="">-- Select Category --</option>
          <option value="GEN">GEN</option><option value="EWS">EWS</option>
          <option value="STAFF">STAFF</option><option value="MANAG">MANAGEMENT</option>
        </select>
      </div>
    </div>

    <!-- New Fields -->
    <div class="row">
      <div class="field"><label for="eclass">E-Class</label><input id="eclass" name="eclass"></div>
      <div class="field"><label for="science">Science</label><input id="science" name="science"></div>
      <div class="field"><label for="computer">Computer</label><input id="computer" name="computer"></div>
      <div class="field"><label for="kgarten">K.Garten</label><input id="kgarten" name="kgarten"></div>
    </div>

    <!-- Fees -->
    <div class="row">
  <div class="field">
    <label for="admission_fee">Admission Fee</label>
    <input id="admission_fee" name="admission_fee">
  </div>
  <div class="field">
    <label for="annual_fee">Annual Fee</label>
    <input id="annual_fee" name="annual_fee">
  </div>
  <div class="field">
    <label for="devl_fee">Development Fee</label>
    <input id="devl_fee" name="devl_fee">
  </div>
</div>

<div class="row">
  <div class="field">
    <label for="discount">Discount On Tuition (Rs.)</label>
    <input id="discount" name="discount" type="number" min="0" value="0">
  </div>
  <div class="field">
    <label for="tuition_fee">Tuition Fee (per month)</label>
    <input id="tuition_fee" name="tuition_fee" readonly>
  </div>
</div>

    <!-- Parents -->
    <div class="row">
      <div class="field"><label for="father_name">Father Name</label><input id="father_name" name="father_name" required></div>
      <div class="field"><label for="mother_name">Mother Name</label><input id="mother_name" name="mother_name" required></div>
    </div>

    <!-- Address/Contact -->
    <div class="row">
      <div class="field"><label for="address">Address</label><input id="address" name="address"></div>
      <div class="field"><label for="contact">Contact Number</label><input id="contact" name="contact"></div>
      <div class="field"><label for="doa">Date of Admission</label><input type="date" id="doa" name="doa"></div>
    </div>

    <!-- Transport -->
    <div class="row">
      <div class="field"><label for="transport">Transport Stand</label>
        <select id="transport" name="transport" required>
          <option value="">-- Select Transport --</option>
          {% for t in transports %}
            <option value="{{ t.stand }}">{{ t.stand }} (₹{{ t.charges }})</option>
          {% endfor %}
        </select>
      </div>
    </div>

    <button type="submit">Save Student</button>
  </form>
  <script>
  const feeData = {{ fee_data|tojson }};
  const classSelect = document.getElementById("class");
  const discountInput = document.getElementById("discount");

  function updateFees() {
    const selectedClass = classSelect.value;
    if (feeData[selectedClass]) {
      document.getElementById("admission_fee").value = feeData[selectedClass].admission || "";
      document.getElementById("annual_fee").value = feeData[selectedClass].annual || "";
      document.getElementById("devl_fee").value = feeData[selectedClass].development || "";

      let tuition = feeData[selectedClass].tuition || 0;
      const discount = parseInt(discountInput.value) || 0;
      document.getElementById("tuition_fee").value = Math.max(
          tuition - discount, 0);
    }
  }

  classSelect.addEventListener("change", updateFees);
  discountInput.addEventListener("input", updateFees);
</script>

</body>
</html>
"""

# --- Routes ---


@master_bp.route("/", methods=["GET"])
def index():
    recent = list(master_collection.find({}, {
        "adm_code": 1, "student_name": 1, "class": 1,
        "sec": 1, "catg": 1, "father_name": 1, "mother_name": 1,
        "address": 1, "contact": 1, "doa": 1, "photo": 1,
        "transport_stand": 1, "transport_charges": 1,
        "class_fee": 1, "admission_fee": 1, "annual_fee": 1, "devl_fee": 1,
        "total_fee": 1, "paid_fee": 1, "balance_fee": 1,
        "eclass": 1, "science": 1, "computer": 1, "kgarten": 1
    }).sort([("_id", -1)]).limit(10))

    transports = list(transport_collection.find(
        {}, {"_id": 0, "stand": 1, "charges": 1}))
    return render_template_string(FORM_HTML, recent=recent, transports=transports, fee_data=fee_data)


@master_bp.route("/save", methods=["POST"])
def save_master():
    next_code = get_next_adm_code()
    adm_code = f"ADM-{next_code:04d}"

    # Auto-generate password
    alphabet = string.ascii_letters + string.digits
    plain_password = ''.join(secrets.choice(alphabet) for i in range(6))
    password_hash = generate_password_hash(plain_password)

    # Photo upload
    photo_file = request.files.get("photo")
    photo_filename = None
    if photo_file and photo_file.filename:
        filename = secure_filename(photo_file.filename)
        photo_filename = f"{adm_code}_{filename}"
        photo_path = os.path.join(app.config["UPLOAD_FOLDER"], photo_filename)
        photo_file.save(photo_path)

    # Date of admission
    doa_str = request.form.get("doa")
    doa = None
    if doa_str:
        try:
            doa = datetime.strptime(doa_str, "%Y-%m-%d").strftime("%d-%m-%Y")
        except:
            doa = doa_str

    # Transport selection
    transport_selected = request.form.get("transport")
    transport_doc = transport_collection.find_one(
        {"stand": transport_selected}, {"_id": 0})
    transport_stand = transport_doc["stand"] if transport_doc else None
    transport_charges = transport_doc["charges"] if transport_doc else 0

# New fields
    eclass = int(request.form.get("eclass") or 0)
    science = int(request.form.get("science") or 0)
    computer = int(request.form.get("computer") or 0)
    kgarten = int(request.form.get("kgarten") or 0)

# Fees
    admission_fee = int(request.form.get("admission_fee") or 0)
    annual_fee = int(request.form.get("annual_fee") or 0)
    devl_fee = int(request.form.get("devl_fee") or 0)
    tuition_fee = int(request.form.get("tuition_fee") or 0)
    discount = int(request.form.get("discount") or 0)

    tuition_total = tuition_fee * 12
    devl_fee = devl_fee * 12
    eclass = eclass * 12
    science = science * 12
    computer = computer * 12
    kgarten = kgarten * 12
    transport_total = transport_charges * 10.5

    # ✅ Total fee now includes new fields
    total_fee = (
        admission_fee + annual_fee + devl_fee +
        tuition_total + transport_total +
        eclass + science + computer + kgarten
    )

    paid_fee = 0
    balance_fee = total_fee - paid_fee

    doc = {
        "adm_code": adm_code,
        "student_name": request.form.get("student_name"),
        "class": request.form.get("class"),
        "sec": request.form.get("sec"),
        "catg": request.form.get("catg"),
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
        "paid_fee": paid_fee,
        "balance_fee": balance_fee,
        "password_hash": password_hash,
        # New fields
        "eclass": eclass,
        "science": science,
        "computer": computer,
        "kgarten": kgarten
    }

    try:
        master_collection.insert_one(doc)
        return redirect(url_for("master_bp.receipt", adm_code=adm_code, plain_password=plain_password))
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for("index"))


# --- Receipt Template ---
RECEIPT_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  #<title>Admission Details</title>
  <style>
    body { font-family: 'Segoe UI', sans-serif; margin: 20px; background:#f9fafb; }
    .card { background:#fff; padding:20px; border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.1); max-width:650px; margin:auto; }
    h1 { text-align:center; color:#111827; font-size:28px; margin-top:0; }       /* big heading */
    h2 { text-align:center; color:#2563eb; font-size:18px; margin-bottom:5px; }   /* small heading */
    table { width:100%; border-collapse:collapse; margin-top:15px; }
    th, td { border:1px solid #ccc; padding:8px; text-align:left; }
    th { background:#f3f4f6; }
    .total-row td { font-weight:bold; background:#eef2f7; }
  </style>
</head>
<body>
  <div class="card">
    <h1>SHANTI GYAN NIKETAN</h2>
    <h2>Goyla Diary, New Delhi - 110042</h3>

  <div class="card">
    <h1>Admission Details</h1>
    {% if student.photo %}
      <p><img src="{{ url_for('static', filename='uploads/' ~ student.photo) }}" width="120"></p>
    {% endif %}
    <p><strong>Admission Code:</strong> {{ student.adm_code }}</p>
    <p><strong>Student Name:</strong> {{ student.student_name }}</p>
    <p><strong>Class:</strong> {{ student.class }} - {{ student.sec }}</p>
    <p><strong>Category:</strong> {{ student.catg }}</p>
    <p><strong>Transport:</strong> {{ student.transport_stand }} (?{{ student.transport_charges }} per month)</p>
    <p><strong>Login Password:</strong> {{ plain_password }}</p>

<table>
  <tr><th>Fee Type</th><th>Amount (₹)</th></tr>

  {% if student.admission_fee and student.admission_fee != 0 %}
    <tr><td>Admission Fee</td><td>{{ student.admission_fee }}</td></tr>
  {% endif %}

  {% if student.annual_fee and student.annual_fee != 0 %}
    <tr><td>Annual Fee</td><td>{{ student.annual_fee }}</td></tr>
  {% endif %}

  {% if student.devl_fee and student.devl_fee != 0 %}
    <tr><td>Development Fee</td><td>{{ student.devl_fee }}</td></tr>
  {% endif %}

  {% if student.discount and student.discount != 0 %}
    <tr><td>Discount Per months on Tuition fee</td><td>{{ student.discount }}</td></tr>
  {% endif %}

  {% if student.tuition_total and student.tuition_total != 0 %}
    <tr><td>Tuition Fee (12 months after discount)</td><td>{{ student.tuition_total }}</td></tr>
  {% endif %}

  {% if student.transport_total and student.transport_total != 0 %}
    <tr><td>Transport Fee (10.5 months)</td><td>{{ student.transport_total }}</td></tr>
  {% endif %}

  {% if student.eclass and student.eclass != 0 %}
    <tr><td>E-Class</td><td>{{ student.eclass }}</td></tr>
  {% endif %}

  {% if student.science and student.science != 0 %}
    <tr><td>Science</td><td>{{ student.science }}</td></tr>
  {% endif %}

  {% if student.computer and student.computer != 0 %}
    <tr><td>Computer</td><td>{{ student.computer }}</td></tr>
  {% endif %}

  {% if student.kgarten and student.kgarten != 0 %}
    <tr><td>K.Garten</td><td>{{ student.kgarten }}</td></tr>
  {% endif %}

  <!-- Totals always show -->
  <tr class="total-row"><td>Total</td><td>{{ student.total_fee }}</td></tr>
  <tr><td>Paid</td><td>{{ student.paid_fee }}</td></tr>
  <tr><td>Balance</td><td>{{ student.balance_fee }}</td></tr>
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
        return redirect(url_for("index"))
    return render_template_string(RECEIPT_HTML, student=student, plain_password=plain_password)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
