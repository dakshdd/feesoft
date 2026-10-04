from flask import Blueprint, render_template, request
from db import master_collection, get_school

defaulter_bp = Blueprint("defaulter_bp", __name__)

MONTHS = [
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "January", "February", "March"
]


def money(v):
    try:
        return float(v or 0)
    except:
        return 0.0


@defaulter_bp.route("/report", methods=["GET", "POST"])
def defaulter_report():
    school = get_school() or {}

    if request.method == "POST":
        cls = request.form.get("class", "").strip()
        sec = request.form.get("section", "").strip()
        month = request.form.get("month", "").strip()

        query = {}
        if cls:
            query["class"] = cls
        if sec:
            query["$or"] = [{"sec": sec}, {"section": sec}]

        students = list(master_collection.find(query))

        field = f"{month.lower()}_status" if month else ""

        defaulters = [
            s for s in students
            if not field or s.get(field, "Unpaid") != "Paid"
        ]

        total_fee = sum(
            money(s.get("total_fee")) for s in defaulters
        )

        total_paid = sum(
            money(s.get("paid_fee")) for s in defaulters
        )

        total_balance = sum(
            money(s.get("balance_fee")) for s in defaulters
        )

        return render_template(
            "defaulter_report.html",
            school=school,
            class_name=cls,
            section=sec,
            month=month,
            defaulters=defaulters,
            total_defaulters=len(defaulters),
            total_fee=total_fee,
            total_paid=total_paid,
            total_balance=total_balance
        )

    classes = sorted(master_collection.distinct("class"))

    sections = sorted(set(
        master_collection.distinct("sec") +
        master_collection.distinct("section")
    ))

    return render_template(
        "defaulter_form.html",
        school=school,
        classes=classes,
        sections=sections,
        months=MONTHS
    )
