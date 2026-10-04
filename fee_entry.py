from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from db import master_collection, counters_collection, tran_collection, master_col, get_school
from pymongo import ReturnDocument
from datetime import timezone, timedelta
import datetime

IST = timezone(timedelta(hours=5, minutes=30))
fee_entry_bp = Blueprint("fee_entry_bp", __name__)
MONTHS = ["April", "May", "June", "July", "August", "September",
          "October", "November", "December", "January", "February", "March"]
HEADS = ["admission_fee", "annual_fee", "tuition_fee", "transport_fee",
         "devl_fee", "eclass", "science", "computer", "kgarten"]


def money(v):
    try:
        return round(float(v or 0), 2)
    except:
        return 0.0


def month_paid(adm, m):
    n = 0
    for t in tran_collection.find({"adm_code": adm}, {"month": 1, "months": 1, "month_details": 1, "paid": 1, "paid_amount": 1}):
        md = t.get("month_details", {})
        if m in md:
            n += money(md[m].get("paid", 0))
        elif t.get("month") == m:
            n += money(t.get("paid_amount", t.get("paid", 0)))
        elif m in t.get("months", []) and not md:
            n += money(t.get("paid_amount", t.get("paid", 0)))
    return round(n, 2)


def month_head_paid(adm, m):
    out = {h: 0 for h in HEADS}
    for t in tran_collection.find({"adm_code": adm}, {"month_details": 1}):
        x = t.get("month_details", {}).get(m, {})
        for h in HEADS:
            z = x.get("heads", {}).get(h)
            if isinstance(z, dict):
                out[h] += money(z.get("paid", 0))
            elif isinstance(x.get(h), dict):
                out[h] += money(x[h].get("paid", 0))
    return {h: round(v, 2) for h, v in out.items()}


def month_detail(s, m):
    tr = money(s.get("transport_charges"))
    if m == "May":
        tr /= 2
    elif m == "June":
        tr = 0
    d = {
        "admission_fee": money(s.get("admission_fee")) if m == "April" else 0,
        "annual_fee": money(s.get("annual_fee")) if m == "April" else 0,
        "tuition_fee": money(s.get("tuition_fee")),
        "transport_fee": round(tr, 2),
        "devl_fee": round(money(s.get("devl_fee"))/12, 2),
        "eclass": round(money(s.get("eclass"))/12, 2),
        "science": round(money(s.get("science"))/12, 2),
        "computer": round(money(s.get("computer"))/12, 2),
        "kgarten": round(money(s.get("kgarten"))/12, 2)}
    d["total"] = round(sum(d.values()), 2)
    return d


def paid_months(adm):
    s = master_col.find_one({"adm_code": adm})
    if not s:
        return set()
    return {m for m in MONTHS if month_detail(s, m)["total"] > 0 and month_paid(adm, m) >= month_detail(s, m)["total"]}


def next_unpaid_month(adm):
    p = paid_months(adm)
    return next((m for m in MONTHS if m not in p), None)


