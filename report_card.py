from flask import Blueprint, render_template, redirect, url_for, request, session
from db import master_col

report_card_bp = Blueprint("report_card_bp", __name__)


def admin_required():
    return session.get("user") and session.get("role") == "admin"


def teacher_required():
    return session.get("teacher_logged_in") and session.get("role") == "teacher"


def get_result(marks):
    total = sum(float(x.get("marks", 0) or 0) for x in marks)
    maximum = sum(float(x.get("max_marks", 0) or 0) for x in marks)
    percentage = round(total / maximum * 100, 2) if maximum else 0
    grade = (
        "A+" if percentage >= 90 else
        "A" if percentage >= 80 else
        "B+" if percentage >= 70 else
        "B" if percentage >= 60 else
        "C" if percentage >= 50 else
        "D" if percentage >= 40 else "F"
    )
    return total, maximum, percentage, grade, "PASS" if percentage >= 40 else "FAIL"


CLASSES = [
    "NURSERY", "LKG", "UKG",
    "1st", "2nd", "3rd", "4th", "5th",
    "6th", "7th", "8th", "9th", "10th",
    "11th", "12th"
]

SECTIONS = ["A", "B", "C"]


# ================= REPORT CARD HOME =================

@report_card_bp.route("/report-card")
def report_card_home():

    mc = master_col.database["marks"]

    # ================= ADMIN =================

    if admin_required():

        cls = request.args.get("class", "").strip()
        sec = request.args.get("section", "").strip()
        students = []
        exams = []

        if cls and sec:

            students = list(
                master_col.find({
                    "class": cls,
                    "sec": sec
                }).sort("student_name", 1)
            )

            # Exams for selected class + section
            exams = sorted(set(
                str(x.get("exam", "")).strip()
                for x in mc.find({
                    "class": cls,
                    "section": sec
                })
                if x.get("exam")
            ))

            # If marks documents don't have class/section,
            # get exams using selected students' admission codes.
            if not exams and students:
                adm_codes = [
                    s.get("adm_code")
                    for s in students
                    if s.get("adm_code")
                ]

                exams = sorted(set(
                    str(x.get("exam", "")).strip()
                    for x in mc.find({
                        "adm_code": {"$in": adm_codes}
                    })
                    if x.get("exam")
                ))

        return render_template(
            "report_card.html",
            students=students,
            exams=exams,
            classes=CLASSES,
            sections=SECTIONS,
            selected_class=cls,
            selected_section=sec,
            teacher_class="",
            teacher_section=""
        )

    # ================= TEACHER =================

    if teacher_required():

        # NEVER take class/section from URL for teacher
        cls = str(session.get("teacher_class", "")).strip()
        sec = str(session.get("teacher_section", "")).strip()

        students = list(
            master_col.find({
                "class": cls,
                "sec": sec
            }).sort("student_name", 1)
        )

        exams = sorted(set(
            str(x.get("exam", "")).strip()
            for x in mc.find({
                "class": cls,
                "section": sec
            })
            if x.get("exam")
        ))

        # Fallback if marks don't contain class/section
        if not exams and students:
            adm_codes = [
                s.get("adm_code")
                for s in students
                if s.get("adm_code")
            ]

            exams = sorted(set(
                str(x.get("exam", "")).strip()
                for x in mc.find({
                    "adm_code": {"$in": adm_codes}
                })
                if x.get("exam")
            ))

        return render_template(
            "report_card.html",
            students=students,
            exams=exams,
            classes=CLASSES,
            sections=SECTIONS,
            selected_class=cls,
            selected_section=sec,
            teacher_class=cls,
            teacher_section=sec
        )

    return redirect(url_for("login"))


# ================= SINGLE REPORT CARD =================

@report_card_bp.route("/report-card/view/<adm_code>")
def view_report_card(adm_code):

    # ================= ADMIN =================

    if admin_required():

        student = master_col.find_one({
            "adm_code": adm_code
        })

        if not student:
            return "Student not found", 404

    # ================= TEACHER =================

    elif teacher_required():

        # Teacher can ONLY access assigned class + section
        cls = str(session.get("teacher_class", "")).strip()
        sec = str(session.get("teacher_section", "")).strip()

        student = master_col.find_one({
            "adm_code": adm_code,
            "class": cls,
            "sec": sec
        })

        if not student:
            return "Access denied / Student not found", 404

    else:
        return redirect(url_for("login"))

    mc = master_col.database["marks"]

    exam = request.args.get("exam", "").strip()

    exam_docs = list(
        mc.find({
            "adm_code": adm_code
        })
    )

    exams = sorted(set(
        str(x.get("exam", "")).strip()
        for x in exam_docs
        if x.get("exam")
    ))

    if not exam and exams:
        exam = exams[0]

    marks = list(
        mc.find({
            "adm_code": adm_code,
            "exam": exam,
            "school_id": student.get(
                "school_id",
                session.get("school_id", "SCH001")
            )
        }).sort("subject", 1)
    )

    total, maximum, percentage, grade, result = get_result(marks)

    return render_template(
        "report_card_view.html",
        student=student,
        marks=marks,
        exam=exam,
        exams=exams,
        total=total,
        maximum=maximum,
        percentage=percentage,
        grade=grade,
        result=result
    )


# ================= PRINT ALL =================

@report_card_bp.route("/report-card/print-all")
def print_all_report_cards():

    # ================= ADMIN =================

    if admin_required():

        cls = request.args.get("class", "").strip()
        sec = request.args.get("section", "").strip()

    # ================= TEACHER =================

    elif teacher_required():

        # NEVER take class/section from URL for teacher
        cls = str(session.get("teacher_class", "")).strip()
        sec = str(session.get("teacher_section", "")).strip()

    else:
        return redirect(url_for("login"))

    exam = request.args.get("exam", "").strip()

    students = list(
        master_col.find({
            "class": cls,
            "sec": sec
        }).sort("student_name", 1)
    )

    mc = master_col.database["marks"]

    if not exam:

        first = mc.find_one({
            "class": cls,
            "section": sec,
            "exam": {"$exists": True}
        })

        if first:
            exam = str(first.get("exam", "")).strip()

    cards = []

    for student in students:

        marks = list(
            mc.find({
                "adm_code": student.get("adm_code"),
                "exam": exam,
                "school_id": student.get(
                    "school_id",
                    session.get("school_id", "SCH001")
                )
            }).sort("subject", 1)
        )

        total, maximum, percentage, grade, result = get_result(marks)

        cards.append({
            "student": student,
            "marks": marks,
            "total": total,
            "maximum": maximum,
            "percentage": percentage,
            "grade": grade,
            "result": result
        })

    return render_template(
        "report_card_all.html",
        cards=cards,
        exam=exam
    )
