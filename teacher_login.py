from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import teachers_collection, users_collection
from werkzeug.security import check_password_hash

teacher_login_bp = Blueprint("teacher_login_bp", __name__)


@teacher_login_bp.route("/teacher-login", methods=["GET", "POST"])
def teacher_login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        teacher = teachers_collection.find_one({
            "username": username,
            "active": True
        })

        if not teacher:
            flash("Invalid Username or Password", "danger")
            return render_template("teacher_login.html")

        password_hash = teacher.get("password_hash", "")

        if not password_hash or not check_password_hash(password_hash, password):
            flash("Invalid Username or Password", "danger")
            return render_template("teacher_login.html")

        user = users_collection.find_one({
            "username": username,
            "role": "teacher",
            "active": True
        })

        print("\n========== LOGIN ==========")
        print("USERNAME:", repr(username))
        print("USER:", user)

        if not user:
            flash("Teacher user account not found.", "danger")
            return render_template("teacher_login.html")

        teacher_class = str(user.get("class_id", "")).strip()
        teacher_section = str(user.get("sec_id", "")).strip()

        print("CLASS_ID:", repr(teacher_class))
        print("SEC_ID:", repr(teacher_section))

        if not teacher_class:
            flash("Class not assigned to this teacher.", "danger")
            return render_template("teacher_login.html")

        if not teacher_section:
            flash("Section not assigned to this teacher.", "danger")
            return render_template("teacher_login.html")

        session.clear()

        session["teacher_logged_in"] = True
        session["teacher_username"] = username
        session["user"] = username
        session["teacher_id"] = str(user.get("teacher_id", ""))
        session["teacher_name"] = user.get("teacher_name", username)

        session["teacher_class"] = teacher_class
        session["teacher_section"] = teacher_section

        session["school_id"] = user.get("school_id", "SCH001")
        session["role"] = "teacher"

        session.permanent = True
        session.modified = True

        print("\n========== SESSION SAVED ==========")
        print(dict(session))
        print("CLASS:", repr(session["teacher_class"]))
        print("SECTION:", repr(session["teacher_section"]))
        print("===================================\n")

        flash("Login Successful!", "success")
        return redirect(url_for("teacher_login_bp.teacher_dashboard"))

    return render_template("teacher_login.html")


@teacher_login_bp.route("/teacher-dashboard")
def teacher_dashboard():

    if not session.get("teacher_logged_in"):
        return redirect(url_for("teacher_login_bp.teacher_login"))

    print("\n========== DASHBOARD SESSION ==========")
    print(dict(session))
    print("CLASS:", repr(session.get("teacher_class")))
    print("SECTION:", repr(session.get("teacher_section")))
    print("=======================================\n")

    return render_template(
        "teacher_dashboard.html",
        teacher_name=session.get("teacher_name", "Teacher"),
        teacher_class=session.get("teacher_class", ""),
        teacher_section=session.get("teacher_section", "")
    )


@teacher_login_bp.route("/teacher-logout")
def teacher_logout():

    session.clear()

    flash("Logged Out Successfully", "success")

    return redirect(url_for("teacher_login_bp.teacher_login"))