def next_receipt():
    c = counters_collection.find_one_and_update({"_id": "receipt_number"}, {
                                                "$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    return f"REC-{c['seq']:05d}"


def late_fine(m, dt=None):
    if not dt:
        return 0
    i = MONTHS.index(m)
    mn = i+4
    if mn > 12:
        mn -= 12
    y = dt.year
    if mn >= 4 and dt.month < 4:
        y -= 1
    due = datetime.date(y, mn, 10)
    pay = dt.date() if hasattr(dt, "date") else dt
    return round(max((pay-due).days, 0)*5, 2)


def build_receipt_data(t):
    months = t.get("months") or ([t["month"]] if t.get("month") else [])
    ht = t.get("head_totals") or {}
    total = round(sum(money(ht.get(h, 0)) for h in HEADS), 2)
    if total <= 0:
        total = money(t.get("amount_paid", t.get("month_total", 0)))
    paid = money(t.get("paid_amount", t.get("paid", 0)))
    bal = money(t.get("balance_amount", t.get("balance", 0)))
    bp = t.get("is_balance_payment", False)
    return {
        "receipt_no": t.get("receipt_no", ""), "adm_code": t.get("adm_code", ""),
        "student_name": t.get("student_name", ""), "student_class": t.get("class", ""),
        "section": t.get("section", t.get("sec", "")), "father_name": t.get("father_name", ""),
        "months": months, "head_totals": ht, "month_total": total, "total_fee": total,
        "amount_paid": paid, "paid_amount": paid, "balance_amount": bal,
        "student_balance": money(t.get("student_balance", 0)),
        "is_balance_payment": bp,
        "payment_type": t.get("payment_type", "New Payment"),
        "late_fee": 0 if bp else money(t.get("late_fee", 0)),
        "auto_late_fee": 0 if bp else money(t.get("auto_late_fee", 0)),
        "late_fee_details": {} if bp else t.get("late_fee_details", {}),
        "payment_mode": t.get("payment_mode", "Cash"),
        "remark": t.get("remark", ""), "date": t.get("date", "")}


def save_payment(adm, months, amount, mode, remark, late_fee_value=None):
    s = master_col.find_one({"adm_code": adm})
    if not s:
        return None, "Student not found"

    months = [m for m in MONTHS if m in set(months)]
    if not months:
        return None, "Please select at least one month"

    details = {}
    heads_total = {h: 0.0 for h in HEADS}

    for m in months:
        original = month_detail(s, m)
        already = month_paid(adm, m)
        outstanding = round(max(original["total"] - already, 0), 2)

        if outstanding <= 0:
            continue

        hp = month_head_paid(adm, m)
        heads = {}

        for h in HEADS:
            total = money(original[h])
            prev = money(hp.get(h, 0))
            bal = round(max(total - prev, 0), 2)

            if bal > 0:
                heads[h] = {
                    "total": total,
                    "paid_before": prev,
                    "paid": 0.0,
                    "balance": bal
                }
                heads_total[h] = round(heads_total[h] + bal, 2)

        details[m] = {
            "original_total": original["total"],
            "already_paid": already,
            "heads": heads,
            "total": outstanding,
            "paid": 0.0,
            "balance": outstanding
        }

    if not details:
        return None, "Selected months are already fully paid"

    due = round(sum(d["balance"] for d in details.values()), 2)
    paid = money(amount)

    if paid <= 0:
        return None, "Please enter Paid Amount"

    if paid > due:
        return None, "Paid Amount cannot be greater than Amount Due"

    student_balance = money(
        s.get("balance_fee", s.get("total_fee", 0))
    )

    if paid > student_balance:
        return None, "Paid Amount cannot be greater than student balance"

    dt = datetime.datetime.now(IST).replace(tzinfo=None)
    new_balance = round(max(student_balance - paid, 0), 2)
    balance = round(max(due - paid, 0), 2)

    # CHECK IF THIS IS PAYMENT OF PREVIOUS PARTIAL BALANCE
    is_balance = any(
        money(d["already_paid"]) > 0
        for d in details.values()
    )

    # =========================================================
    # BALANCE PAYMENT
    # =========================================================
    if is_balance:

        remaining = paid
        paid_heads = {h: 0.0 for h in HEADS}

        for m, d in details.items():

            if remaining <= 0:
                break

            mp = min(remaining, money(d["balance"]))

            d["paid"] = round(mp, 2)
            d["balance"] = round(
                max(d["balance"] - mp, 0), 2
            )

            r = mp

            for h in HEADS:
                hb = money(
                    d["heads"].get(h, {}).get("balance", 0)
                )

                hp = min(r, hb)

                if h in d["heads"]:
                    d["heads"][h]["paid"] = round(hp, 2)

                paid_heads[h] = round(
                    paid_heads[h] + hp, 2
                )

                r = round(r - hp, 2)

                if r <= 0:
                    break

            remaining = round(
                remaining - mp, 2
            )

        t = {
            "receipt_no": next_receipt(),
            "adm_code": adm,
            "student_name": s.get("student_name", ""),
            "class": s.get("class", ""),
            "section": s.get("section", s.get("sec", "")),
            "father_name": s.get("father_name", ""),
            "months": list(details),
            "month_details": details,
            "head_totals": heads_total,
            "paid_head_totals": paid_heads,
            "amount_paid": due,
            "paid_amount": paid,
            "paid": paid,
            "balance_amount": balance,
            "balance": balance,
            "student_balance": new_balance,
            "is_balance_payment": True,
            "payment_type": "Balance Payment",
            "late_fee": 0,
            "auto_late_fee": 0,
            "date": dt,
            "payment_mode": mode,
            "remark": remark,
            "month": list(details)[0]
            if len(details) == 1 else None
        }

        try:
            tran_collection.insert_one(t)

            sets = {
                "balance_fee": new_balance
            }

            for m, d in details.items():
                sets[f"{m.lower()}_status"] = (
                    "Paid"
                    if d["balance"] <= 0
                    else "Partial"
                    if d["paid"] > 0
                    else "Unpaid"
                )

            for h, v in paid_heads.items():
                if v:
                    sets[f"{h}_paid"] = round(
                        money(s.get(f"{h}_paid", 0)) + v,
                        2
                    )

            master_col.update_one(
                {"adm_code": adm},
                {
                    "$inc": {"paid_fee": paid},
                    "$set": sets
                }
            )

        except Exception as e:
            return None, f"Payment save failed: {e}"

        return t, None

    # =========================================================
    # NORMAL / NEW PAYMENT
    # =========================================================

    remaining = paid
    paid_heads = {h: 0.0 for h in HEADS}

    for m, d in details.items():

        if remaining <= 0:
            break

        mp = min(
            remaining,
            money(d["balance"])
        )

        d["paid"] = round(mp, 2)
        d["balance"] = round(
            max(d["balance"] - mp, 0), 2
        )

        r = mp

        for h in HEADS:

            hb = money(
                d["heads"].get(h, {}).get("balance", 0)
            )

            hp = min(r, hb)

            if h in d["heads"]:
                d["heads"][h]["paid"] = round(
                    hp, 2
                )

            paid_heads[h] = round(
                paid_heads[h] + hp, 2
            )

            r = round(r - hp, 2)

            if r <= 0:
                break

        remaining = round(
            remaining - mp, 2
        )

    auto_fine = round(
        sum(late_fine(m, dt) for m in details),
        2
    )

    final_fine = (
        max(money(late_fee_value), 0)
        if late_fee_value is not None
        else auto_fine
    )

    late_details = {
        m: late_fine(m, dt)
        for m in details
    }

    t = {
        "receipt_no": next_receipt(),
        "adm_code": adm,
        "student_name": s.get("student_name", ""),
        "class": s.get("class", ""),
        "section": s.get("section", s.get("sec", "")),
        "father_name": s.get("father_name", ""),
        "months": list(details),
        "month_details": details,
        "head_totals": heads_total,
        "paid_head_totals": paid_heads,
        "amount_paid": due,
        "paid_amount": paid,
        "paid": paid,
        "balance_amount": balance,
        "balance": balance,
        "student_balance": new_balance,
        "month_total": due,
        "is_balance_payment": False,
        "payment_type": "New Payment",
        "late_fee": final_fine,
        "auto_late_fee": auto_fine,
        "late_fee_details": late_details,
        "date": dt,
        "payment_mode": mode,
        "remark": remark,
        "month": list(details)[0]
        if len(details) == 1 else None
    }

    try:
        tran_collection.insert_one(t)

        sets = {
            "balance_fee": new_balance
        }

        for m, d in details.items():
            sets[f"{m.lower()}_status"] = (
                "Paid"
                if d["balance"] <= 0
                else "Partial"
                if d["paid"] > 0
                else "Unpaid"
            )

        for h, v in paid_heads.items():
            if v:
                sets[f"{h}_paid"] = round(
                    money(s.get(f"{h}_paid", 0)) + v,
                    2
                )

        master_col.update_one(
            {"adm_code": adm},
            {
                "$inc": {"paid_fee": paid},
                "$set": sets
            }
        )

    except Exception as e:
        return None, f"Payment save failed: {e}"

    return t, None


@fee_entry_bp.route("/home")
def fee_home(): return redirect(url_for("fee_entry_bp.fee_entry"))


@fee_entry_bp.route("/")
def fee_entry():
    return render_template("fee_entry.html", adm_code=request.args.get("adm_code", "").strip(), months=MONTHS)


@fee_entry_bp.route("/autocomplete")
def autocomplete():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])
    cur = master_col.find({"$or": [{"student_name": {"$regex": q, "$options": "i"}}, {"adm_code": {"$regex": q, "$options": "i"}}]},
                          {"student_name": 1, "adm_code": 1, "class": 1, "section": 1, "sec": 1, "father_name": 1}).limit(10)
    return jsonify([{"student_name": x.get("student_name", ""), "adm_code": x.get("adm_code", ""),
                    "class": x.get("class", ""), "section": x.get("section", x.get("sec", "")),
                     "father_name": x.get("father_name", "")} for x in cur])


