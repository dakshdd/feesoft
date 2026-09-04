import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from datetime import timedelta

from db import users_collection


app = Flask(__name__)

# Use Render Environment Variable
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.permanent_session_lifetime = timedelta(minutes=30)


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Find user from school_db.users
        user = users_collection.find_one({
            "username": username
        })

        if user:
            print(f"✅ User found: {username}")
        else:
            print(f"❌ User not found: {username}")

        # Check password
        if user and check_password_hash(
            user.get("password_hash", ""),
            password
        ):

            session.permanent = True
            session["username"] = username
            session["role"] = user.get("role", "")

            role = user.get("role")

            # Role-based redirect
            if role == "admin":
                return redirect(url_for("admin_dashboard"))

            elif role == "teacher":
                return redirect(url_for("teacher_dashboard"))

            elif role == "parent":
                return redirect(url_for("parent_dashboard"))

            elif role == "clerk":
                return redirect(url_for("clerk_dashboard"))

            else:
                return "❌ Unknown role"

        else:
            return render_template(
                "login.html",
                error="Invalid credentials"
            )

    return render_template("login.html")


@app.route("/admin")
def admin_dashboard():
    return render_template("admin_dashboard.html")


@app.route("/teacher")
def teacher_dashboard():
    return render_template("teacher_dashboard.html")


@app.route("/parent")
def parent_dashboard():
    return render_template("parent_dashboard.html")


@app.route("/clerk")
def clerk_dashboard():
    return render_template("clerk_dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
