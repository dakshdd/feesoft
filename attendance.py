from flask import Blueprint, render_template, request, redirect, url_for, session
from db import master_collection, attendance_collection
from datetime import datetime

attendance_bp = Blueprint("attendance_bp", __name__)


# ================= TEACHER ATTENDANCE =================
@attendance_bp.route("/attendance", methods=["GET", "POST"])
def attendance():

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    teacher_class = session.get("teacher_class")
    teacher_section = session.get("teacher_section")
    school_id = session.get("school_id")

    date = request.values.get(
        "date",
        datetime.now().strftime("%Y-%m-%d")
    )

    students = list(
        master_collection.find({
            "class": teacher_class,
            "sec": teacher_section
        }).sort("student_name", 1)
    )

    # Save attendance
    if request.method == "POST":

        for student in students:

            adm_code = student.get("adm_code")
            status = request.form.get(f"status_{adm_code}")

            if status not in ["Present", "Absent", "Leave"]:
                continue

            attendance_collection.update_one(
                {
                    "school_id": school_id,
                    "date": date,
                    "adm_code": adm_code
                },
                {
                    "$set": {
                        "school_id": school_id,
                        "date": date,
                        "adm_code": adm_code,
                        "student_name": student.get("student_name", ""),
                        "class": teacher_class,
                        "section": teacher_section,
                        "status": status,
                        "marked_by": session.get("teacher_id"),
                        "marked_time": datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    }
                },
                upsert=True
            )

        return redirect(
            url_for(
                "attendance_bp.attendance",
                date=date,
                saved=1
            )
        )

    # Load saved attendance
    records = attendance_collection.find({
        "school_id": school_id,
        "date": date
    })

    attendance_map = {
        x["adm_code"]: x.get("status")
        for x in records
    }

    return render_template(
        "attendance.html",
        students=students,
        date=date,
        teacher_name=session.get("teacher_name"),
        teacher_class=teacher_class,
        teacher_section=teacher_section,
        attendance_map=attendance_map,
        saved=request.args.get("saved")
    )


# ================= TEACHER MONTHLY REPORT =================
@attendance_bp.route("/attendance-report")
def attendance_report():

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    teacher_class = session.get("teacher_class")
    teacher_section = session.get("teacher_section")
    school_id = session.get("school_id")

    month = request.args.get(
        "month",
        datetime.now().strftime("%Y-%m")
    )

    year, mon = map(int, month.split("-"))

    start_date = f"{month}-01"

    if mon == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, mon + 1

    end_date = f"{next_year:04d}-{next_month:02d}-01"

    students = list(
        master_collection.find({
            "class": teacher_class,
            "sec": teacher_section
        }).sort("student_name", 1)
    )

    records = attendance_collection.find({
        "school_id": school_id,
        "class": teacher_class,
        "section": teacher_section,
        "date": {
            "$gte": start_date,
            "$lt": end_date
        }
    })

    attendance_data = {}

    for record in records:

        adm_code = record.get("adm_code")

        if adm_code not in attendance_data:
            attendance_data[adm_code] = {
                "Present": 0,
                "Absent": 0,
                "Leave": 0
            }

        status = record.get("status")

        if status in attendance_data[adm_code]:
            attendance_data[adm_code][status] += 1

    report = []

    for student in students:

        adm_code = student.get("adm_code")

        data = attendance_data.get(
            adm_code,
            {
                "Present": 0,
                "Absent": 0,
                "Leave": 0
            }
        )

        total = (
            data["Present"] +
            data["Absent"] +
            data["Leave"]
        )

        percentage = (
            round(data["Present"] / total * 100, 1)
            if total else 0
        )

        report.append({
            "adm_code": adm_code,
            "student_name": student.get("student_name", ""),
            "present": data["Present"],
            "absent": data["Absent"],
            "leave": data["Leave"],
            "total": total,
            "percentage": percentage
        })

    return render_template(
        "attendance_report.html",
        report=report,
        month=month,
        teacher_name=session.get("teacher_name"),
        teacher_class=teacher_class,
        teacher_section=teacher_section
    )


# ================= ADMIN ATTENDANCE =================
@attendance_bp.route("/admin-attendance")
def admin_attendance():

    if not session.get("user"):
        return redirect(url_for("login"))

    date = request.args.get(
        "date",
        datetime.now().strftime("%Y-%m-%d")
    )

    selected_class = request.args.get("class", "")
    selected_section = request.args.get("section", "")

    classes = sorted(master_collection.distinct("class"))
    sections = sorted(master_collection.distinct("sec"))

    query = {}

    if selected_class:
        query["class"] = selected_class

    if selected_section:
        query["sec"] = selected_section

    students = list(
        master_collection.find(query).sort("student_name", 1)
    )

    records = attendance_collection.find({
        "date": date
    })

    attendance_map = {
        x["adm_code"]: x.get("status")
        for x in records
    }

    present = sum(
        1 for x in students
        if attendance_map.get(x.get("adm_code")) == "Present"
    )

    absent = sum(
        1 for x in students
        if attendance_map.get(x.get("adm_code")) == "Absent"
    )

    leave = sum(
        1 for x in students
        if attendance_map.get(x.get("adm_code")) == "Leave"
    )

    return render_template(
        "admin_attendance.html",
        students=students,
        attendance_map=attendance_map,
        date=date,
        classes=classes,
        sections=sections,
        selected_class=selected_class,
        selected_section=selected_section,
        present=present,
        absent=absent,
        leave=leave,
        total=len(students)
    )
# ================= ADMIN MONTHLY REPORT =================


@attendance_bp.route("/admin-attendance-report")
def admin_attendance_report():
    if not session.get("user"):
        return redirect(url_for("login"))

    month = request.args.get(
        "month",
        datetime.now().strftime("%Y-%m")
    )

    selected_class = request.args.get("class", "")
    selected_section = request.args.get("section", "")

    year, mon = map(int, month.split("-"))
    start_date = f"{month}-01"

    if mon == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, mon + 1

    end_date = f"{next_year:04d}-{next_month:02d}-01"

    classes = sorted(master_collection.distinct("class"))
    sections = sorted(master_collection.distinct("sec"))

    query = {}

    if selected_class:
        query["class"] = selected_class

    if selected_section:
        query["sec"] = selected_section

    students = list(
        master_collection.find(query).sort("student_name", 1)
    )

    records = attendance_collection.find({
        "date": {
            "$gte": start_date,
            "$lt": end_date
        }
    })

    data = {}

    for r in records:
        adm = r.get("adm_code")

        if adm not in data:
            data[adm] = {
                "Present": 0,
                "Absent": 0,
                "Leave": 0
            }

        status = r.get("status")

        if status in data[adm]:
            data[adm][status] += 1

    report = []

    for student in students:
        adm = student.get("adm_code")

        d = data.get(
            adm,
            {"Present": 0, "Absent": 0, "Leave": 0}
        )

        total = (
            d["Present"] +
            d["Absent"] +
            d["Leave"]
        )

        percentage = (
            round(d["Present"] / total * 100, 1)
            if total else 0
        )

        report.append({
            "adm_code": adm,
            "student_name": student.get("student_name", ""),
            "class": student.get("class", ""),
            "section": student.get("sec", ""),
            "present": d["Present"],
            "absent": d["Absent"],
            "leave": d["Leave"],
            "total": total,
            "percentage": percentage
        })

    return render_template(
        "admin_attendance_report.html",
        report=report,
        month=month,
        classes=classes,
        sections=sections,
        selected_class=selected_class,
        selected_section=selected_section
    )
