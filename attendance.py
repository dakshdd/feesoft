import os
from datetime import datetime
from pymongo import MongoClient
from db import master_collection, users_collection
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

attendance_bp = Blueprint("attendance_bp", __name__)
client = MongoClient(os.getenv("MONGO_URI"))

CLASSES = [
    "Nursery", "LKG", "UKG", "1st", "2nd", "3rd", "4th",
    "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"
]
SECTIONS = ["A", "B", "C"]


def attendance_collection():
    return client["school_db"]["attendance"]


def get_teacher_details():
    if not session.get("teacher_logged_in"):
        return None, "", ""

    teacher_class = str(session.get("teacher_class", "")).strip()
    teacher_section = str(session.get("teacher_section", "")).strip()

    if teacher_class and teacher_section:
        return {
            "teacher_name": session.get("teacher_name", ""),
            "username": session.get("teacher_username", session.get("user", ""))
        }, teacher_class, teacher_section

    username = session.get("teacher_username", session.get("user", ""))

    if username:
        user = users_collection.find_one({
            "username": username,
            "role": "teacher",
            "active": True
        })

        if user:
            teacher_class = str(user.get("class_id", "")).strip()
            teacher_section = str(user.get("sec_id", "")).strip()

            session["teacher_class"] = teacher_class
            session["teacher_section"] = teacher_section
            session["teacher_name"] = user.get(
                "teacher_name", user.get("username", "")
            )

            return user, teacher_class, teacher_section

    return None, "", ""


# ================= TEACHER ATTENDANCE =================

@attendance_bp.route("/teacher-attendance")
def teacher_attendance():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    user, teacher_class, teacher_section = get_teacher_details()

    if not teacher_class or not teacher_section:
        return "Teacher Class/Section not found. Please login again."

    return render_template(
        "attendance_entry.html",
        classes=[teacher_class],
        sections=[teacher_section],
        teacher=True,
        teacher_class=teacher_class,
        teacher_section=teacher_section,
        today=datetime.now().strftime("%Y-%m-%d")
    )


@attendance_bp.route("/teacher-attendance/students")
def teacher_attendance_students():
    if not session.get("teacher_logged_in"):
        return jsonify([])

    user, student_class, section = get_teacher_details()

    if not student_class or not section:
        return jsonify([])

    students = list(master_collection.find(
        {"class": student_class, "sec": section},
        {
            "_id": 0,
            "adm_code": 1,
            "student_name": 1,
            "photo": 1,
            "class": 1,
            "sec": 1
        }
    ).sort("adm_code", 1))

    return jsonify(students)


# ================= TEACHER REPORT =================

@attendance_bp.route("/teacher-attendance-report")
def teacher_attendance_report():
    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    user, teacher_class, teacher_section = get_teacher_details()

    if not teacher_class or not teacher_section:
        return "Teacher Class/Section not found. Please login again."

    month = request.args.get(
        "month",
        datetime.now().strftime("%Y-%m")
    ).strip()

    try:
        year, mon = map(int, month.split("-"))
    except:
        month = datetime.now().strftime("%Y-%m")
        year, mon = map(int, month.split("-"))

    start_date = f"{year:04d}-{mon:02d}-01"

    if mon == 12:
        end_date = f"{year + 1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{mon + 1:02d}-01"

    school_id = session.get("school_id", "SCH001")

    attendance_docs = list(
        attendance_collection().find({
            "school_id": school_id,
            "class": teacher_class,
            "section": teacher_section,
            "date": {
                "$gte": start_date,
                "$lt": end_date
            }
        })
    )

    students = list(
        master_collection.find({
            "class": teacher_class,
            "sec": teacher_section
        }).sort("adm_code", 1)
    )

    report = []

    for student in students:
        adm_code = str(student.get("adm_code", "")).strip()

        present = absent = leave = 0

        for doc in attendance_docs:
            if str(doc.get("adm_code", "")).strip() != adm_code:
                continue

            status = str(doc.get("status", "")).strip().lower()

            if status in ("p", "present"):
                present += 1
            elif status in ("a", "absent"):
                absent += 1
            elif status in ("l", "leave"):
                leave += 1

        total = present + absent + leave
        percentage = round((present * 100) / total, 1) if total else 0

        report.append({
            "adm_code": adm_code,
            "student_name": student.get("student_name", ""),
            "total": total,
            "present": present,
            "absent": absent,
            "leave": leave,
            "percentage": percentage
        })

    return render_template(
        "teacher_attendance_report.html",
        teacher_name=session.get("teacher_name", ""),
        teacher_class=teacher_class,
        teacher_section=teacher_section,
        month=month,
        report=report
    )


