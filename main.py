import os
import webbrowser
import threading
from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta

# ------------------ Import Blueprints ------------------
from classrpt import classrpt_bp
from student_crud import student_crud_bp
from dailyreport import dailyreport_bp
from defaulter import defaulter_bp
from studledg import studledg_bp
from receipt import receipt_bp
from transport import transport_bp
from feestru import feestru_bp
from fee_entry import fee_entry_bp
from app import master_bp   # Admission Entry blueprint
from marks_entry import marks_entry_bp
from report_card import report_card_bp

# ------------------ MongoDB Setup ------------------
client = MongoClient("mongodb://localhost:27017/")
db = client["school_db"]
users_collection = db["users"]

# ------------------ Flask Setup ------------------
main_app = Flask(__name__)
main_app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret")
main_app.permanent_session_lifetime = timedelta(minutes=30)

# ------------------ Routes ------------------


@main_app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user["password_hash"], password):
            session["user"] = username
            session["role"] = user.get("role", "user")
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@main_app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("base.html", role=session.get("role"))


@main_app.route("/welcome")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    male_count = db.students.count_documents({"gender": "Male"})
    female_count = db.students.count_documents({"gender": "Female"})
    new_admissions = db.students.count_documents({"admission_year": 2026})
    return render_template("welcome.html",
                           male=male_count,
                           female=female_count,
                           new=new_admissions)


@main_app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("role", None)
    return redirect(url_for("login"))

# ------------------ User Creation Route ------------------


@main_app.route("/create_user", methods=["GET", "POST"])
def create_user():
    # Sirf admin ko allow karein
    if "user" not in session or session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]

        # Duplicate check
        if users_collection.find_one({"username": username}):
            return render_template("create_user.html", error="⚠ User already exists!")

        hashed_pw = generate_password_hash(password)

        user_doc = {
            "username": username,
            "password_hash": hashed_pw,
            "role": role
        }

        if role == "teacher":
            user_doc["class_id"] = request.form.get("class_id")
        if role == "parent":
            user_doc["adm_code"] = request.form.get("adm_code")

        users_collection.insert_one(user_doc)
        return render_template("create_user.html", success=f"✅ User '{username}' created successfully!")

    return render_template("create_user.html")


@main_app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    # Sirf teacher/admin ko allow karein
    if "user" not in session or session.get("role") not in ["admin", "teacher"]:
        return redirect(url_for("login"))

    if request.method == "POST":
        adm_code = request.form.get("adm_code")
        new_password = request.form.get("new_password")

        # master collection use karo
        student = db.master.find_one({"adm_code": adm_code})
        if not student:
            return render_template("reset_password.html", error="❌ Admission code not found!")

        hashed_pw = generate_password_hash(new_password)
        db.master.update_one(
            {"adm_code": adm_code},
            {"$set": {"password_hash": hashed_pw}}
        )
        return render_template("reset_password.html", success=f"✅ Password reset for Admission {adm_code}")

    return render_template("reset_password.html")


# ------------------ Register Blueprints ------------------
main_app.register_blueprint(master_bp, url_prefix="/master")
main_app.register_blueprint(fee_entry_bp, url_prefix="/fee")
main_app.register_blueprint(feestru_bp, url_prefix="/structure")
main_app.register_blueprint(transport_bp, url_prefix="/transport")
main_app.register_blueprint(marks_entry_bp, url_prefix="/marks")
main_app.register_blueprint(report_card_bp, url_prefix="/reportcard")
main_app.register_blueprint(receipt_bp, url_prefix="/receipts")
main_app.register_blueprint(studledg_bp, url_prefix="/studledg")
main_app.register_blueprint(dailyreport_bp, url_prefix="/dailyreport")
main_app.register_blueprint(defaulter_bp, url_prefix="/defaulter")
main_app.register_blueprint(student_crud_bp, url_prefix="/mastmodi")
main_app.register_blueprint(classrpt_bp, url_prefix="/classwise")

# ------------------ Run ------------------


def open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    main_app.run(host="0.0.0.0", port=5000, debug=True)
