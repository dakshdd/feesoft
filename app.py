import os
import json
import secrets
import string
from datetime import datetime
from flask import Blueprint, Flask, request, render_template_string, redirect, url_for, flash
from pymongo import ASCENDING, ReturnDocument
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from db import master_collection, counters_collection, transport_collection, tran_collection, school_collection

master_bp = Blueprint("master_bp", __name__)
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

if counters_collection.count_documents({"_id": "adm_code"}) == 0:
    counters_collection.insert_one({"_id": "adm_code", "seq": 0})

master_collection.create_index([("adm_code", ASCENDING)], unique=True)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ================= FEE DATA =================
def load_fee_data():
    try:
        with open("fee_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for x in data.values():
            x.pop("examination", None)
            x.setdefault("admission", 0)
            x.setdefault("annual", 0)
            x.setdefault("tuition", 0)

        return data
    except:
        return {}


# ================= ADMISSION FORM =================
FORM_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>New Admission</title>
<meta name="viewport" content="width=device-width,initial-scale=1">

<style>
*{box-sizing:border-box}
body{
font-family:Arial,sans-serif;
background:#f4f6f8;
margin:0;
padding:20px
}
.box{
max-width:1000px;
margin:auto;
background:#fff;
padding:22px;
border-radius:12px;
box-shadow:0 2px 12px #0001
}
h2{color:#17365d;margin-top:0}
.grid{
display:grid;
grid-template-columns:repeat(3,1fr);
gap:12px
}
.field label{
display:block;
font-weight:bold;
font-size:13px;
margin-bottom:5px
}
input,select{
width:100%;
padding:9px;
border:1px solid #ccc;
border-radius:6px
}
.full{grid-column:1/-1}
button{
background:#17365d;
color:white;
border:0;
padding:11px 20px;
border-radius:6px;
cursor:pointer
}
.photo-preview{
display:none;
width:110px;
height:120px;
object-fit:cover;
margin-top:8px;
border:1px solid #aaa;
border-radius:7px
}
@media(max-width:700px){
.grid{grid-template-columns:1fr}
.full{grid-column:auto}
}
</style>
</head>

<body>

<div class="box">
<h2>🎓 New Admission</h2>

<form method="post"
action="{{ url_for('master_bp.save_master') }}"
enctype="multipart/form-data">

<div class="grid">

<!-- NAME -->
<div class="field">
<label>Student Name</label>
<input name="student_name" required>
</div>

<!-- PHOTO AFTER NAME -->
<div class="field">
<label>Student Photo</label>
<input type="file" id="photo" name="photo" accept="image/*">
<img id="photoPreview" class="photo-preview">
</div>

<div class="field">
<label>Class</label>
<select id="class" name="class" required>
<option value="">-- Select Class --</option>
{% for c in fee_data %}
<option value="{{ c }}">{{ c }}</option>
{% endfor %}
</select>
</div>

<div class="field">
<label>Section</label>
<select name="sec" required>
<option value="">-- Select Section --</option>
<option>A</option>
<option>B</option>
<option>C</option>
</select>
</div>

<div class="field">
<label>Category</label>
<select name="catg">
<option value="">-- Select Category --</option>
<option>GEN</option>
<option>OBC</option>
<option>SC</option>
<option>ST</option>
</select>
</div>

<div class="field">
<label>Gender</label>
<select name="gender">
<option value="">-- Select Gender --</option>
<option>Male</option>
<option>Female</option>
<option>Other</option>
</select>
</div>

<div class="field">
<label>Date of Admission</label>
<input type="date" name="doa">
</div>

<div class="field">
<label>Father Name</label>
<input name="father_name">
</div>

<div class="field">
<label>Mother Name</label>
<input name="mother_name">
</div>

<div class="field">
<label>Contact</label>
<input name="contact">
</div>

<div class="field full">
<label>Address</label>
<input name="address">
</div>

<div class="field">
<label>Admission Fee</label>
<input id="admission_fee" name="admission_fee" type="number" value="0">
</div>

<div class="field">
<label>Annual Fee</label>
<input id="annual_fee" name="annual_fee" type="number" value="0">
</div>

<div class="field">
<label>Development Fee</label>
<input id="devl_fee" name="devl_fee" type="number" value="0">
</div>

<div class="field">
<label>Monthly Tuition Fee</label>
<input id="tuition_fee" name="tuition_fee" type="number" value="0">
</div>

<div class="field">
<label>Discount (On Tuition)</label>
<input id="discount" name="discount" type="number" value="0">
</div>

<div class="field">
<label>Transport Stand</label>
<select id="stand" name="transport_stand">
<option value="NIL">-- No Transport --</option>
{% for t in transports %}
<option value="{{ t.stand }}" data-charge="{{ t.charges }}">
{{ t.stand }} - ₹{{ t.charges }}
</option>
{% endfor %}
</select>
</div>

<div class="field">
<label>Transport Charges</label>
<input id="transport_charges" name="transport_charges" type="number" value="0">
</div>

<div class="field">
<label>E-Class Monthly</label>
<input name="eclass" type="number" value="0">
</div>

<div class="field">
<label>Science Monthly</label>
<input name="science" type="number" value="0">
</div>

<div class="field">
<label>Computer Monthly</label>
<input name="computer" type="number" value="0">
</div>

<div class="field">
<label>KGarten Monthly</label>
<input name="kgarten" type="number" value="0">
</div>

<div class="field">
<label>Fee Total</label>
<input id="total_fee" readonly>
</div>

<div class="field full">
<button type="submit">💾 Save Admission</button>
</div>

</div>
</form>
</div>


<script>
const feeData={{ fee_data|tojson }};
const cls=document.getElementById("class");
const discount=document.getElementById("discount");
const stand=document.getElementById("stand");
const photo=document.getElementById("photo");
const preview=document.getElementById("photoPreview");


function tuition(){
    let f=feeData[cls.value];
    if(!f)return;

    let t=Number(f.tuition)||0;
    let d=Number(discount.value)||0;

    document.getElementById("tuition_fee").value=Math.max(t-d,0);
    total();
}


function total(){
    let a=+document.getElementById("admission_fee").value||0;
    let y=+document.getElementById("annual_fee").value||0;
    let d=+document.getElementById("devl_fee").value||0;
    let t=+document.getElementById("tuition_fee").value||0;
    let tr=+document.getElementById("transport_charges").value||0;

    let ec=+document.querySelector('[name="eclass"]').value||0;
    let sc=+document.querySelector('[name="science"]').value||0;
    let co=+document.querySelector('[name="computer"]').value||0;
    let kg=+document.querySelector('[name="kgarten"]').value||0;

    document.getElementById("total_fee").value=
        a+y+d*12+t*12+tr*10.5+ec*12+sc*12+co*12+kg*12;
}


cls.addEventListener("change",()=>{
    let f=feeData[cls.value];
    if(!f)return;

    document.getElementById("admission_fee").value=f.admission||0;
    document.getElementById("annual_fee").value=f.annual||0;
    document.getElementById("devl_fee").value=f.development||0;

    tuition();
});

discount.addEventListener("input",tuition);

stand.addEventListener("change",function(){
    document.getElementById("transport_charges").value=
        this.options[this.selectedIndex].dataset.charge||0;
    total();
});

document.querySelectorAll('input[type="number"]').forEach(x=>{
    x.addEventListener("input",total);
});


/* PHOTO PREVIEW */
photo.addEventListener("change",function(){
    let file=this.files[0];

    if(!file){
        preview.src="";
        preview.style.display="none";
        return;
    }

    if(!file.type.startsWith("image/")){
        alert("Please select an image file.");
        this.value="";
        preview.src="";
        preview.style.display="none";
        return;
    }

    let reader=new FileReader();

    reader.onload=e=>{
        preview.src=e.target.result;
        preview.style.display="block";
    };

    reader.readAsDataURL(file);
});

total();
</script>

</body>
</html>
"""


# ================= FORM =================
@master_bp.route("/", methods=["GET"])
def index():
    fee_data = load_fee_data()

    transports = list(
        transport_collection.find(
            {},
            {"_id": 0, "stand": 1, "charges": 1}
        )
    )

    return render_template_string(
        FORM_HTML,
        fee_data=fee_data,
        transports=transports
    )


# ================= SAVE =================
@master_bp.route("/save", methods=["POST"])
def save_master():

    r = counters_collection.find_one_and_update(
        {"_id": "adm_code"},
        {"$inc": {"seq": 1}},
        return_document=ReturnDocument.AFTER
    )

    adm_code = f"ADM-{r['seq']:04d}"

    # PASSWORD
    password = "".join(
        secrets.choice(string.ascii_letters+string.digits)
        for _ in range(6)
    )

    # PHOTO
    photo_path = None
    photo = request.files.get("photo")

    if photo and photo.filename:
        ext = os.path.splitext(
            secure_filename(photo.filename)
        )[1].lower()

        if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            ext = ".jpg"

        filename = f"{adm_code}{ext}"
        path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        photo.save(path)
        photo_path = f"uploads/{filename}"

    def num(x):
        try:
            return float(request.form.get(x, 0) or 0)
        except:
            return 0

    student_name = request.form.get("student_name", "").strip()
    class_name = request.form.get("class", "").strip()
    sec = request.form.get("sec", "").strip()
    catg = request.form.get("catg", "").strip()
    gender = request.form.get("gender", "").strip()

    father = request.form.get("father_name", "").strip()
    mother = request.form.get("mother_name", "").strip()
    address = request.form.get("address", "").strip()
    contact = request.form.get("contact", "").strip()

    doa = request.form.get("doa", "").strip()

    if doa:
        try:
            doa = datetime.strptime(
                doa, "%Y-%m-%d"
            ).strftime("%d-%m-%Y")
        except:
            pass

    admission_fee = num("admission_fee")
    annual_fee = num("annual_fee")
    devl_monthly = num("devl_fee")
    tuition_fee = num("tuition_fee")
    discount = num("discount")

    transport_stand = request.form.get(
        "transport_stand", "NIL"
    ).strip()

    transport_charges = num("transport_charges")

    eclass_monthly = num("eclass")
    science_monthly = num("science")
    computer_monthly = num("computer")
    kgarten_monthly = num("kgarten")

    tuition_total = tuition_fee*12
    devl_fee = devl_monthly*12
    transport_total = transport_charges*10.5

    eclass = eclass_monthly*12
    science = science_monthly*12
    computer = computer_monthly*12
    kgarten = kgarten_monthly*12

    total_fee = (
        admission_fee +
        annual_fee +
        devl_fee +
        tuition_total +
        transport_total +
        eclass +
        science +
        computer +
        kgarten
    )

    # SAME DB STRUCTURE AS YOUR EXISTING DATA
    doc = {
        "adm_code": adm_code,
        "student_name": student_name,
        "class": class_name,
        "sec": sec,
        "catg": catg,
        "gender": gender,

        "father_name": father,
        "mother_name": mother,
        "address": address,
        "contact": contact,
        "doa": doa,

        "photo": photo_path,

        "transport_stand": transport_stand,
        "transport_charges": transport_charges,

        "admission_fee": admission_fee,
        "annual_fee": annual_fee,
        "devl_fee": devl_fee,
        "discount": discount,
        "tuition_fee": tuition_fee,
        "tuition_total": tuition_total,
        "transport_total": transport_total,

        "total_fee": total_fee,
        "paid_fee": 0,
        "balance_fee": total_fee,

        "password_hash": generate_password_hash(password),

        "eclass": eclass,
        "science": science,
        "computer": computer,
        "kgarten": kgarten,

        "april_status": "Unpaid",
        "may_status": "Unpaid",
        "june_status": "Unpaid",
        "july_status": "Unpaid",

        "created_at": datetime.now()
    }

    master_collection.insert_one(doc)

    # PASSWORD DB MEIN HASH HAI,
    # ORIGINAL PASSWORD SIRF CURRENT RESPONSE FLOW MEIN PASS HOGA
    return redirect(
        url_for(
            "master_bp.admission_detail",
            adm_code=adm_code,
            password=password
        )
    )


# ================= DETAIL + PRINT =================
@master_bp.route("/detail/<adm_code>")
def admission_detail(adm_code):

    student = master_collection.find_one(
        {"adm_code": adm_code}
    )

    if not student:
        return "Student not found", 404

    school = get_school()

    password = request.args.get("password", "")

    photo_url = None

    if student.get("photo"):
        photo_url = url_for(
            "static",
            filename=student["photo"]
        )

    return render_template_string(
        """
<!DOCTYPE html>
<html>
<head>
<title>Admission Details</title>
<meta name="viewport" content="width=device-width,initial-scale=1">

<style>
body{
font-family:Arial;
background:#f4f6f8;
margin:0;
padding:20px
}
.card{
max-width:850px;
margin:auto;
background:#fff;
padding:25px;
border-radius:12px;
box-shadow:0 2px 12px #0002
}
.header{
text-align:center;
border-bottom:2px solid #17365d;
padding-bottom:12px
}
.header h1{
margin:0;
color:#17365d
}
.top{
display:flex;
justify-content:space-between;
gap:20px;
margin-top:18px
}
.photo{
width:120px;
height:140px;
object-fit:cover;
border:1px solid #aaa;
border-radius:6px
}
.grid{
display:grid;
grid-template-columns:1fr 1fr;
gap:10px;
margin-top:15px
}
.item{
padding:9px;
background:#f7f8fa;
border-radius:5px
}
.login{
margin-top:20px;
padding:15px;
background:#eef5ff;
border:1px solid #b9d3f5;
border-radius:8px
}
.login b{
font-size:18px
}
.fee{
margin-top:20px;
border-top:2px solid #ddd;
padding-top:10px
}
.total{
font-size:18px;
font-weight:bold;
line-height:1.8
}
.actions{
text-align:center;
margin-top:25px
}
button{
background:#17365d;
color:#fff;
border:0;
padding:11px 22px;
border-radius:6px;
margin:5px;
cursor:pointer
}
@media(max-width:600px){
.top{display:block}
.grid{grid-template-columns:1fr}
}
@media print{
body{background:white;padding:0}
.card{
box-shadow:none;
max-width:none
}
.actions{display:none}
}
</style>
</head>

<body>

<div class="card">

<div class="header">
<h1>{{ school.get("school_name","MODERN ERA SCHOOL") }}</h1>
<p>{{ school.get("address","") }}</p>
<p>{{ school.get("phone","") }}</p>
<h3>NEW ADMISSION DETAILS</h3>
</div>


<div class="top">

<div style="flex:1">

<div class="grid">

<div class="item">
<b>Admission Code</b><br>
{{ student.get("adm_code","") }}
</div>

<div class="item">
<b>Student Name</b><br>
{{ student.get("student_name","") }}
</div>

<div class="item">
<b>Class</b><br>
{{ student.get("class","") }}
</div>

<div class="item">
<b>Section</b><br>
{{ student.get("sec","") }}
</div>

<div class="item">
<b>Gender</b><br>
{{ student.get("gender","") }}
</div>

<div class="item">
<b>Category</b><br>
{{ student.get("catg","") }}
</div>

<div class="item">
<b>Date of Admission</b><br>
{{ student.get("doa","") }}
</div>

<div class="item">
<b>Contact</b><br>
{{ student.get("contact","") }}
</div>

<div class="item">
<b>Father Name</b><br>
{{ student.get("father_name","") }}
</div>

<div class="item">
<b>Mother Name</b><br>
{{ student.get("mother_name","") }}
</div>

<div class="item" style="grid-column:1/-1">
<b>Address</b><br>
{{ student.get("address","") }}
</div>

</div>
</div>

{% if photo_url %}
<img src="{{ photo_url }}" class="photo">
{% endif %}

</div>


<!-- PARENT LOGIN -->
<div class="login">

<h3>🔐 Parent Online Fee Login</h3>

<div class="grid">

<div class="item">
<b>Admission Code / Login ID</b><br>
{{ student.get("adm_code","") }}
</div>

<div class="item">
<b>Parent Password</b><br>
{{ password if password else "Password already saved securely." }}
</div>

</div>

</div>


<!-- FEE -->
<div class="fee">

<h3>Fee Details</h3>

<div class="grid">

<div class="item">
<b>Admission Fee</b><br>
₹{{ student.get("admission_fee",0) }}
</div>

<div class="item">
<b>Annual Fee</b><br>
₹{{ student.get("annual_fee",0) }}
</div>

<div class="item">
<b>Development Fee</b><br>
₹{{ student.get("devl_fee",0) }}
</div>

<div class="item">
<b>Tuition Total</b><br>
₹{{ student.get("tuition_total",0) }}
</div>

<div class="item">
<b>Transport Total</b><br>
₹{{ student.get("transport_total",0) }}
</div>

<div class="item">
<b>E-Class</b><br>
₹{{ student.get("eclass",0) }}
</div>

<div class="item">
<b>Science</b><br>
₹{{ student.get("science",0) }}
</div>

<div class="item">
<b>Computer</b><br>
₹{{ student.get("computer",0) }}
</div>

<div class="item">
<b>KGarten</b><br>
₹{{ student.get("kgarten",0) }}
</div>

</div>

<div class="total">
Total Fee: ₹{{ student.get("total_fee",0) }}<br>
Paid Fee: ₹{{ student.get("paid_fee",0) }}<br>
Balance Fee: ₹{{ student.get("balance_fee",0) }}
</div>

</div>


<div class="actions">

<button onclick="window.print()">
🖨️ Print Details
</button>

<button onclick="location.href='{{ url_for("master_bp.index") }}'">
➕ New Admission
</button>

</div>

</div>

</body>
</html>
""",
        student=student,
        school=school,
        photo_url=photo_url,
        password=password
    )


# ================= SCHOOL =================
def get_school():
    try:
        return school_collection.find_one({}, {"_id": 0}) or {}
    except:
        return {}


app.register_blueprint(master_bp)
