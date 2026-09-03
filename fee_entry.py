import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from pymongo import MongoClient, errors
import datetime
from db import master, counters, transport_collection, tran_collection, users_collection, tran_col, master_col

# ------------------ Blueprint Setup ------------------
fee_entry_bp = Blueprint("fee_entry_bp", __name__)
# ------------------ HTML Routes ------------------


@fee_entry_bp.route("/home")
def fee_home():
    return redirect(url_for("fee_entry_bp.fee_entry"))


@fee_entry_bp.route("/", methods=["GET"])
def fee_entry():
    return render_template("fee_entry.html")


@fee_entry_bp.route("/autocomplete")
def autocomplete():
    term = request.args.get("q", "").strip()
    results = []
    if term:
        cursor = master_col.find(
            {
                "$or": [
                    {"student_name": {"$regex": term, "$options": "i"}},
                    {"adm_code": {"$regex": term, "$options": "i"}}
                ]
            },
            {"student_name": 1, "adm_code": 1, "class": 1, "father_name": 1}
        ).limit(10)

        for r in cursor:
            results.append({
                "student_name": r.get("student_name", ""),
                "adm_code": r.get("adm_code", ""),
                "class": r.get("class", ""),
                "father_name": r.get("father_name", "")
            })
    return jsonify(results)


@fee_entry_bp.route("/details")
def student_details():
    adm_code = request.args.get("adm_code")
    r = master_col.find_one({"adm_code": adm_code})
    if not r:
        return jsonify({})
    return jsonify({
        "adm_code": r.get("adm_code", ""),
        "student_name": r.get("student_name", ""),
        "class": r.get("class", ""),
        "father_name": r.get("father_name", ""),
        "total_fee": r.get("total_fee", 0),
        "paid_fee": r.get("paid_fee", 0),
        "balance_fee": r.get("balance_fee", r.get("total_fee", 0))
    })


@fee_entry_bp.route("/month_total")
def month_total():
    adm_code = request.args.get("adm_code")
    month = request.args.get("month", "April")

    student = master_col.find_one({"adm_code": adm_code})
    if not student:
        return jsonify({"error": "Student not found"}), 404

    tuition_monthly = student.get("tuition_fee", 0)
    transport_monthly = student.get("transport_total", 0) / 12
    devl_monthly = student.get("devl_fee", 0) / 12
    eclass_monthly = student.get("eclass", 0) / 12
    science_monthly = student.get("science", 0) / 12
    computer_monthly = student.get("computer", 0) / 12
    kgarten_monthly = student.get("kgarten", 0) / 12

    if month == "April":
        total = (
            student.get("admission_fee", 0) +
            student.get("annual_fee", 0) +
            devl_monthly + eclass_monthly + science_monthly +
            computer_monthly + kgarten_monthly +
            tuition_monthly + transport_monthly
        )
    else:
        total = (
            devl_monthly + eclass_monthly + science_monthly +
            computer_monthly + kgarten_monthly +
            tuition_monthly + transport_monthly
        )

    trans = tran_col.find_one({"adm_code": adm_code, "month": month})
    paid = trans.get("paid", 0) if trans else 0
    balance = total - paid

    return jsonify({"month": month, "total": total, "paid": paid, "balance": balance})