# ================= COMMON ATTENDANCE =================

@attendance_bp.route("/attendance_entry")
def attendance_entry():
    if session.get("teacher_logged_in"):
        return redirect(url_for("attendance_bp.teacher_attendance"))

    return render_template(
        "attendance_entry.html",
        classes=CLASSES,
        sections=SECTIONS,
        teacher=False,
        today=datetime.now().strftime("%Y-%m-%d")
    )


@attendance_bp.route("/get_students")
def get_students():
    student_class = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    students = list(master_collection.find(
        {"class": student_class, "sec": section},
        {
            "_id": 0,
            "adm_code": 1,
            "student_name": 1,
            "photo": 1,
            "class": 1,
            "sec": 1
        }
    ).sort("adm_code", 1))

    return jsonify(students)


# ================= SAVE ATTENDANCE =================

@attendance_bp.route("/save_attendance", methods=["POST"])
def save_attendance():
    data = request.json or {}
    date = str(data.get("date", "")).strip()

    if session.get("teacher_logged_in"):
        user, student_class, section = get_teacher_details()
    else:
        student_class = str(data.get("class", "")).strip()
        section = str(data.get("section", "")).strip()

    if not date:
        return jsonify({
            "success": False,
            "message": "Date is required."
        }), 400

    if not student_class or not section:
        return jsonify({
            "success": False,
            "message": "Teacher Class/Section not found. Please login again."
        }), 400

    school_id = session.get("school_id", "SCH001")
    att_col = attendance_collection()
    saved = 0

    for stu in data.get("students", []):
        adm_code = str(stu.get("adm_code", "")).strip()

        if not adm_code:
            continue

        att_col.update_one(
            {
                "school_id": school_id,
                "date": date,
                "adm_code": adm_code
            },
            {
                "$set": {
                    "school_id": school_id,
                    "date": date,
                    "class": student_class,
                    "section": section,
                    "adm_code": adm_code,
                    "student_name": stu.get("student_name", ""),
                    "status": stu.get("status", "")
                }
            },
            upsert=True
        )

        saved += 1

    return jsonify({
        "success": True,
        "message": "Attendance Saved Successfully",
        "count": saved
    })


# ================= LOAD ATTENDANCE =================

@attendance_bp.route("/load_attendance")
def load_attendance():
    date = request.args.get("date", "").strip()

    if session.get("teacher_logged_in"):
        user, student_class, section = get_teacher_details()
    else:
        student_class = request.args.get("class", "").strip()
        section = request.args.get("section", "").strip()

    records = list(attendance_collection().find(
        {
            "school_id": session.get("school_id", "SCH001"),
            "date": date,
            "class": student_class,
            "section": section
        },
        {
            "_id": 0,
            "adm_code": 1,
            "status": 1
        }
    ))

    return jsonify(records)


# ================= ADMIN VIEW =================

@attendance_bp.route("/admin_attendance")
def admin_attendance():
    return render_template(
        "attendance_view.html",
        classes=CLASSES,
        sections=SECTIONS,
        today=datetime.now().strftime("%Y-%m-%d")
    )


@attendance_bp.route("/attendance_view_data")
def attendance_view_data():
    date = request.args.get("date", "").strip()
    student_class = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    records = list(attendance_collection().find(
        {
            "school_id": session.get("school_id", "SCH001"),
            "date": date,
            "class": student_class,
            "section": section
        },
        {
            "_id": 0,
            "adm_code": 1,
            "student_name": 1,
            "status": 1
        }
    ).sort("adm_code", 1))

    return jsonify(records)


# ================= ADMIN MONTHLY REPORT =================

@attendance_bp.route("/admin_attendance_report")
def admin_attendance_report():
    return render_template(
        "admin_attendance_report.html",
        classes=CLASSES,
        sections=SECTIONS
    )


# ================= MONTHLY API =================

@attendance_bp.route("/monthly_attendance_data")
def monthly_attendance_data():
    month = request.args.get("month", "").strip()
    student_class = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    if session.get("teacher_logged_in"):
        _, student_class, section = get_teacher_details()

    if not month or not student_class or not section:
        return jsonify([])

    query = {
        "school_id": session.get("school_id", "SCH001"),
        "date": {"$regex": f"^{month}"},
        "class": student_class,
        "section": section
    }

    records = list(
        attendance_collection().find(
            query,
            {
                "_id": 0,
                "date": 1,
                "adm_code": 1,
                "student_name": 1,
                "status": 1
            }
        ).sort([
            ("adm_code", 1),
            ("date", 1)
        ])
    )

    return jsonify(records)
