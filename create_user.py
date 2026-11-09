
import os
import json

from flask import Blueprint, render_template, request
from werkzeug.security import generate_password_hash

from db import users_collection

create_user_bp = Blueprint("create_user_bp", __name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_fee_data():
    file_path = os.path.join(BASE_DIR, "fee_data.json")

    print("FEE JSON PATH:", file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {}

        print("CLASSES LOADED:", list(data.keys()))
        return data

    except Exception as e:
        print("FEE DATA ERROR:", str(e))
        return {}


@create_user_bp.route("/create_user", methods=["GET", "POST"])
def create_user():

    fee_data = load_fee_data()
    classes = list(fee_data.keys())

    error = None
    success = None

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip()
        class_id = request.form.get("class_id", "").strip()
        sec_id = request.form.get("sec_id", "").strip()
        adm_code = request.form.get("adm_code", "").strip()

        if not username or not password:
            error = "Username and password required!"

        elif role not in ["admin", "teacher", "parent", "clerk"]:
            error = "Invalid role!"

        elif role == "teacher" and class_id not in fee_data:
            error = "Please select a valid class!"

        elif role == "teacher" and sec_id not in ["A", "B", "C"]:
            error = "Please select a valid section!"

        elif role == "parent" and not adm_code:
            error = "Admission Code required!"

        elif users_collection.find_one({
            "username": {"$regex": f"^{username}$", "$options": "i"}
        }):
            error = "Username already exists!"

        else:

            user = {
                "username": username,
                "password_hash": generate_password_hash(password),
                "role": role
            }

            if role == "teacher":
                user.update({
                    "class_id": class_id,
                    "sec_id": sec_id
                })

            elif role == "parent":
                user["adm_code"] = adm_code

            users_collection.insert_one(user)

            success = "User created successfully!"

    return render_template(
        "create_user.html",
        fee_data=fee_data,
        classes=classes,
        error=error,
        success=success
    )