@fee_entry_bp.route("/details")
def student_details():
    adm = request.args.get("adm_code", "").strip()
    s = master_col.find_one({"adm_code": adm})
    if not s:
        return jsonify({})
    return jsonify({"adm_code": adm, "student_name": s.get("student_name", ""), "class": s.get("class", ""),
                    "section": s.get("section", s.get("sec", "")), "father_name": s.get("father_name", ""),
                    "total_fee": money(s.get("total_fee")), "paid_fee": money(s.get("paid_fee")),
                    "balance_fee": money(s.get("balance_fee", s.get("total_fee", 0))),
                    "paid_months": list(paid_months(adm)), "months": MONTHS})


@fee_entry_bp.route("/month_total")
def month_total():
    adm = request.args.get("adm_code", "").strip()
    m = request.args.get("month", "").strip()
    if m not in MONTHS:
        return jsonify({"error": "Invalid month"}), 400
    s = master_col.find_one({"adm_code": adm})
    if not s:
        return jsonify({"error": "Student not found"}), 404
    d = month_detail(s, m)
    paid = month_paid(adm, m)
    bal = round(max(d["total"]-paid, 0), 2)
    return jsonify({"month": m, "total": d["total"], "paid": paid, "balance": bal,
                    "already_paid": bal <= 0,
                    "status": "Paid" if bal <= 0 else "Partial" if paid > 0 else "Unpaid",
                    **{k: d[k] for k in HEADS}})


