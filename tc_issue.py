
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import date, datetime
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
import re

from db import master_collection, counters_collection, get_school

tc_issue_bp = Blueprint("tc_issue_bp", __name__)

# Same school_db database, separate collection
tc_collection = master_collection.database["tc"]

# Prevent issuing multiple TCs for the same admission code
tc_collection.create_index("adm_code", unique=True)


def admin_required():
    return str(session.get("role", "")).lower() in ("admin", "administrator")


def tc_number():
    counter = counters_collection.find_one_and_update(
        {"_id": "tc_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return f"TC-{date.today().year}-{counter['seq']:04d}"


@tc_issue_bp.route("/", methods=["GET"])
def tc_home():
    if not admin_required():
        return "Unauthorized", 403

    q = request.args.get("q", "").strip()
    students = []

    if q:
        pattern = re.escape(q)
        students = list(master_collection.find({
            "$or": [
                {"adm_code": {"$regex": pattern, "$options": "i"}},
                {"student_name": {"$regex": pattern, "$options": "i"}}
            ]
        }).limit(30))

    return render_template(
        "tc_issue.html",
        mode="search",
        students=students,
        q=q,
        school=get_school()
    )


@tc_issue_bp.route("/preview/<adm_code>", methods=["GET"])
def tc_preview(adm_code):
    if not admin_required():
        return "Unauthorized", 403

    student = master_collection.find_one({"adm_code": adm_code})

    if not student:
        flash("Student record not found or TC already issued.", "warning")
        return redirect(url_for("tc_issue_bp.tc_home"))

    if tc_collection.find_one({"adm_code": adm_code}):
        flash("TC has already been issued for this student.", "warning")
        return redirect(url_for("tc_issue_bp.tc_home"))

    return render_template(
        "tc_issue.html",
        mode="preview",
        student=student,
        school=get_school(),
        today=date.today().isoformat()
    )


@tc_issue_bp.route("/issue/<adm_code>", methods=["POST"])
def issue_tc(adm_code):
    if not admin_required():
        return "Unauthorized", 403

    student = master_collection.find_one({"adm_code": adm_code})

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("tc_issue_bp.tc_home"))

    if tc_collection.find_one({"adm_code": adm_code}):
        flash("TC has already been issued.", "warning")
        return redirect(url_for("tc_issue_bp.tc_home"))

    issue_date = request.form.get("issue_date", "").strip()
    leaving_date = request.form.get("leaving_date", "").strip()
    reason = request.form.get("reason", "").strip()

    if not issue_date or not leaving_date or not reason:
        flash("Issue date, leaving date and reason are required.", "danger")
        return redirect(url_for("tc_issue_bp.tc_preview", adm_code=adm_code))

    try:
        datetime.strptime(issue_date, "%Y-%m-%d")
        datetime.strptime(leaving_date, "%Y-%m-%d")
    except ValueError:
        flash("Please enter valid dates.", "danger")
        return redirect(url_for("tc_issue_bp.tc_preview", adm_code=adm_code))

    number = tc_number()

    # Preserve every original student field and original MongoDB _id.
    archive = dict(student)
    archive.update({
        "tc_number": number,
        "tc_issue_date": issue_date,
        "leaving_date": leaving_date,
        "tc_reason": reason,
        "conduct": request.form.get("conduct", ""),
        "result": request.form.get("result", ""),
        "remarks": request.form.get("remarks", ""),
        "archive_status": "Archived",
        "archived_at": datetime.now()
    })

    try:
        # Archive first. If source deletion fails, the archived copy is retained
        # so that the student's data is never lost.
        tc_collection.insert_one(archive)

    except DuplicateKeyError:
        flash("TC already exists for this student.", "warning")
        return redirect(url_for("tc_issue_bp.tc_home"))

    try:
        deleted = master_collection.delete_one({
            "_id": student["_id"],
            "adm_code": adm_code
        })

        if deleted.deleted_count != 1:
            tc_collection.update_one(
                {"adm_code": adm_code},
                {"$set": {"archive_status": "Needs Review - source still exists"}}
            )
            flash(
                "TC record was saved, but the original student record could not be removed. "
                "Please contact the administrator before issuing again.",
                "warning"
            )
            return redirect(url_for("tc_issue_bp.tc_home"))

    except Exception:
        tc_collection.update_one(
            {"adm_code": adm_code},
            {"$set": {"archive_status": "Needs Review - source still exists"}}
        )
        flash(
            "TC was saved, but moving the original record needs administrator review.",
            "warning"
        )
        return redirect(url_for("tc_issue_bp.tc_home"))

    return render_template(
        "tc_issue.html",
        mode="issued",
        student=archive,
        school=get_school()
    )
