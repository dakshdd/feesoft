from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import teachers_collection

teacher_login_bp = Blueprint("teacher_login_bp", __name__)


# ---------------- Teacher Login ----------------

@teacher_login_bp.route("/teacher-login", methods=["GET", "POST"])
def teacher_login():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        teacher = teachers_collection.find_one({
            "username": username,
            "active": True
        })

        print("Username entered:", username)
        print("Teacher found:", teacher)

        if teacher and teacher["password"] == password:

            session["teacher_logged_in"] = True
            session["teacher_id"] = teacher["teacher_id"]
            session["teacher_name"] = teacher["teacher_name"]
            session["teacher_class"] = teacher["class"]
            session["teacher_section"] = teacher["section"]
            session["school_id"] = teacher["school_id"]

            flash("Login Successful!", "success")
            return redirect(url_for("teacher_login_bp.teacher_dashboard"))

        flash("Invalid Username or Password", "danger")

    return render_template("teacher_login.html")


# ---------------- Teacher Dashboard ----------------
@teacher_login_bp.route("/teacher-dashboard")
def teacher_dashboard():

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    return render_template("teacher_dashboard.html")


# ---------------- Logout ----------------
@teacher_login_bp.route("/teacher-logout")
def teacher_logout():

    session.clear()
    flash("Logged Out Successfully", "success")
    return redirect(url_for("teacher_login_bp.teacher_login"))
