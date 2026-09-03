# parent_login.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from pymongo import MongoClient
from types import SimpleNamespace
import razorpay
import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret")

# MongoDB connection
client = MongoClient("mongodb://dakshd:Dhanjal01@localhost:27017/school_db")
school_db = client["school_db"]
master_col = school_db["master"]

# Transactions DB
tran_client = MongoClient("mongodb://dakshdd:Dhanjal99@localhost:27017/tran")
tran_db = tran_client["tran"]
tran_col = tran_db["transactions"]

# Razorpay client
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_SDy9xMyjmCtIEt")
RAZORPAY_KEY_SECRET = os.environ.get(
    "RAZORPAY_KEY_SECRET", "75xgs943MeNtbDqy4PH1p3Fh")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


# ---------------- Helper: Receipt Number ----------------
def get_next_receipt_number():
    counter = tran_db["counters"].find_one_and_update(
        {"_id": "receipt_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return f"REC-{counter['seq']:05d}"   # e.g. REC-00001

# ---------------- LOGIN ----------------


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        adm_code = request.form.get("adm_code").strip()
        password = request.form.get("password")
        record = master_col.find_one({"adm_code": adm_code})
        if record and "password_hash" in record and check_password_hash(record["password_hash"], password):
            session["admission_code"] = adm_code
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid login credentials", "error")
    return render_template("parent_login.html")

# ---------------- DASHBOARD ----------------


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "admission_code" not in session:
        return redirect(url_for("login"))

    adm_code = session["admission_code"]
    record = master_col.find_one({"adm_code": adm_code})
    if not record:
        flash("Student record not found", "error")
        return redirect(url_for("login"))

    # Fee heads
    admission_fee = record.get("admission_fee", 0)
    annual_fee = record.get("annual_fee", 0)
    tuition_fee = record.get("tuition_fee", 0)

    devl_fee = record.get("devl_fee", 0) / 12
    eclass_fee = record.get("eclass", 0) / 12
    science_fee = record.get("science", 0) / 12
    computer_fee = record.get("computer", 0) / 12
    kgarten_fee = record.get("kgarten", 0) / 12
    transport_monthly = record.get("transport_total", 0) / 12

    # Transaction history
    history_cursor = tran_col.find({"adm_code": adm_code}).sort("date", -1)
    history = [SimpleNamespace(**h) for h in history_cursor]
    paid_months = [h.month for h in history if hasattr(h, "month")]

    # All months list
    months = ["April", "May", "June", "July", "August", "September", "October",
              "November", "December", "January", "February", "March"]

    # ✅ Auto select next unpaid month
    selected_month = request.args.get("month")
    if not selected_month:
        for m in months:
            if m not in paid_months:
                selected_month = m
                break
    # Agar sab paid ho gaye to default current month
    if not selected_month:
        selected_month = datetime.datetime.now().strftime("%B")

    # Fee calculation
    if selected_month == "April":
        total = admission_fee + annual_fee + tuition_fee + devl_fee + eclass_fee + \
            science_fee + computer_fee + kgarten_fee + transport_monthly
    else:
        total = tuition_fee + devl_fee + eclass_fee + science_fee + \
            computer_fee + kgarten_fee + transport_monthly

    balance = record.get("balance_fee", total)
    auto_paid = total

    student_obj = SimpleNamespace(**record)
    return render_template(
        "parent_dashboard.html",
        student=student_obj,
        total=total,
        balance=balance,
        auto_paid=auto_paid,
        history=history,
        paid_months=paid_months,
        razorpay_key_id=RAZORPAY_KEY_ID,
        selected_month=selected_month,
        photo=record.get("photo", "")
    )

# ---------------- Razorpay ----------------


@app.route("/create_order", methods=["POST"])
def create_order():
    amount = int(float(request.form.get("paid", 0)) * 100)
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
            selected_month = data.get("month")
            if tran_col.find_one({"adm_code": data["admission_code"], "month": selected_month}):
                return {"status": "error", "message": "Fee for this month already paid"}

            record = master_col.find_one({"adm_code": data["admission_code"]})
            if not record:
                return {"status": "error", "message": "Student not found"}

            # Recalculate expected fee for selected month
            admission_fee = record.get("admission_fee", 0)
            annual_fee = record.get("annual_fee", 0)
            tuition_fee = record.get("tuition_fee", 0)

            devl_fee = record.get("devl_fee", 0) / 12
            eclass_fee = record.get("eclass", 0) / 12
            science_fee = record.get("science", 0) / 12
            computer_fee = record.get("computer", 0) / 12
            kgarten_fee = record.get("kgarten", 0) / 12
            transport_monthly = record.get("transport_total", 0) / 12

            if selected_month == "April":
                expected_paid = admission_fee + annual_fee + tuition_fee + devl_fee + \
                    eclass_fee + science_fee + computer_fee + kgarten_fee + transport_monthly
            else:
                expected_paid = tuition_fee + devl_fee + eclass_fee + \
                    science_fee + computer_fee + kgarten_fee + transport_monthly

            paid = float(data.get("paid", 0))
            if abs(paid - expected_paid) > 1:
                return {"status": "error", "message": f"Invalid amount. Expected {expected_paid}, got {paid}"}

            prev_balance = float(record.get(
                "balance_fee", record.get("total_fee", 0)))
            new_balance = max(prev_balance - paid, 0)

            # ✅ Generate receipt number
            receipt_no = get_next_receipt_number()

            tran_col.insert_one({
                "receipt_no": receipt_no,
                "adm_code": data["admission_code"],
                "student_name": data["student_name"],
                "class": data["class"],
                "father_name": data["father_name"],
                "photo": data["photo"],

                # ✅ Store individual heads
                "admission_fee": admission_fee if selected_month == "April" else 0,
                "annual_fee": annual_fee if selected_month == "April" else 0,
                "tuition_fee": tuition_fee,
                "transport_fee": transport_monthly,
                "devl_fee": devl_fee,
                "eclass": eclass_fee,
                "science": science_fee,
                "computer": computer_fee,
                "kgarten": kgarten_fee,

                # ✅ Totals
                "total_fee": expected_paid,
                "paid": paid,
                "balance": new_balance,

                "month": selected_month,
                "date": datetime.datetime.now(),
                "payment_id": data["payment_id"],
                "order_id": data["order_id"],
                "remark": data.get("remarks", ""),
                "payment_mode": "Online"
            })

            master_col.update_one(
                {"adm_code": data["admission_code"]},
                {"$set": {
                    "paid_fee": record.get("paid_fee", 0) + paid,
                    "balance_fee": new_balance
                }}
            )
            return {"status": "success", "receipt_no": receipt_no}
        else:
            return {"status": "failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ---------------- LOGOUT ----------------


@app.route("/logout")
def logout():
    session.pop("admission_code", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
