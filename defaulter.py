from flask import Blueprint, render_template, request
from db import master_collection

defaulter_bp = Blueprint("defaulter_bp", __name__)


@defaulter_bp.route("/report", methods=["GET", "POST"])
def defaulter_report():
    if request.method == "POST":
        class_name = request.form.get("class")
        section = request.form.get("section")
        month = request.form.get("month")

        query = {}

        if class_name:
            query["class"] = class_name

        if section:
            query["sec"] = section

        students = list(master_collection.find(query))

        month_field = f"{month.lower()}_status"

        defaulters = [
            s for s in students
            if s.get(month_field, "Unpaid") != "Paid"
        ]

        # Grand totals
        total_defaulters = len(defaulters)

        # Safely handle balance_fee stored as number or string
        def get_balance(value):
            try:
                return float(value or 0)
            except (ValueError, TypeError):
                return 0

        total_balance = sum(
            get_balance(s.get("balance_fee"))
            for s in defaulters
        )

        return render_template(
            "defaulter_report.html",
            class_name=class_name,
            section=section,
            month=month,
            defaulters=defaulters,
            total_defaulters=total_defaulters,
            total_balance=total_balance
        )

    classes = master_collection.distinct("class")
    sections = master_collection.distinct("sec")

    return render_template(
        "defaulter_form.html",
        classes=classes,
        sections=sections
    )
