# fee_entry.py
import datetime
from datetime import timezone, timedelta
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from pymongo import ReturnDocument, errors
from db import master_collection, counters_collection, tran_collection, master_col, get_school

IST = timezone(timedelta(hours=5, minutes=30))
fee_entry_bp = Blueprint("fee_entry_bp", __name__)

MONTHS = ["April", "May", "June", "July", "August", "September",
          "October", "November", "December", "January", "February", "March"]


def next_unpaid_month(adm_code):
    paid = {x.get("month") for x in tran_collection.find(
        {"adm_code": adm_code}, {"month": 1}) if x.get("month")}
    return next((m for m in MONTHS if m not in paid), None)


def next_receipt():
    c = counters_collection.find_one_and_update(
        {"_id": "receipt_number"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=ReturnDocument.AFTER
    )
    return f"REC-{c['seq']:05d}"


def month_fee(s, month):
    total = (
        float(s.get("tuition_fee", 0) or 0) +
        float(s.get("transport_total", 0) or 0)/10.5 +
        float(s.get("devl_fee", 0) or 0)/12 +
        float(s.get("eclass", 0) or 0)/12 +
        float(s.get("science", 0) or 0)/12 +
        float(s.get("computer", 0) or 0)/12 +
        float(s.get("kgarten", 0) or 0)/12
    )
    if month == "April":
        total += float(s.get("admission_fee", 0) or 0) + \
            float(s.get("annual_fee", 0) or 0)
    return round(total, 2)


@fee_entry_bp.route("/home")
def fee_home():
    return redirect(url_for("fee_entry_bp.fee_entry"))


@fee_entry_bp.route("/")
def fee_entry():
    return render_template("fee_entry.html", adm_code=request.args.get("adm_code", "").strip())


@fee_entry_bp.route("/autocomplete")
def autocomplete():
    term = request.args.get("q", "").strip()
    results = []
    if term:
        cur = master_col.find(
            {"$or": [
                {"student_name": {"$regex": term, "$options": "i"}},
                {"adm_code": {"$regex": term, "$options": "i"}}
            ]},
            {"student_name": 1, "adm_code": 1, "class": 1, "father_name": 1}
        ).limit(10)

        results = [{
            "student_name": r.get("student_name", ""),
            "adm_code": r.get("adm_code", ""),
            "class": r.get("class", ""),
            "father_name": r.get("father_name", "")
        } for r in cur]

    return jsonify(results)


@fee_entry_bp.route("/details")
def student_details():
    r = master_col.find_one({"adm_code": request.args.get("adm_code")})
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
    adm = request.args.get("adm_code")
    month = request.args.get("month", "April")
    s = master_col.find_one({"adm_code": adm})

    if not s:
        return jsonify({"error": "Student not found"}), 404

    total = month_fee(s, month)
    t = tran_collection.find_one({"adm_code": adm, "month": month})
    paid = float(t.get("paid", 0) or 0) if t else 0

    return jsonify({
        "month": month, "total": total,
        "paid": round(paid, 2),
        "balance": round(max(total-paid, 0), 2)
    })


@fee_entry_bp.route("/receive", methods=["POST"])
def receive_payment():

    adm = request.form.get("adm_code", "").strip()
    month = request.form.get("month", "").strip()
    mode = request.form.get("mode", "Cash").strip()
    remark = request.form.get("remark", "").strip()

    try:
        amount = float(request.form.get("amount", 0))
    except:
        amount = 0

    if not adm:
        flash("Admission code is required.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    if amount <= 0:
        flash("Please enter a valid payment amount.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    s = master_col.find_one({"adm_code": adm})

    if not s:
        flash("Student not found.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    month = month or next_unpaid_month(adm)

    if not month:
        flash("All months are already paid.", "success")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    if month not in MONTHS:
        flash("Invalid month selected.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    existing = tran_collection.find_one({"adm_code": adm, "month": month})

    if existing:
        flash(
            f"{month} fee is already paid. Receipt No: {existing.get('receipt_no', '')}", "warning")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    prev = float(s.get("balance_fee", s.get("total_fee", 0)) or 0)

    if prev <= 0:
        flash("No outstanding balance left.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    if amount > prev:
        flash(
            f"Payment cannot be greater than outstanding balance ₹{prev:.2f}.", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    balance = max(prev-amount, 0)
    receipt = next_receipt()

    transaction = {
        "receipt_no": receipt, "adm_code": adm,
        "student_name": s.get("student_name", ""),
        "class": s.get("class", ""),
        "father_name": s.get("father_name", ""),
        "month": month,
        "admission_fee": float(s.get("admission_fee", 0) or 0) if month == "April" else 0,
        "annual_fee": float(s.get("annual_fee", 0) or 0) if month == "April" else 0,
        "tuition_fee": float(s.get("tuition_fee", 0) or 0),
        "transport_fee": round(float(s.get("transport_total", 0) or 0)/10.5, 2),
        "devl_fee": round(float(s.get("devl_fee", 0) or 0)/12, 2),
        "eclass": round(float(s.get("eclass", 0) or 0)/12, 2),
        "science": round(float(s.get("science", 0) or 0)/12, 2),
        "computer": round(float(s.get("computer", 0) or 0)/12, 2),
        "kgarten": round(float(s.get("kgarten", 0) or 0)/12, 2),
        "month_total": month_fee(s, month),
        "paid": round(amount, 2),
        "balance": round(balance, 2),
        "date": datetime.datetime.now(IST).replace(tzinfo=None),
        "payment_mode": mode, "remark": remark
    }

    try:
        tran_collection.insert_one(transaction)
    except errors.DuplicateKeyError:
        existing = tran_collection.find_one({"adm_code": adm, "month": month})
        flash(f"{month} fee is already paid. Receipt No: {existing.get('receipt_no', '') if existing else ''}", "warning")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    master_col.update_one(
        {"adm_code": adm},
        {"$set": {
            "paid_fee": round(float(s.get("paid_fee", 0) or 0)+amount, 2),
            "balance_fee": round(balance, 2),
            f"{month.lower()}_status": "Paid"
        }}
    )

    school = get_school() or {}

    return render_template(
        "receipt.html",
        school_name=school.get("school_name", ""),
        school_address=school.get("address", ""),
        school_phone=school.get("phone", ""),
        receipt_no=receipt, adm_code=adm,
        student_name=s.get("student_name", ""),
        student_class=s.get("class", ""),
        section=s.get("section", ""),
        father_name=s.get("father_name", ""),
        payment_mode=mode, remark=remark,
        date=datetime.datetime.now(IST).strftime("%d-%m-%Y %H:%M"),
        month=month, paid=round(amount, 2), balance=round(balance, 2),
        admission_fee=transaction["admission_fee"],
        annual_fee=transaction["annual_fee"],
        tuition_fee=transaction["tuition_fee"],
        transport_fee=transaction["transport_fee"],
        devl_fee=transaction["devl_fee"],
        eclass=transaction["eclass"],
        science=transaction["science"],
        computer=transaction["computer"],
        kgarten=transaction["kgarten"]
    )


@fee_entry_bp.route("/next_month")
def next_month():
    adm = request.args.get("adm_code")
    if not adm:
        return jsonify({"error": "Admission code required"}), 400

    paid = [x.get("month") for x in tran_collection.find(
        {"adm_code": adm}, {"month": 1}) if x.get("month")]

    return jsonify({
        "next_month": next_unpaid_month(adm),
        "paid_months": paid
    })


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

    adm = str(data.get("adm_code", "")).strip()
    month = str(data.get("month", "")).strip()
    mode = str(data.get("mode", "Cash")).strip()

    try:
        amount = float(data.get("amount", 0))
    except:
        amount = 0

    if not adm:
        return jsonify({"error": "Admission code required"}), 400

    if amount <= 0:
        return jsonify({"error": "Invalid payment amount"}), 400

    s = master_col.find_one({"adm_code": adm})

    if not s:
        return jsonify({"error": "Student not found"}), 404

    month = month or next_unpaid_month(adm)

    if not month:
        return jsonify({"error": "All months are already paid"}), 400

    existing = tran_collection.find_one({"adm_code": adm, "month": month})

    if existing:
        return jsonify({
            "error": f"{month} fee already received",
            "receipt_no": existing.get("receipt_no", "")
        }), 400

    prev = float(s.get("balance_fee", s.get("total_fee", 0)) or 0)

    if prev <= 0:
        return jsonify({"error": "No outstanding balance"}), 400

    if amount > prev:
        return jsonify({
            "error": f"Payment cannot exceed balance ₹{prev:.2f}"
        }), 400

    balance = max(prev-amount, 0)
    receipt = next_receipt()

    try:
        tran_collection.insert_one({
            "receipt_no": receipt,
            "adm_code": adm,
            "student_name": s.get("student_name", ""),
            "class": s.get("class", ""),
            "father_name": s.get("father_name", ""),
            "month": month,
            "paid": round(amount, 2),
            "balance": round(balance, 2),
            "date": datetime.datetime.now(IST).replace(tzinfo=None),
            "payment_mode": mode
        })
    except errors.DuplicateKeyError:
        existing = tran_collection.find_one({"adm_code": adm, "month": month})
        return jsonify({
            "error": f"{month} fee already received",
            "receipt_no": existing.get("receipt_no", "") if existing else ""
        }), 400

    master_col.update_one(
        {"adm_code": adm},
        {"$set": {
            "paid_fee": round(float(s.get("paid_fee", 0) or 0)+amount, 2),
            "balance_fee": round(balance, 2),
            f"{month.lower()}_status": "Paid"
        }}
    )

    return jsonify({
        "status": "success",
        "receipt_no": receipt,
        "adm_code": adm,
        "month": month,
        "paid": round(amount, 2),
        "balance": round(balance, 2)
    })


@fee_entry_bp.route("/api/next_month")
def api_next_month():
    return next_month()