@fee_entry_bp.route("/api/pay", methods=["POST"])
def api_pay():
    x = request.get_json(silent=True) or {}
    adm = str(x.get("adm_code", "")).strip()
    months = x.get("months") or []
    months = [months] if isinstance(months, str) else months
    try:
        amount = float(x.get("amount", 0) or 0)
    except:
        amount = 0
    try:
        fine = float(x.get("late_fee", 0) or 0)
    except:
        fine = 0

    t, e = save_payment(adm, months, amount, str(
        x.get("mode", "Cash")), str(x.get("remark", "")), fine)
    if e:
        return jsonify({"success": False, "error": e}), 400

    return jsonify({"success": True, "receipt_no": t["receipt_no"], "months": t["months"],
                    "amount_paid": t["amount_paid"], "paid_amount": t["paid_amount"],
                    "balance_amount": t["balance_amount"], "paid": t["paid_amount"],
                    "balance": t["balance_amount"], "student_balance": t["student_balance"],
                    "head_totals": t.get("head_totals", {}),
                    "is_balance_payment": t.get("is_balance_payment", False),
                    "payment_type": t.get("payment_type", "New Payment"),
                    "late_fee": t.get("late_fee", 0),
                    "receipt_url": url_for("fee_entry_bp.reprint_receipt", receipt_no=t["receipt_no"])})


@fee_entry_bp.route("/receive", methods=["POST"])
def receive_payment():
    adm = request.form.get("adm_code", "").strip()
    months = request.form.getlist("months") or (
        [request.form.get("month", "").strip()] if request.form.get("month") else [])
    try:
        amount = float(request.form.get("amount", 0) or 0)
    except:
        amount = 0
    try:
        fine = float(request.form.get("late_fee", 0) or 0)
    except:
        fine = 0

    t, e = save_payment(adm, months, amount, request.form.get(
        "mode", "Cash"), request.form.get("remark", ""), fine)

    if e:
        flash(e, "error")
        return redirect(url_for("fee_entry_bp.fee_entry", adm_code=adm))

    school = get_school() or {}
    return render_template("receipt.html", school_name=school.get("school_name", "School"),
                           school_address=school.get("address", ""), school_phone=school.get("phone", ""),
                           **build_receipt_data(t))


@fee_entry_bp.route("/receipt/<receipt_no>")
def reprint_receipt(receipt_no):
    t = tran_collection.find_one({"receipt_no": receipt_no})
    if not t:
        flash("Receipt not found", "error")
        return redirect(url_for("fee_entry_bp.fee_entry"))

    school = get_school() or {}
    return render_template("receipt.html", school_name=school.get("school_name", "School"),
                           school_address=school.get("address", ""), school_phone=school.get("phone", ""),
                           **build_receipt_data(t))


@fee_entry_bp.route("/api/details/<adm_code>")
def api_details(adm_code):
    s = master_col.find_one({"adm_code": adm_code})
    if not s:
        return jsonify({})
    return jsonify({"adm_code": adm_code, "student_name": s.get("student_name", ""),
                    "class": s.get("class", ""), "section": s.get("section", s.get("sec", "")),
                    "father_name": s.get("father_name", ""), "total_fee": money(s.get("total_fee")),
                    "paid_fee": money(s.get("paid_fee")),
                    "balance_fee": money(s.get("balance_fee", s.get("total_fee", 0))),
                    "paid_months": list(paid_months(adm_code)), "months": MONTHS,
                    "head_paid": {h: money(s.get(f"{h}_paid", 0)) for h in HEADS}})


@fee_entry_bp.route("/api/month_total")
def api_month_total(): return month_total()


@fee_entry_bp.route("/next_month")
def next_month():
    return jsonify({"month": next_unpaid_month(request.args.get("adm_code", "").strip())})


@fee_entry_bp.route("/api/next_month/<adm_code>")
def api_next_month(adm_code):
    return jsonify({"month": next_unpaid_month(adm_code)})
