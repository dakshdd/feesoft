from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from werkzeug.security import check_password_hash
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"   # change this in production
app.permanent_session_lifetime = timedelta(minutes=30)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
users_db = client["users_name"]
users_col = users_db["users"]


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users_col.find_one({"username": username})
        if user and check_password_hash(user["password_hash"], password):
            session["username"] = username
            session["role"] = user["role"]

            # Role-based redirect
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            elif user["role"] == "teacher":
                return redirect(url_for("teacher_dashboard"))
            elif user["role"] == "parent":
                return redirect(url_for("parent_dashboard"))
            elif user["role"] == "clerk":
                return redirect(url_for("clerk_dashboard"))
            else:
                return "❌ Unknown role"
        else:
            return "❌ Invalid username or password"
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
