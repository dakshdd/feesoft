import os
from flask import Blueprint, render_template, request
from pymongo import MongoClient

defaulter_bp = Blueprint("defaulter_bp", __name__)
# ------------------ MongoDB Connection ------------------
MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(MONGO_URI)

db = client["school_db"]
master_col = db["master"]


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

        students = list(master_col.find(query))
        month_field = f"{month.lower()}_status"

        defaulters = [s for s in students if s.get(
            month_field, "Unpaid") != "Paid"]

        # Grand totals
        total_defaulters = len(defaulters)
        total_balance = sum(s.get("balance_fee", 0) for s in defaulters)

        return render_template("defaulter_report.html",
                               class_name=class_name,
                               section=section,
                               month=month,
                               defaulters=defaulters,
                               total_defaulters=total_defaulters,
                               total_balance=total_balance)

    # First load → show form
    # Distinct class/section list for combobox
    classes = master_col.distinct("class")
    sections = master_col.distinct("sec")
    return render_template("defaulter_form.html", classes=classes, sections=sections)
