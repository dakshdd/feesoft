from flask import Blueprint, render_template, request, jsonify, session
from db import master_collection
from pymongo import MongoClient
from datetime import datetime
import os

attendance_bp = Blueprint("attendance_bp", __name__)

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)


# ---------- Attendance Collection ----------
def attendance_collection():
    school_id = session.get("school_id", "school_db")
    return client[school_id]["attendance"]


# ---------- Common ----------
CLASSES = [
    "Nursery", "LKG", "UKG",
    "1st", "2nd", "3rd", "4th", "5th",
    "6th", "7th", "8th", "9th", "10th",
    "11th", "12th"
]

SECTIONS = ["A", "B", "C"]


# ---------- Attendance Entry ----------
@attendance_bp.route("/attendance_entry")
def attendance_entry():
    return render_template(
        "attendance_entry.html",
        classes=CLASSES,
        sections=SECTIONS,
        today=datetime.now().strftime("%Y-%m-%d")
    )


# ---------- Load Students ----------
@attendance_bp.route("/get_students")
def get_students():

    student_class = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    students = list(
        master_collection.find(
            {
                "class": student_class,
                "sec": section
            },
            {
                "_id": 0,
                "adm_code": 1,
                "student_name": 1,
                "photo": 1,
                "class": 1,
                "sec": 1
            }
        ).sort("adm_code", 1)
    )

    return jsonify(students)


# ---------- Save Attendance ----------
@attendance_bp.route("/save_attendance", methods=["POST"])
def save_attendance():

    data = request.json or {}
    att_col = attendance_collection()

    school_id = session.get("school_id", "school_db")

    date = data.get("date")
    student_class = data.get("class")
    section = data.get("section")

    for stu in data.get("students", []):

        att_col.update_one(
            {
                "date": date,
                "adm_code": stu["adm_code"]
            },
            {
                "$set": {
                    "school_id": school_id,
                    "date": date,
                    "class": student_class,
                    "section": section,
                    "adm_code": stu["adm_code"],
                    "student_name": stu["student_name"],
                    "status": stu["status"]
                }
            },
            upsert=True
        )

    return jsonify({
        "success": True,
        "message": "Attendance Saved Successfully"
    })


# ---------- Load Existing Attendance ----------
@attendance_bp.route("/load_attendance")
def load_attendance():

    date = request.args.get("date")
    student_class = request.args.get("class")
    section = request.args.get("section")

    records = list(
        attendance_collection().find(
            {
                "date": date,
                "class": student_class,
                "section": section
            },
            {
                "_id": 0,
                "adm_code": 1,
                "status": 1
            }
        )
    )

    return jsonify(records)


# ---------- Attendance View ----------
@attendance_bp.route("/admin_attendance")
def admin_attendance():

    return render_template(
        "attendance_view.html",
        classes=CLASSES,
        sections=SECTIONS,
        today=datetime.now().strftime("%Y-%m-%d")
    )


# ---------- Daily Attendance View API ----------
@attendance_bp.route("/attendance_view_data")
def attendance_view_data():

    date = request.args.get("date")
    student_class = request.args.get("class")
    section = request.args.get("section")

    records = list(
        attendance_collection().find(
            {
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
        ).sort("adm_code", 1)
    )

    return jsonify(records)


# ---------- Monthly Attendance Report ----------
@attendance_bp.route("/admin_attendance_report")
def admin_attendance_report():

    return render_template(
        "admin_attendance_report.html",
        classes=CLASSES,
        sections=SECTIONS
    )


# ---------- Monthly Report API ----------
@attendance_bp.route("/monthly_attendance_data")
def monthly_attendance_data():

    month = request.args.get("month", "").strip()
    student_class = request.args.get("class", "").strip()
    section = request.args.get("section", "").strip()

    if not month or not student_class or not section:
        return jsonify([])

    records = list(
        attendance_collection().find(
            {
                "date": {
                    "$regex": f"^{month}"
                },
                "class": student_class,
                "section": section
            },
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
