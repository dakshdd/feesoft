from flask import Flask, request, render_template_string, redirect, url_for, flash, jsonify
from pymongo import MongoClient
import datetime
import json
import os
import razorpay

app = Flask(__name__)
app.secret_key = "rzp_test_SDy9xMyjmCtIEt"

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
school_db = client["school_db"]
master_col = school_db["master"]

tran_db = client["tran"]
tran_col = tran_db["transactions"]

DATA_FILE = "fee_data.json"

# Razorpay client
razorpay_client = razorpay.Client(
    auth=("rzp_test_SDy9xMyjmCtIEt", "75xgs943MeNtbDqy4PH1p3Fh"))


def load_fee_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------- TEMPLATE ----------------
TEMPLATE = """ 
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Fee Entry</title>
  <style>
    body { font-family: Arial, sans-serif; background:#f4f4f4; margin:0; padding:20px; }
    .card { background:#fff; padding:20px; border-radius:8px; max-width:750px; margin:auto; }
    h2 { margin-top:0; }
    label { display:block; margin-top:10px; }
    input, select, button { padding:8px; width:100%; margin-top:5px; }
    table { width:100%; border-collapse:collapse; margin-top:20px; }
    th, td { border:1px solid #ccc; padding:8px; text-align:left; }
    img { border:1px solid #ccc; border-radius:5px; margin-top:5px; }
    .success { background:#d1fae5; padding:10px; margin-top:10px; border-radius:5px; }
    .error { background:#fecaca; padding:10px; margin-top:10px; border-radius:5px; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Fee Entry</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, msg in messages %}
          <div class="{{ 'error' if category == 'error' else 'success' }}">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form method="post" action="{{ url_for('fee_entry') }}">
      <label>Admission Code</label>
      <input type="text" name="admission_code" required>
      <button type="submit">Fetch Fee Details</button>
    </form>

    {% if student %}
    <h3>Student Details</h3>
    <table>
        <tr><th>Student Name</th><td>{{ student.student_name }}</td></tr>
        <tr><th>Class</th><td>{{ student.class }}</td></tr>
        <tr><th>Father Name</th><td>{{ student.father_name }}</td></tr>
        <tr><th>Transport Charges</th><td>{{ student.transport_charges }}</td></tr>
        <tr><th>Photo</th>
         <td>
            {% if student.photo %}
                <img src="{{ url_for('static', filename=student.photo if 'uploads/' in student.photo else 'uploads/' + student.photo) }}"
                    alt="Student Photo" width="120" height="150">
            {% else %}
                No photo available
            {% endif %}
         </td>
        </tr>
    </table>

    <h3>Fee / Balance Details</h3>
    <table>
      <tr><th>Total Fee</th><td>{{ total }}</td></tr>
      <tr><th>Outstanding Balance</th><td>{{ balance }}</td></tr>
    </table>

    <form id="saveForm" method="post" action="{{ url_for('save_transaction') }}">
      <input type="hidden" name="admission_code" value="{{ admission_code }}">
      <input type="hidden" name="student_name" value="{{ student.student_name }}">
      <input type="hidden" name="class" value="{{ student.class }}">
      <input type="hidden" name="father_name" value="{{ student.father_name }}">
      <input type="hidden" name="photo" value="{{ student.photo }}">
      <input type="hidden" name="balance" value="{{ balance }}">
      <input type="hidden" name="total" value="{{ total }}">
      <input type="hidden" name="auto_paid" value="{{ auto_paid }}">

      <label>Month</label>
      <select name="month" required>
        {% for m in ["April","May","June","July","August","September","October","November","December","January","February","March"] %}
          <option value="{{m}}" {% if paid_months and m in paid_months %}disabled{% endif %}>{{m}}</option>
        {% endfor %}
      </select>

      <label>Paid Amount (Auto)</label>
      <input type="number" step="0.01" min="0" name="paid" value="{{ auto_paid }}" readonly>

      <button type="button" onclick="openRazorpay()">Pay & Save Transaction</button>
    </form>

    {% if history %}
    <h3>Transaction History</h3>
    <table>
      <tr>
        <th>Date</th><th>Month</th><th>Paid</th><th>Balance</th>
      </tr>
      {% for h in history %}
      <tr>
        <td>{{ h.date.strftime("%d-%m-%Y %H:%M") }}</td>
        <td>{{ h.month }}</td>
        <td>{{ h.paid }}</td>
        <td>{{ h.balance }}</td>
      </tr>
      {% endfor %}
    </table>
    {% endif %}
    {% endif %}
  </div>

<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<script>
function openRazorpay() {
    let form = document.getElementById("saveForm");
    let amount = form.querySelector("input[name='paid']").value;
    let admissionCode = form.querySelector("input[name='admission_code']").value;

    fetch("{{ url_for('create_order') }}", {   // ✅ ensures correct path
        method: "POST",
        body: new FormData(form)
    })
    .then(res => res.json())
    .then(data => {
        var options = {
            "key": "rzp_test_SDy9xMyjmCtIEt",
            "amount": amount * 100,
            "currency": "INR",
            "name": "School Fee Payment",
            "order_id": data.order_id,
            "handler": function (response){
                fetch("{{ url_for('verify_payment') }}", {   // ✅ ensures correct path
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        payment_id: response.razorpay_payment_id,
                        order_id: response.razorpay_order_id,
                        signature: response.razorpay_signature,
                        admission_code: admissionCode
                    })
                }).then(res => res.json())
                  .then(result => {
                      if(result.status === "success"){
                          alert("Payment successful and transaction saved!");
                          window.location.href = "{{ url_for('fee_entry') }}";
                      } else {
                          alert("Payment verification failed!");
                      }
                  });
            }
        };
        var rzp = new Razorpay(options);
        rzp.open();
    });
}
</script>

</body>
</html>
"""


