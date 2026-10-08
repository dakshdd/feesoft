from flask import Blueprint, request, redirect, url_for, render_template_string, flash
import json
import os

feestru_bp = Blueprint("feestru_bp", __name__)
DATA_FILE = "fee_data.json"

CLASS_ORDER = ["NURSERY", "LKG", "UKG", "1st", "2nd", "3rd", "4th", "5th", "6th",
               "7th", "8th", "9th", "10th", "11th", "12th"]

DEFAULT_FEES = {
    "NURSERY": {"admission": 2500, "annual": 1500, "tuition": 1200},
    "LKG": {"admission": 2500, "annual": 1500, "tuition": 1200},
    "UKG": {"admission": 3000, "annual": 1800, "tuition": 1500},
    "1st": {"admission": 3500, "annual": 2000, "tuition": 1800},
    "2nd": {"admission": 3500, "annual": 2000, "tuition": 1900},
    "3rd": {"admission": 4000, "annual": 2200, "tuition": 2000}
}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_FEES)
        return DEFAULT_FEES
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for fees in data.values():
            fees.pop("examination", None)
            for k in ["admission", "annual", "tuition"]:
                fees[k] = float(fees.get(k, 0))
        save_data(data)
        return data
    except Exception:
        save_data(DEFAULT_FEES)
        return DEFAULT_FEES


def classes(data):
    return [x for x in CLASS_ORDER if x in data]+sorted(x for x in data if x not in CLASS_ORDER)


TEMPLATE = """
<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fee Structure</title>
<style>
body{margin:0;background:#f3f4f6;font-family:Arial;color:#111827}
.wrap{max-width:1100px;margin:30px auto;padding:15px}.card{background:#fff;padding:22px;border-radius:10px;box-shadow:0 3px 12px #0002}
h1{color:#2563eb}.row{display:flex;gap:15px;flex-wrap:wrap}.field{flex:1;min-width:180px}
input,select{width:100%;box-sizing:border-box;padding:9px;border:1px solid #ccc;border-radius:6px}
button{padding:9px 16px;border:0;border-radius:6px;cursor:pointer}
.save{background:#22c55e;color:white}.add{background:#6b7280;color:white}.delete{background:#ef4444;color:white}
table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #ddd;padding:8px;text-align:center}
.msg{padding:10px;background:#d1fae5;margin:10px 0;border-radius:5px}.error{background:#fee2e2}
.total{font-size:20px;font-weight:bold;color:#dc2626;margin-top:8px}
</style></head><body><div class="wrap"><div class="card">

<h1>Fee Structure</h1>

{% with messages=get_flashed_messages(with_categories=true) %}
{% for cat,msg in messages %}<div class="msg {{'error' if cat=='error' else ''}}">{{msg}}</div>{% endfor %}
{% endwith %}

<form method="get" action="{{url_for('feestru_bp.index')}}">
<div class="row">
<div class="field"><label>Select Class</label>
<select name="class" onchange="this.form.submit()">
{% for c in classes %}<option value="{{c}}" {{'selected' if c==selected else ''}}>{{c}}</option>{% endfor %}
</select></div>

<div class="field"><label>Add New Class</label>
<input name="new_class" placeholder="e.g. 4th">
<button class="add" formaction="{{url_for('feestru_bp.add_class')}}">Add</button>
</div>
</div></form>

<form method="post" action="{{url_for('feestru_bp.save')}}">
<input type="hidden" name="class" value="{{selected}}">

<div class="row" style="margin-top:18px">
<div class="field"><label>Admission Fee</label>
<input type="number" name="admission" value="{{fees.admission}}" oninput="total()"></div>

<div class="field"><label>Annual Fee</label>
<input type="number" name="annual" value="{{fees.annual}}" oninput="total()"></div>

<div class="field"><label>Monthly Tuition Fee</label>
<input type="number" name="tuition" value="{{fees.tuition}}" oninput="total()"></div>
</div>

<div class="total" id="total">₹ {{'%.2f'|format(total)}}</div>
<p style="color:#6b7280">Total = Admission + Annual + (12 × Monthly Tuition)</p>

<button class="save" type="submit">Save</button>
<button class="delete" type="button" onclick="delClass()">Delete Class</button>
</form>

<table><thead><tr>
<th>Class</th><th>Admission</th><th>Annual</th><th>Monthly Tuition</th><th>Total</th>
</tr></thead><tbody>
{% for c,f in all_data.items() %}<tr>
<td>{{c}}</td><td>₹ {{'%.2f'|format(f.admission)}}</td>
<td>₹ {{'%.2f'|format(f.annual)}}</td>
<td>₹ {{'%.2f'|format(f.tuition)}}</td>
<td>₹ {{'%.2f'|format(f.admission+f.annual+12*f.tuition)}}</td>
</tr>{% endfor %}
</tbody></table>

</div></div>

<script>
function total(){
 let a=+document.querySelector('[name=admission]').value||0;
 let n=+document.querySelector('[name=annual]').value||0;
 let t=+document.querySelector('[name=tuition]').value||0;
 document.getElementById('total').innerText='₹ '+(a+n+12*t).toFixed(2);
}
function delClass(){
 let c=document.querySelector('[name=class]').value;
 if(confirm('Delete class "'+c+'"?')){
  let f=document.createElement('form');
  f.method='post';f.action="{{url_for('feestru_bp.delete_class')}}";
  let i=document.createElement('input');
  i.type='hidden';i.name='class';i.value=c;f.appendChild(i);
  document.body.appendChild(f);f.submit();
 }
}
</script></body></html>
"""


