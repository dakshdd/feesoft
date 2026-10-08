from flask import Blueprint, request, render_template_string, redirect, url_for, flash, session
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
from db import teachers_collection, users_collection

teachers_staff_bp = Blueprint("teachers_staff_bp", __name__)


def admin_required():
    return session.get("role") in ("admin", "Admin")


BASE = """<!DOCTYPE html><html><head><title>Teachers & Staff</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{font-family:Arial;margin:0;background:#f4f6f9;color:#222}.container{max-width:1200px;margin:25px auto;background:#fff;padding:22px;border-radius:12px;box-shadow:0 2px 10px #ddd}h2{margin-top:0;color:#2c3e50}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}input,select,textarea{width:100%;padding:9px;box-sizing:border-box;border:1px solid #ccc;border-radius:6px}textarea{height:70px}button,.btn{border:0;padding:9px 14px;border-radius:6px;cursor:pointer;text-decoration:none;display:inline-block}.save{background:#198754;color:white}.edit{background:#0d6efd;color:white}.delete{background:#dc3545;color:white}.back{background:#6c757d;color:white}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #ddd;padding:9px;text-align:left}th{background:#2c3e50;color:white}.msg{padding:10px;background:#e8f5e9;margin:10px 0;border-radius:6px}.actions{white-space:nowrap}@media(max-width:800px){.grid{grid-template-columns:1fr}table{font-size:12px}}
</style></head><body><div class="container">{{content|safe}}</div></body></html>"""

FIELDS = [
    ("name", "Name", "text"), ("type", "Type",
                               "select"), ("gender", "Gender", "select"),
    ("mobile", "Mobile", "text"), ("email", "Email",
                                   "email"), ("address", "Address", "textarea"),
    ("qualification", "Qualification", "text"), ("subject", "Subject", "text"),
    ("class", "Class", "text"), ("section", "Section",
                                 "text"), ("joining_date", "Joining Date", "date"),
    ("salary", "Salary", "number"), ("status", "Status", "select"),
    ("username", "Login Username", "text"), ("password", "Login Password", "password")
]


def form_html(data=None):
    data = data or {}
    h = '<h2>Teacher / Staff Details</h2><form method="POST"><div class="grid">'
    for key, label, typ in FIELDS:
        val = data.get(key, "")
        if key == "password":
            val = ""
        if typ == "select":
            opts = ["Teacher", "Staff"] if key == "type" else (
                ["Male", "Female", "Other"] if key == "gender" else ["Active", "Inactive"])
            h += f'<div><label>{label}</label><select name="{key}"><option value="">Select</option>'
            for x in opts:
                h += f'<option value="{x}" {"selected" if str(val) == x else ""}>{x}</option>'
            h += '</select></div>'
        elif typ == "textarea":
            h += f'<div><label>{label}</label><textarea name="{key}">{val}</textarea></div>'
        else:
            req = "required" if key in ("name", "username") else ""
            if key == "password" and not data:
                req = "required"
            h += f'<div><label>{label}</label><input type="{typ}" name="{key}" value="{val}" {req}></div>'
    h += f'</div><br><button class="save">Save</button> <a class="btn back" href="{url_for("teachers_staff_bp.teachers_staff")}">Back</a></form>'
    return h


@teachers_staff_bp.route("/teachers-staff")
def teachers_staff():
    if not admin_required():
        return redirect("/login")
    rows = list(teachers_collection.find().sort("name", 1))
    content = """<h2>Teachers & Staff</h2>
    {% with m=get_flashed_messages() %}{% for x in m %}<div class="msg">{{x}}</div>{% endfor %}{% endwith %}
    <a class="btn save" href="{{url_for('teachers_staff_bp.add_teacher')}}">+ Add Teacher / Staff</a>
    <table><tr><th>Name</th><th>Type</th><th>Gender</th><th>Mobile</th><th>Qualification</th><th>Subject</th><th>Class</th><th>Section</th><th>Joining</th><th>Salary</th><th>Status</th><th>Action</th></tr>
    {% for x in rows %}<tr>
    <td>{{x.get('name','')}}</td><td>{{x.get('type','')}}</td><td>{{x.get('gender','')}}</td><td>{{x.get('mobile','')}}</td>
    <td>{{x.get('qualification','')}}</td><td>{{x.get('subject','')}}</td><td>{{x.get('class','')}}</td><td>{{x.get('section','')}}</td>
    <td>{{x.get('joining_date','')}}</td><td>{{x.get('salary','')}}</td><td>{{x.get('status','')}}</td>
    <td><a class="btn edit" href="{{url_for('teachers_staff_bp.edit_teacher',id=x['_id'])}}">Edit</a>
    <a class="btn delete" href="{{url_for('teachers_staff_bp.teachers_staff_delete',id=x['_id'])}}" onclick="return confirm('Delete this record?')">Delete</a></td>
    </tr>{% else %}<tr><td colspan="12" style="text-align:center">No records found</td></tr>{% endfor %}</table>"""
    return render_template_string(BASE, content=render_template_string(content, rows=rows))


