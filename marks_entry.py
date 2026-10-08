from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import master_col
from datetime import datetime

marks_entry_bp = Blueprint("marks_entry_bp", __name__)


def teacher_required():
    return session.get("teacher_logged_in") and session.get("role") == "teacher"


@marks_entry_bp.route("/marks")
def marks_home():
    return redirect(url_for("marks_entry_bp.teacher_marks_entry"))


@marks_entry_bp.route("/teacher/marks-entry", methods=["GET", "POST"])
def teacher_marks_entry():

    if not teacher_required():
        return redirect(url_for("teacher_login_bp.teacher_login"))

    teacher_name = session.get("teacher_name", "Teacher")
    teacher_class = str(session.get("teacher_class", "")).strip()
    teacher_section = str(session.get("teacher_section", "")).strip()
    school_id = session.get("school_id", "SCH001")

    # Student data: actual master fields are class + sec
    students = list(master_col.find({
        "class": teacher_class,
        "sec": teacher_section
    }).sort("student_name", 1))

    marks_collection = master_col.database["marks"]

    if request.method == "POST":

        exam = request.form.get("exam", "").strip()
        subject = request.form.get("subject", "").strip()

        try:
            max_marks = float(request.form.get("max_marks", 100))
        except:
            max_marks = 100

        if not exam or not subject:
            flash("Please select Exam and Subject.", "danger")
            return redirect(url_for("marks_entry_bp.teacher_marks_entry"))

        now = datetime.now()

        for student in students:

            adm_code = str(student.get("adm_code", "")).strip()

            if not adm_code:
                continue

            value = request.form.get(f"marks_{adm_code}", "").strip()

            if value == "":
                continue

            try:
                marks = float(value)
            except:
                continue

            if marks < 0 or marks > max_marks:
                continue

            marks_collection.update_one(
                {
                    "adm_code": adm_code,
                    "exam": exam,
                    "subject": subject
                },
                {
                    "$set": {
                        "school_id": school_id,
                        "adm_code": adm_code,
                        "student_name": student.get("student_name", ""),
                        "class": teacher_class,
                        "section": teacher_section,
                        "exam": exam,
                        "subject": subject,
                        "marks": marks,
                        "max_marks": max_marks,
                        "teacher_name": teacher_name,
                        "teacher_id": session.get("teacher_id", ""),
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )

        flash("Marks saved successfully.", "success")

        return redirect(url_for(
            "marks_entry_bp.teacher_marks_entry",
            exam=exam,
            subject=subject,
            max_marks=max_marks
        ))

    exam = request.args.get("exam", "")
    subject = request.args.get("subject", "")
    max_marks = request.args.get("max_marks", "100")

    existing = {}

    if exam and subject:
        rows = marks_collection.find({
            "class": teacher_class,
            "section": teacher_section,
            "exam": exam,
            "subject": subject
        })

        for row in rows:
            existing[row.get("adm_code")] = row.get("marks", "")

    return render_template(
        "marks_entry.html",
        teacher_name=teacher_name,
        teacher_class=teacher_class,
        teacher_section=teacher_section,
        students=students,
        exam=exam,
        subject=subject,
        max_marks=max_marks,
        existing=existing
    )
