from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from bson import ObjectId
from db import get_school, school_db

homework_bp = Blueprint("homework_bp", __name__)
homework_col = school_db["homework"]

CLASSES = ["NURSERY", "LKG", "UKG", "1st", "2nd", "3rd", "4th", "5th", "6th",
           "7th", "8th", "9th", "10th", "11th", "12th"]
SECTIONS = ["A", "B", "C"]


# ================= ADMIN HOMEWORK =================
@homework_bp.route("/homework")
def homework_home():

    # TEACHER KO ADMIN PAGE PAR JAANE HI NA DO
    if session.get("teacher_logged_in"):
        return redirect(url_for("homework_bp.teacher_homework"))

    if "user" not in session:
        return redirect(url_for("login"))

    q = {}

    if request.args.get("class"):
        q["class"] = request.args["class"]

    if request.args.get("section"):
        q["section"] = request.args["section"]

    if request.args.get("subject"):
        q["subject"] = {
            "$regex": request.args["subject"],
            "$options": "i"
        }

    data = list(
        homework_col.find(q).sort("given_date", -1)
    )

    return render_template(
        "homework.html",
        school=get_school(),
        homework=data,
        classes=CLASSES,
        edit=None,
        teacher=False
    )


# ================= TEACHER HOMEWORK =================
@homework_bp.route("/teacher-homework")
def teacher_homework():

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    cls = session.get("teacher_class")
    sec = session.get("teacher_section")

    q = {
        "class": cls,
        "section": sec
    }

    data = list(
        homework_col.find(q).sort("given_date", -1)
    )

    return render_template(
        "teacher_homework.html",
        school=get_school(),
        homework=data,
        teacher_name=session.get("teacher_name", "Teacher"),
        teacher_class=cls,
        teacher_section=sec,
        edit=None
    )


# ================= TEACHER ADD =================
@homework_bp.route("/teacher-homework/add", methods=["POST"])
def teacher_homework_add():

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    f = request.form

    if not f.get("subject") or not f.get("description") or not f.get("given_date"):
        flash("Please fill all required fields.", "danger")
        return redirect(url_for("homework_bp.teacher_homework"))

    homework_col.insert_one({
        "class": session.get("teacher_class"),
        "section": session.get("teacher_section"),
        "subject": f["subject"].strip(),
        "description": f["description"].strip(),
        "given_date": f["given_date"],
        "due_date": f.get("due_date", ""),
        "created_at": datetime.now()
    })

    flash("Homework added successfully.", "success")
    return redirect(url_for("homework_bp.teacher_homework"))


# ================= TEACHER EDIT =================
@homework_bp.route("/teacher-homework/edit/<id>", methods=["GET", "POST"])
def teacher_homework_edit(id):

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    q = {
        "_id": ObjectId(id),
        "class": session.get("teacher_class"),
        "section": session.get("teacher_section")
    }

    h = homework_col.find_one(q)

    if not h:
        flash("Homework not found.", "danger")
        return redirect(url_for("homework_bp.teacher_homework"))

    if request.method == "POST":

        f = request.form

        homework_col.update_one(
            {"_id": ObjectId(id)},
            {"$set": {
                "subject": f["subject"].strip(),
                "description": f["description"].strip(),
                "given_date": f["given_date"],
                "due_date": f.get("due_date", ""),
                "updated_at": datetime.now()
            }}
        )

        flash("Homework updated successfully.", "success")
        return redirect(url_for("homework_bp.teacher_homework"))

    data = list(
        homework_col.find({
            "class": session.get("teacher_class"),
            "section": session.get("teacher_section")
        }).sort("given_date", -1)
    )

    return render_template(
        "teacher_homework.html",
        school=get_school(),
        homework=data,
        teacher_name=session.get("teacher_name", "Teacher"),
        teacher_class=session.get("teacher_class"),
        teacher_section=session.get("teacher_section"),
        edit=h
    )


# ================= TEACHER DELETE =================
@homework_bp.route("/teacher-homework/delete/<id>")
def teacher_homework_delete(id):

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    homework_col.delete_one({
        "_id": ObjectId(id),
        "class": session.get("teacher_class"),
        "section": session.get("teacher_section")
    })

    flash("Homework deleted.", "success")
    return redirect(url_for("homework_bp.teacher_homework"))


# ================= ADMIN ADD =================
@homework_bp.route("/homework/add", methods=["POST"])
def homework_add():

    if "user" not in session:
        return redirect(url_for("login"))

    f = request.form

    homework_col.insert_one({
        "class": f["class"],
        "section": f["section"],
        "subject": f["subject"].strip(),
        "description": f["description"].strip(),
        "given_date": f["given_date"],
        "due_date": f.get("due_date", ""),
        "created_at": datetime.now()
    })

    flash("Homework added successfully.", "success")
    return redirect(url_for("homework_bp.homework_home"))


# ================= ADMIN EDIT =================
@homework_bp.route("/homework/edit/<id>", methods=["GET", "POST"])
def homework_edit(id):

    if "user" not in session:
        return redirect(url_for("login"))

    oid = ObjectId(id)
    h = homework_col.find_one({"_id": oid})

    if not h:
        flash("Homework not found.", "danger")
        return redirect(url_for("homework_bp.homework_home"))

    if request.method == "POST":

        f = request.form

        homework_col.update_one(
            {"_id": oid},
            {"$set": {
                "class": f["class"],
                "section": f["section"],
                "subject": f["subject"].strip(),
                "description": f["description"].strip(),
                "given_date": f["given_date"],
                "due_date": f.get("due_date", ""),
                "updated_at": datetime.now()
            }}
        )

        flash("Homework updated successfully.", "success")
        return redirect(url_for("homework_bp.homework_home"))

    return render_template(
        "homework.html",
        school=get_school(),
        homework=list(homework_col.find().sort("given_date", -1)),
        classes=CLASSES,
        edit=h,
        teacher=False
    )


# ================= ADMIN DELETE =================
@homework_bp.route("/homework/delete/<id>")
def homework_delete(id):

    if "user" not in session:
        return redirect(url_for("login"))

    homework_col.delete_one({"_id": ObjectId(id)})

    flash("Homework deleted.", "success")
    return redirect(url_for("homework_bp.homework_home"))