@feestru_bp.route("/home")
def structure_home():
    return redirect(url_for("feestru_bp.index"))


@feestru_bp.route("/", methods=["GET"])
def index():
    data = load_data()
    cls = classes(data)
    selected = request.args.get("class") or (cls[0] if cls else "NURSERY")
    if selected not in data and cls:
        selected = cls[0]
    fees = data.get(selected, {"admission": 0, "annual": 0, "tuition": 0})
    total = fees["admission"]+fees["annual"]+12*fees["tuition"]
    return render_template_string(
        TEMPLATE, classes=cls, selected=selected,
        fees=type("F", (), fees), total=total,
        all_data={c: type("F", (), data[c]) for c in cls}
    )


@feestru_bp.route("/add", methods=["GET"])
def add_class():
    data = load_data()
    c = (request.args.get("new_class") or "").strip()
    aliases = {"nursery": "NURSERY", "pre nursery": "NURSERY", "lkg": "LKG",
               "lower kg": "LKG", "ukg": "UKG", "upper kg": "UKG", "kg": "UKG"}
    c = aliases.get(c.lower(), c)
    if not c:
        flash("Please enter a class name.", "error")
        return redirect(url_for("feestru_bp.index"))
    if c in data:
        flash(f'"{c}" already exists.', "error")
    else:
        data[c] = {"admission": 0, "annual": 0, "tuition": 0}
        save_data(data)
        flash(f'Class "{c}" added.', "ok")
    return redirect(url_for("feestru_bp.index", **{"class": c}))


@feestru_bp.route("/save", methods=["POST"])
def save():
    data = load_data()
    c = (request.form.get("class") or "").strip()
    if not c:
        flash("Class is missing.", "error")
        return redirect(url_for("feestru_bp.index"))
    try:
        data[c] = {
            "admission": max(0, float(request.form.get("admission", 0))),
            "annual": max(0, float(request.form.get("annual", 0))),
            "tuition": max(0, float(request.form.get("tuition", 0)))
        }
    except ValueError:
        flash("Invalid number input.", "error")
        return redirect(url_for("feestru_bp.index", **{"class": c}))
    save_data(data)
    flash(f'Fees saved for "{c}".', "ok")
    return redirect(url_for("feestru_bp.index", **{"class": c}))


@feestru_bp.route("/delete", methods=["POST"])
def delete_class():
    data = load_data()
    c = (request.form.get("class") or "").strip()
    if c not in data:
        flash("Class not found.", "error")
    else:
        del data[c]
        save_data(data)
        flash(f'Class "{c}" deleted.', "ok")
    return redirect(url_for("feestru_bp.index"))