# ---------------- ROUTES ----------------
@app.route("/", methods=["GET", "POST"])
def fee_entry():
    total = None
    balance = None
    admission_code = None
    student = None
    history = None
    auto_paid = None
    paid_months = []

    if request.method == "POST":
        admission_code = request.form.get("admission_code").strip()
        record = master_col.find_one({"adm_code": admission_code})
        if record:
            student = {
                "student_name": record.get("student_name", ""),
                "class": record.get("class", ""),
                "father_name": record.get("father_name", ""),
                "photo": record.get("photo", ""),
                "transport_charges": record.get("transport_charges", 0)
            }

            fee_data = load_fee_data()
            class_name = student["class"]

            # Check last transaction
            last_tran = tran_col.find_one(
                {"adm_code": admission_code}, sort=[("date", -1)])
            if last_tran:
                total = last_tran.get("total_fee", 0)
                balance = last_tran.get("balance", 0)
                if class_name in fee_data:
                    fees = fee_data[class_name]
                    auto_paid = fees.get("tuition", 0) + \
                        student["transport_charges"]
            else:
                if class_name in fee_data:
                    fees = fee_data[class_name]
                    transport_charge = student["transport_charges"]

                    total = fees.get("admission", 0) + fees.get("annual", 0) + \
                        fees.get("examination", 0) + (12 *
                                                      fees.get("tuition", 0)) + (11 * transport_charge)

                    balance = total

                    auto_paid = fees.get("admission", 0) + fees.get("annual", 0) + \
                        fees.get("examination", 0) + \
                        fees.get("tuition", 0) + transport_charge
                else:
                    flash(
                        f"Class '{class_name}' not found in fee_data.json.", "error")

            # Fetch history
            history_cursor = tran_col.find(
                {"adm_code": admission_code}).sort("date", -1)
            history = [type("H", (), h) for h in history_cursor]
            paid_months = [h.month for h in history if hasattr(h, "month")]

        else:
            flash("Admission code not found in master data.", "error")

    student_obj = type("S", (), student) if student else None
    return render_template_string(TEMPLATE,
                                  total=total, balance=balance,
                                  admission_code=admission_code, student=student_obj,
                                  history=history, auto_paid=auto_paid,
                                  paid_months=paid_months)


# ---------------- Razorpay Routes ----------------
@app.route("/create_order", methods=["POST"])
def create_order():
    amount = int(float(request.form.get("paid", 0)) * 100)  # convert to paise
    admission_code = request.form.get("admission_code")

    order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    return jsonify({"order_id": order["id"], "admission_code": admission_code})


@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    data = request.get_json()
    try:
        params_dict = {
            "razorpay_order_id": data["order_id"],
            "razorpay_payment_id": data["payment_id"],
            "razorpay_signature": data["signature"]
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        payment = razorpay_client.payment.fetch(data["payment_id"])
        if payment["status"] == "captured":
            new_balance = max(float(data["balance"]) - float(data["paid"]), 0)

            tran_col.insert_one({
                "adm_code": data["admission_code"],
                "student_name": data["student_name"],
                "class": data["class"],
                "father_name": data["father_name"],
                "photo": data["photo"],
                "total_fee": float(data["total"]),
                "paid": float(data["paid"]),
                "balance": new_balance,
                "month": data["month"],
                "date": datetime.datetime.now(),
                "payment_id": data["payment_id"],
                "order_id": data["order_id"]
            })
            return {"status": "success"}
        else:
            return {"status": "failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------- Save Transaction ----------------


@app.route("/save", methods=["POST"])
def save_transaction():
    admission_code = request.form.get("admission_code")
    student_name = request.form.get("student_name")
    student_class = request.form.get("class")
    father_name = request.form.get("father_name")
    photo = request.form.get("photo")
    total = float(request.form.get("total", 0))
    prev_balance = float(request.form.get("balance", 0))
    paid = float(request.form.get("paid", 0))  # auto value
    month = request.form.get("month")

    if prev_balance <= 0:
        flash("No outstanding balance left.", "error")
        return redirect(url_for("fee_entry"))

    new_balance = max(prev_balance - paid, 0)

    tran_col.insert_one({
        "adm_code": admission_code,
        "student_name": student_name,
        "class": student_class,
        "father_name": father_name,
        "photo": photo,
        "total_fee": total,
        "paid": paid,
        "balance": new_balance,
        "month": month,
        "date": datetime.datetime.now()
    })

    flash(
        f"Transaction saved for {month}: Paid ₹{paid}, Remaining Balance ₹{new_balance}", "success")
    return redirect(url_for("fee_entry"))


# ---------------- Run App ----------------
if __name__ == "__main__":
    # For deployment you can change host/port
    app.run(host="0.0.0.0", port=5000, debug=True)
