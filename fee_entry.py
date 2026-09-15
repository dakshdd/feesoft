import datetime
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from pymongo import ReturnDocument, errors
from db import master_collection, counters_collection, tran_collection, master_col

fee_entry_bp = Blueprint("fee_entry_bp", __name__)

MONTHS = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
]


def next_unpaid_month(adm_code):
    paid = {
        x.get("month")
        for x in tran_collection.find({"adm_code": adm_code}, {"month": 1})
        if x.get("month")
    }
    return next((m for m in MONTHS if m not in paid), None)


def next_receipt():
    counter = counters_collection.find_one_and_update(
        {"_id": "receipt_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return f"REC-{counter['seq']:05d}"


def month_fee(student, month):
    tuition = float(student.get("tuition_fee", 0) or 0)
    transport = float(student.get("transport_total", 0) or 0) / 12
    devl = float(student.get("devl_fee", 0) or 0) / 12
    eclass = float(student.get("eclass", 0) or 0) / 12
    science = float(student.get("science", 0) or 0) / 12
    computer = float(student.get("computer", 0) or 0) / 12
    kgarten = float(student.get("kgarten", 0) or 0) / 12

    total = devl + eclass + science + computer + kgarten + tuition + transport

    if month == "April":
        total += (
            float(student.get("admission_fee", 0) or 0) +
            float(student.get("annual_fee", 0) or 0)
        )

    return round(total, 2)


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
            {"$or": [
                {"student_name": {"$regex": term, "$options": "i"}},
                {"adm_code": {"$regex": term, "$options": "i"}}
            ]},
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

    total = month_fee(student, month)

    trans = tran_collection.find_one({
        "adm_code": adm_code,
        "month": month
    })

    paid = float(trans.get("paid", 0) or 0) if trans else 0

    return jsonify({
        "month": month,
        "total": total,
        "paid": round(paid, 2),
        "balance": round(max(total - paid, 0), 2)
    })


@fee_entry_bp.route("/receive", methods=["POST"])
def receive_payment():

    adm_code = request.form.get("adm_code", "").strip()
    month = request.form.get("month", "").strip()
    mode = request.form.get("mode", "Cash").strip()
    remark = request.form.get("remark", "").strip()

    try:
        amount = float(request.form.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0

    if not adm_code:
        flash("Admission code is required.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    if amount <= 0:
        flash("Please enter a valid payment amount.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    record = master_col.find_one({"adm_code": adm_code})

    if not record:
        flash("Student not found.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    if not month:
        month = next_unpaid_month(adm_code)

    if not month:
        flash("All months are already paid.", "success")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    if month not in MONTHS:
        flash("Invalid month selected.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    existing = tran_collection.find_one({
        "adm_code": adm_code,
        "month": month
    })

    if existing:
        flash(
            f"{month} fee is already paid. Receipt No: {existing.get('receipt_no', '')}",
            "warning"
        )
        return redirect(url_for("fee_entry_bp.fee_entry"))

    prev_balance = float(
        record.get("balance_fee", record.get("total_fee", 0)) or 0
    )

    if prev_balance <= 0:
        flash("No outstanding balance left.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    if amount > prev_balance:
        flash(
            f"Payment cannot be greater than outstanding balance ₹{prev_balance:.2f}.",
            "error"
        )
        return redirect(url_for("fee_entry_bp.fee_entry"))

    new_balance = max(prev_balance - amount, 0)
    receipt_no = next_receipt()

    transaction = {
        "receipt_no": receipt_no,
        "adm_code": adm_code,
        "student_name": record.get("student_name", ""),
        "class": record.get("class", ""),
        "father_name": record.get("father_name", ""),
        "month": month,
        "paid": round(amount, 2),
        "balance": round(new_balance, 2),
        "date": datetime.datetime.now(),
        "payment_mode": mode,
        "remark": remark
    }

    try:
        tran_collection.insert_one(transaction)
    except errors.DuplicateKeyError:
        existing = tran_collection.find_one({
            "adm_code": adm_code,
            "month": month
        })
        flash(
            f"{month} fee is already paid. Receipt No: {existing.get('receipt_no', '') if existing else ''}",
            "warning"
        )
        return redirect(url_for("fee_entry_bp.fee_entry"))

    master_col.update_one(
        {"adm_code": adm_code},
        {"$set": {
            "paid_fee": round(float(record.get("paid_fee", 0) or 0) + amount, 2),
            "balance_fee": round(new_balance, 2),
            f"{month.lower()}_status": "Paid"
        }}
    )

    return render_template(
        "receipt.html",

        # Student details
        receipt_no=receipt_no,
        adm_code=adm_code,
        student_name=record.get("student_name", ""),
        student_class=record.get("class", ""),
        section=record.get("section", ""),
        father_name=record.get("father_name", ""),

        # Payment details
        payment_mode=mode,
        remark=remark,
        date=datetime.datetime.now().strftime("%d-%m-%Y %H:%M"),
        month=month,
        paid=round(amount, 2),
        balance=round(new_balance, 2),

        # Fee details
        admission_fee=record.get("admission_fee", 0),
        annual_fee=record.get("annual_fee", 0),
        tuition_fee=record.get("tuition_fee", 0),

        transport_fee=record.get(
            "transport_fee",
            record.get("transport_total", 0)
        ),

        devl_fee=record.get("devl_fee", 0),
        eclass=record.get("eclass", 0),
        science=record.get("science", 0),
        computer=record.get("computer", 0),
        kgarten=record.get("kgarten", 0)
    )


@fee_entry_bp.route("/next_month")
def next_month():
    adm_code = request.args.get("adm_code")

    if not adm_code:
        return jsonify({"error": "Admission code required"}), 400

    paid = [
        x.get("month")
        for x in tran_collection.find(
            {"adm_code": adm_code},
            {"month": 1}
        )
        if x.get("month")
    ]

    return jsonify({
        "next_month": next_unpaid_month(adm_code),
        "paid_months": paid
    })


# ========================= API =========================

@fee_entry_bp.route("/api/details/<adm_code>")
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


@fee_entry_bp.route("/api/month_total")
def api_month_total():
    return month_total()


@fee_entry_bp.route("/api/pay", methods=["POST"])
def api_receive_payment():

    data = request.get_json(silent=True) or {}

    adm_code = str(data.get("adm_code", "")).strip()
    month = str(data.get("month", "")).strip()
    mode = str(data.get("mode", "Cash")).strip()

    try:
        amount = float(data.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0

    if not adm_code:
        return jsonify({"error": "Admission code required"}), 400

    if amount <= 0:
        return jsonify({"error": "Invalid payment amount"}), 400

    record = master_col.find_one({"adm_code": adm_code})

    if not record:
        return jsonify({"error": "Student not found"}), 404

    if not month:
        month = next_unpaid_month(adm_code)

    if not month:
        return jsonify({"error": "All months are already paid"}), 400

    existing = tran_collection.find_one({
        "adm_code": adm_code,
        "month": month
    })

    if existing:
        return jsonify({
            "error": f"{month} fee already received",
            "receipt_no": existing.get("receipt_no", "")
        }), 400

    prev_balance = float(
        record.get("balance_fee", record.get("total_fee", 0)) or 0
    )

    if prev_balance <= 0:
        return jsonify({"error": "No outstanding balance"}), 400

    if amount > prev_balance:
        return jsonify({
            "error": f"Payment cannot exceed balance ₹{prev_balance:.2f}"
        }), 400

    new_balance = max(prev_balance - amount, 0)
    receipt_no = next_receipt()

    try:
        tran_collection.insert_one({
            "receipt_no": receipt_no,
            "adm_code": adm_code,
            "student_name": record.get("student_name", ""),
            "class": record.get("class", ""),
            "father_name": record.get("father_name", ""),
            "month": month,
            "paid": round(amount, 2),
            "balance": round(new_balance, 2),
            "date": datetime.datetime.now(),
            "payment_mode": mode
        })
    except errors.DuplicateKeyError:
        existing = tran_collection.find_one({
            "adm_code": adm_code,
            "month": month
        })
        return jsonify({
            "error": f"{month} fee already received",
            "receipt_no": existing.get("receipt_no", "") if existing else ""
        }), 400

    master_col.update_one(
        {"adm_code": adm_code},
        {"$set": {
            "paid_fee": round(float(record.get("paid_fee", 0) or 0) + amount, 2),
            "balance_fee": round(new_balance, 2),
            f"{month.lower()}_status": "Paid"
        }}
    )

    return jsonify({
        "status": "success",
        "receipt_no": receipt_no,
        "adm_code": adm_code,
        "month": month,
        "paid": round(amount, 2),
        "balance": round(new_balance, 2)
    })


@fee_entry_bp.route("/api/next_month")
def api_next_month():
    return next_month()