@teachers_staff_bp.route("/teachers-staff/add", methods=["GET", "POST"])
def add_teacher():
    if not admin_required():
        return redirect("/login")

    if request.method == "POST":
        data = {k: request.form.get(k, "").strip() for k, _, _ in FIELDS}
        username = data["username"]
        raw_password = data["password"]

        if not data["name"] or not username or not raw_password:
            flash("Name, Username and Password are required.")
            return redirect(url_for("teachers_staff_bp.add_teacher"))

        if teachers_collection.find_one({"username": username}) or users_collection.find_one({"username": username}):
            flash("Username already exists.")
            return redirect(url_for("teachers_staff_bp.add_teacher"))

        try:
            data["salary"] = float(data["salary"]) if data["salary"] else 0
        except:
            data["salary"] = 0

        password_hash = generate_password_hash(raw_password)
        data["password_hash"] = password_hash
        data.pop("password", None)
        data["school_id"] = "SCH001"

        teacher_id = teachers_collection.insert_one(data).inserted_id

        users_collection.insert_one({
            "username": username,
            "password_hash": password_hash,
            "role": "teacher",
            "teacher_name": data["name"],
            "class_id": data.get("class", ""),
            "sec_id": data.get("section", ""),
            "school_id": "SCH001",
            "active": data.get("status", "Active") != "Inactive",
            "teacher_id": teacher_id
        })

        flash("Teacher / Staff added successfully.")
        return redirect(url_for("teachers_staff_bp.teachers_staff"))

    return render_template_string(BASE, content=form_html())


@teachers_staff_bp.route("/teachers-staff/edit/<id>", methods=["GET", "POST"])
def edit_teacher(id):
    if not admin_required():
        return redirect("/login")

    try:
        oid = ObjectId(id)
    except:
        return redirect(url_for("teachers_staff_bp.teachers_staff"))

    old = teachers_collection.find_one({"_id": oid})
    if not old:
        return redirect(url_for("teachers_staff_bp.teachers_staff"))

    if request.method == "POST":
        data = {k: request.form.get(k, "").strip() for k, _, _ in FIELDS}
        username = data["username"]
        raw_password = data["password"]

        if not data["name"] or not username:
            flash("Name and Username are required.")
            return redirect(url_for("teachers_staff_bp.edit_teacher", id=id))

        other = teachers_collection.find_one(
            {"username": username, "_id": {"$ne": oid}})
        if other:
            flash("Username already exists.")
            return redirect(url_for("teachers_staff_bp.edit_teacher", id=id))

        old_username = old.get("username", "")
        user = users_collection.find_one({"teacher_id": oid})

        if not user and old_username:
            user = users_collection.find_one({"username": old_username})

        if raw_password:
            password_hash = generate_password_hash(raw_password)
        elif user:
            password_hash = user.get("password_hash", "")
        else:
            password_hash = old.get("password_hash", "")

        if not password_hash:
            flash("Please enter a password.")
            return redirect(url_for("teachers_staff_bp.edit_teacher", id=id))

        try:
            data["salary"] = float(data["salary"]) if data["salary"] else 0
        except:
            data["salary"] = 0

        data["password_hash"] = password_hash
        data.pop("password", None)
        data["school_id"] = old.get("school_id", "SCH001")

        teachers_collection.update_one({"_id": oid}, {"$set": data})

        user_doc = {
            "username": username,
            "password_hash": password_hash,
            "role": "teacher",
            "teacher_name": data["name"],
            "class_id": data.get("class", ""),
            "sec_id": data.get("section", ""),
            "school_id": data["school_id"],
            "active": data.get("status", "Active") != "Inactive",
            "teacher_id": oid
        }

        if user:
            users_collection.update_one(
                {"_id": user["_id"]}, {"$set": user_doc})
        else:
            users_collection.insert_one(user_doc)

        flash("Teacher / Staff updated successfully.")
        return redirect(url_for("teachers_staff_bp.teachers_staff"))

    return render_template_string(BASE, content=form_html(old))


@teachers_staff_bp.route("/teachers-staff/delete/<id>")
def teachers_staff_delete(id):
    if not admin_required():
        return redirect("/login")

    try:
        oid = ObjectId(id)
    except:
        return redirect(url_for("teachers_staff_bp.teachers_staff"))

    old = teachers_collection.find_one({"_id": oid})

    if old:
        username = old.get("username", "")
        users_collection.delete_many(
            {"$or": [{"teacher_id": oid}, {"username": username}]})
        teachers_collection.delete_one({"_id": oid})
        flash("Teacher / Staff deleted successfully.")
    else:
        flash("Teacher / Staff not found.")

    return redirect(url_for("teachers_staff_bp.teachers_staff"))