@fee_entry_bp.route("/receive", methods=["POST"])
def receive_payment():
    adm_code = request.form.get("adm_code")
    mode = request.form.get("mode")
    remark = request.form.get("remark", "")
    amount = float(request.form.get("amount", 0))
    month = request.form.get("month")

    record = master_col.find_one({"adm_code": adm_code})
    if not record:
        flash("Student not found.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    # Auto-pick next unpaid month if not provided
    if not month:
        months = ["April", "May", "June", "July", "August", "September",
                  "October", "November", "December", "January", "February", "March"]
        trans = tran_col.find({"adm_code": adm_code}, {"month": 1})
        paid_months = [t.get("month") for t in trans if t.get("month")]
        for m in months:
            if m not in paid_months:
                month = m
                break

    if not month:
        flash("All months already paid.", "success")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    prev_balance = record.get("balance_fee", record.get("total_fee", 0))
    if prev_balance <= 0:
        flash("No outstanding balance left.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    new_balance = max(prev_balance - amount, 0)

    def get_next_receipt_number():
        counter = tran_db["counters"].find_one_and_update(
            {"_id": "receipt_number"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )
        return f"REC-{counter['seq']:05d}"

    receipt_no = get_next_receipt_number()
    tran_col.insert_one({
        "receipt_no": receipt_no,
        "adm_code": adm_code,
        "student_name": record.get("student_name", ""),
        "class": record.get("class", ""),
        "father_name": record.get("father_name", ""),
        "month": month,
        "paid": amount,
        "balance": new_balance,
        "date": datetime.datetime.now(),
        "payment_mode": mode,
        "remark": remark
    })

    master_col.update_one(
        {"adm_code": adm_code},
        {"$set": {
            "paid_fee": record.get("paid_fee", 0) + amount,
            "balance_fee": new_balance,
            f"{month.lower()}_status": "Paid"
        }}
    )

    return render_template("receipt.html",
                           receipt_no=receipt_no,
                           adm_code=adm_code,
                           student_name=record.get("student_name", ""),
                           student_class=record.get("class", ""),
                           father_name=record.get("father_name", ""),
                           payment_mode=mode,
                           remark=remark,
                           date=datetime.datetime.now().strftime("%d-%m-%Y %H:%M"),
                           month=month,
                           paid=round(amount, 2),
                           balance=round(new_balance, 2))


@fee_entry_bp.route("/next_month")
def next_month():
    adm_code = request.args.get("adm_code")
    if not adm_code:
        return jsonify({"error": "Admission code required"}), 400

    months = ["April", "May", "June", "July", "August", "September",
              "October", "November", "December", "January", "February", "March"]

    trans = tran_col.find({"adm_code": adm_code}, {"month": 1})
    paid_months = [t.get("month") for t in trans if t.get("month")]

    next_month = None
    for m in months:
        if m not in paid_months:
            next_month = m
            break

    return jsonify({"next_month": next_month, "paid_months": paid_months})

# ------------------ API Routes ------------------


@fee_entry_bp.route("/api/details/<adm_code>", methods=["GET"])
def api_student_details(adm_code):
    r = master_col.find_one({"adm_code": adm_code})
    if not r:
        return jsonify({"error": "Student not found"}), 404
    return jsonify({
        "adm_code": r.get("adm_code", ""),
        "student_name": r.get("student_name", ""),
        "class": r.get("class", ""),
        "father_name": r.get("father_name", ""),
        "total_fee": r.get("total_fee", 0),
        "paid_fee": r.get("paid_fee", 0),
        "balance_fee": r.get("balance_fee", r.get("total_fee", 0))
    })


@fee_entry_bp.route("/api/month_total", methods=["GET"])
def api_month_total():
    # Reuse HTML month_total logic
    return month_total()


@fee_entry_bp.route("/api/pay", methods=["POST"])
def api_receive_payment():
    data = request.json
    adm_code = data.get("adm_code")
    amount = float(data.get("amount", 0))
    mode = data.get("mode", "Cash")
    month = data.get("month")

    record = master_col.find_one({"adm_code": adm_code})
    if not record:
        return jsonify({"error": "Student not found"}), 404

    prev_balance = record.get("balance_fee", record.get("total_fee", 0))
    if prev_balance <= 0:
        return jsonify({"error": "No outstanding balance"}), 400

    new_balance = max(prev_balance - amount, 0)

    receipt_no = f"REC-{tran_db['counters'].find_one_and_update({'_id': 'receipt_number'}, {'$inc': {'seq': 1}}, upsert=True, return_document=True)['seq']:05d}"

    tran_col.insert_one({
        "receipt_no": receipt_no,
        "adm_code": adm_code,
        "student_name": record.get("student_name", ""),
        "class": record.get("class", ""),
        "father_name": record.get("father_name", ""),
        "month": month,
        "paid": amount,
        "balance": new_balance,
        "date": datetime.datetime.now(),
        "payment_mode": mode
    })

    master_col.update_one(
        {"adm_code": adm_code},
        {"$set": {
            "paid_fee": record.get("paid_fee", 0) + amount,
            "balance_fee": new_balance
        }}
    )

    return jsonify({
        "status": "success",
        "receipt_no": receipt_no,
        "adm_code": adm_code,
        "month": month,
        "paid": amount,
        "balance": new_balance
    })


@fee_entry_bp.route("/api/next_month", methods=["GET"])
def api_next_month():
    # Reuse HTML next_month logic
    return next_month()
