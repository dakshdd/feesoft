import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta

from db import (
    master_collection, counters_collection, transport_collection,
    tran_collection, users_collection, students_collection,
    teachers_collection, get_school
)

from classrpt import classrpt_bp
from student_crud import student_crud_bp
from dailyreport import dailyreport_bp
from defaulter import defaulter_bp
from studledg import studledg_bp
from receipt import receipt_bp
from transport import transport_bp
from feestru import feestru_bp
from fee_entry import fee_entry_bp
from app import master_bp
from marks_entry import marks_entry_bp
from report_card import report_card_bp
from studledg_mob import studledg_mob_bp
from teacher_login import teacher_login_bp
from attendance import attendance_bp
from homework import homework_bp
from teachers_staff import teachers_staff_bp
# from marks_entry import marks_entry_bp


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret")
app.permanent_session_lifetime = timedelta(minutes=30)


# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = users_collection.find_one({
            "username": {"$regex": f"^{username}$", "$options": "i"}
        })

        if user:
            try:
                valid = check_password_hash(
                    user.get("password_hash", ""),
                    password
                )
            except:
                valid = False

            if valid:

                session.clear()
                session.permanent = True

                role = user.get("role", "user")

                # ================= TEACHER =================
                if role == "teacher":

                    session["user"] = user.get("username", username)
                    session["role"] = "teacher"
                    session["teacher_logged_in"] = True
                    session["teacher_id"] = str(user.get("_id"))
                    session["teacher_name"] = user.get(
                        "teacher_name",
                        user.get("username", username)
                    )
                    session["teacher_class"] = user.get("class_id", "")
                    session["teacher_section"] = user.get("sec_id", "")
                    session["school_id"] = user.get(
                        "school_id", "SCHOOL001"
                    )

                    return redirect(
                        url_for(
                            "teacher_login_bp.teacher_dashboard"
                        )
                    )

                # ================= ADMIN / OTHER USER =================
                session["user"] = user.get("username", username)
                session["role"] = role

                return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid username or password."
        )

    return render_template("login.html")

# ================= ADMIN DASHBOARD =================


@app.route("/dashboard")
def dashboard():

    if "user" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template(
        "base.html",
        role=session.get("role"),
        school=get_school()
    )


# ================= WELCOME =================
@app.route("/welcome")
def home():

    if "user" not in session:
        return redirect(url_for("login"))

    total_students = master_collection.count_documents({})

    male_count = master_collection.count_documents({
        "gender": {"$regex": "^male$", "$options": "i"}
    })

    female_count = master_collection.count_documents({
        "gender": {"$regex": "^female$", "$options": "i"}
    })

    new_admissions = master_collection.count_documents({
        "doa": {"$regex": r"^\d{2}-\d{2}-2026$"}
    })

    male_percent = round(male_count*100/total_students,
                         1) if total_students else 0
    female_percent = round(female_count*100/total_students,
                           1) if total_students else 0
    new_admissions_percent = round(
        new_admissions*100/total_students, 1) if total_students else 0

    return render_template(
        "welcome.html",
        total_students=total_students,
        male_count=male_count,
        female_count=female_count,
        new_admissions=new_admissions,
        male_percent=male_percent,
        female_percent=female_percent,
        new_admissions_percent=new_admissions_percent,
        school=get_school()
    )


# ================= ADMIN LOGOUT =================
@app.route("/logout")
def logout():

    session.clear()
    return redirect(url_for("login"))


# ================= CREATE USER =================
@app.route("/create_user", methods=["GET", "POST"])
def create_user():

    if "user" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":

        username = request.form["username"].strip()
        password = request.form["password"]
        role = request.form["role"]

        if users_collection.find_one({
            "username": {"$regex": f"^{username}$", "$options": "i"}
        }):
            return render_template(
                "create_user.html",
                error="⚠ User already exists!"
            )

        doc = {
            "username": username,
            "password_hash": generate_password_hash(password),
            "role": role
        }

        if role == "teacher":
            doc["class_id"] = request.form.get("class_id")

        if role == "parent":
            doc["adm_code"] = request.form.get("adm_code")

        users_collection.insert_one(doc)

        return render_template(
            "create_user.html",
            success=f"✅ User '{username}' created successfully!"
        )

    return render_template("create_user.html")


# ================= RESET PASSWORD =================
@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():

    if "user" not in session or session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    if request.method == "POST":

        adm_code = request.form.get("adm_code")
        new_password = request.form.get("new_password")

        student = master_collection.find_one({"adm_code": adm_code})

        if not student:
            return render_template(
                "reset_password.html",
                error="❌ Admission code not found!"
            )

        master_collection.update_one(
            {"adm_code": adm_code},
            {"$set": {
                "password_hash": generate_password_hash(new_password)
            }}
        )

        return render_template(
            "reset_password.html",
            success=f"✅ Password reset for Admission {adm_code}"
        )

    return render_template("reset_password.html")


# ================= BLUEPRINTS =================
app.register_blueprint(master_bp, url_prefix="/master")
app.register_blueprint(fee_entry_bp, url_prefix="/fee")
app.register_blueprint(feestru_bp, url_prefix="/structure")
app.register_blueprint(transport_bp, url_prefix="/transport")
app.register_blueprint(marks_entry_bp, url_prefix="/marks")
app.register_blueprint(report_card_bp, url_prefix="/reportcard")
app.register_blueprint(receipt_bp, url_prefix="/receipts")
app.register_blueprint(studledg_bp, url_prefix="/studledg")
app.register_blueprint(studledg_mob_bp)
app.register_blueprint(dailyreport_bp, url_prefix="/dailyreport")
app.register_blueprint(defaulter_bp, url_prefix="/defaulter")
app.register_blueprint(student_crud_bp, url_prefix="/mastmodi")
app.register_blueprint(classrpt_bp, url_prefix="/classwise")
app.register_blueprint(teacher_login_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(homework_bp)
app.register_blueprint(teachers_staff_bp)
# app.register_blueprint(marks_entry_bp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
