from flask import Blueprint, Flask, request, redirect, url_for, render_template_string, flash
import json
import os

app = Flask(__name__)
app.secret_key = "change-this-key"

# ------------------ Blueprint Setup ------------------
feestru_bp = Blueprint("feestru_bp", __name__)


@feestru_bp.route("/home")
def structure_home():
    return redirect(url_for("feestru_bp.index"))


# ------------------ Data Handling ------------------
DATA_FILE = "fee_data.json"

DEFAULT_FEES = {
    "Nursery": {"admission": 2500, "annual": 1500, "examination": 800, "tuition": 1200},
    "KG":      {"admission": 3000, "annual": 1800, "examination": 900, "tuition": 1500},
    "Class 1": {"admission": 3500, "annual": 2000, "examination": 1000, "tuition": 1800},
    "Class 2": {"admission": 3500, "annual": 2000, "examination": 1000, "tuition": 1900},
    "Class 3": {"admission": 4000, "annual": 2200, "examination": 1100, "tuition": 2000},
}


def load_data():
    if not os.path.exists(DATA_FILE):
        save_data(DEFAULT_FEES)
        return DEFAULT_FEES
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            for cls, fees in data.items():
                for k in ["admission", "annual", "examination", "tuition"]:
                    fees[k] = float(fees.get(k, 0))
            return data
        except json.JSONDecodeError:
            save_data(DEFAULT_FEES)
            return DEFAULT_FEES


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ------------------ Template ------------------
TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Fee Structure</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { background: #f3f4f6; color: #111827; font-family: system-ui, Segoe UI, Roboto, Arial; margin: 0; }
    .wrap { max-width: 1200px; margin: 40px auto; padding: 0 16px; }
    .card { background: #fff; border-radius: 10px; padding: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    h1 { margin-top: 0; color: #2563eb; }
    .row, .row-3 { display: flex; gap: 16px; flex-wrap: wrap; }
    .row-3 div { flex: 1; }
    .flex { display: flex; gap: 12px; }
    input, select { padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; width: 100%; }
    input:focus, select:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 4px #2563eb55; }
    .btn { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; transition: 0.2s; }
    .btn-primary { background: #22c55e; color: #fff; }
    .btn-primary:hover { background: #16a34a; }
    .btn-secondary { background: #6b7280; color: #fff; }
    .btn-secondary:hover { background: #4b5563; }
    .btn-danger { background: #ef4444; color: #fff; }
    .btn-danger:hover { background: #dc2626; }
    .table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    .table th, .table td { border: 1px solid #d1d5db; padding: 8px; text-align: center; }
    .table tr:hover { background: #f9fafb; }
    .flash { padding: 10px; margin: 10px 0; border-radius: 4px; background: #d1fae5; }
    .flash.error { background: #fee2e2; }
    .muted { color: #6b7280; font-size: 0.9em; }
    .total { font-weight: bold; font-size: 1.3em; color: #dc2626; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Fee Structure</h1>

      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for category, msg in messages %}
            <div class="flash {{ 'error' if category == 'error' else '' }}">{{ msg }}</div>
          {% endfor %}
        {% endif %}
      {% endwith %}

      <!-- Class selection + add -->
      <form method="get" action="{{ url_for('feestru_bp.index') }}">
        <div class="row">
          <div>
            <label>Select class</label>
            <select name="class" onchange="this.form.submit()">
              {% for cls in classes %}
                <option value="{{ cls }}" {{ 'selected' if cls == selected_class else '' }}>{{ cls }}</option>
              {% endfor %}
            </select>
          </div>
          <div>
            <label>Add new class</label>
            <div class="flex">
              <input type="text" name="new_class" placeholder="e.g., Class 4">
              <button class="btn btn-secondary" formaction="{{ url_for('feestru_bp.add_class') }}">Add</button>
            </div>
          </div>
        </div>
      </form>

      <!-- Fee entry -->
      <form method="post" action="{{ url_for('feestru_bp.save') }}">
        <input type="hidden" name="class" value="{{ selected_class }}">
        <div class="row-3 mt">
          <div><label>Admission fee</label><input type="number" name="admission" value="{{ fees.admission }}" oninput="updateTotal()"></div>
          <div><label>Annual fee</label><input type="number" name="annual" value="{{ fees.annual }}" oninput="updateTotal()"></div>
          <div><label>Examination fee</label><input type="number" name="examination" value="{{ fees.examination }}" oninput="updateTotal()"></div>
        </div>
        <div class="row mt">
          <div>
            <label>Tuition fee (monthly)</label>
            <input type="number" name="tuition" value="{{ fees.tuition }}" oninput="updateTotal()">
          </div>
          <div class="right">
            <div class="muted">Auto total (Admission + Annual + Examination + 12 × Tuition)</div>
            <div class="total" id="total">₹ {{ "%.2f"|format(total) }}</div>
          </div>
        </div>
        <div class="flex mt">
          <button class="btn btn-primary" type="submit">Save</button>
          <button class="btn btn-danger" type="button" onclick="confirmDelete()">Delete class</button>
        </div>
      </form>

      <!-- Table -->
      <table class="table">
        <thead>
          <tr>
            <th>Class</th><th>Admission</th><th>Annual</th><th>Examination</th><th>Tuition</th><th>Total</th>
          </tr>
        </thead>
        <tbody>
          {% for cls, f in all_data.items() %}
          <tr>
            <td>{{ cls }}</td>
            <td>₹ {{ "%.2f"|format(f.admission) }}</td>
            <td>₹ {{ "%.2f"|format(f.annual) }}</td>
            <td>₹ {{ "%.2f"|format(f.examination) }}</td>
            <td>₹ {{ "%.2f"|format(f.tuition) }}</td>
            <td>₹ {{ "%.2f"|format(f.admission + f.annual + f.examination + 12*f.tuition) }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

<script>
  function updateTotal(){
    let admission = parseFloat(document.querySelector('input[name="admission"]').value) || 0;
    let annual = parseFloat(document.querySelector('input[name="annual"]').value) || 0;
    let exam = parseFloat(document.querySelector('input[name="examination"]').value) || 0;
    let tuition = parseFloat(document.querySelector('input[name="tuition"]').value) || 0;
    let total = admission + annual + exam + (12 * tuition);
    document.getElementById("total").innerText = "₹ " + total.toFixed(2);
  }

  function confirmDelete(){
    const cls = document.querySelector('input[name="class"]').value;
    if(confirm(`Delete class "${cls}"?`)){
      const form = document.createElement('form');
      form.method = 'post';
      form.action = "{{ url_for('feestru_bp.delete_class') }}";
      const inp = document.createElement('input');
      inp.type = 'hidden'; inp.name = 'class'; inp.value = cls;
      form.appendChild(inp);
      document.body.appendChild(form);
      form.submit();
    }
  }
</script>
</body>
</html>
"""
# ------------------ Routes ------------------


@feestru_bp.route("/", methods=["GET"])
def index():
    data = load_data()
    classes = sorted(list(data.keys()))
    selected_class = request.args.get("class") or (
        classes[0] if classes else "Class 1")
    if selected_class not in data and classes:
        selected_class = classes[0]
    fees = data.get(selected_class, {
                    "admission": 0, "annual": 0, "examination": 0, "tuition": 0})
    total = fees["admission"] + fees["annual"] + \
        fees["examination"] + 12 * fees["tuition"]
    fees_obj = type("F", (), fees)
    all_obj = {k: type("F", (), v) for k, v in data.items()}
    return render_template_string(TEMPLATE,
                                  classes=classes,
                                  selected_class=selected_class,
                                  fees=fees_obj,
                                  total=total,
                                  all_data=all_obj)


@feestru_bp.route("/add", methods=["GET"])
def add_class():
    data = load_data()
    new_cls = (request.args.get("new_class") or "").strip()
    if not new_cls:
        flash("Please enter a class name.", "error")
        return redirect(url_for("feestru_bp.index"))
    if new_cls in data:
        flash(f'"{new_cls}" already exists.', "error")
        return redirect(url_for("feestru_bp.index", **{"class": new_cls}))
    data[new_cls] = {"admission": 0, "annual": 0,
                     "examination": 0, "tuition": 0}
    save_data(data)
    flash(f'Class "{new_cls}" added.', "ok")
    return redirect(url_for("feestru_bp.index", **{"class": new_cls}))


@feestru_bp.route("/save", methods=["POST"])
def save():
    data = load_data()
    cls = (request.form.get("class") or "").strip()
    try:
        admission = float(request.form.get("admission", 0))
        annual = float(request.form.get("annual", 0))
        examination = float(request.form.get("examination", 0))
        tuition = float(request.form.get("tuition", 0))
    except ValueError:
        flash("Invalid number input.", "error")
        return redirect(url_for("feestru_bp.index", **{"class": cls or ""}))
    if not cls:
        flash("Class is missing.", "error")
        return redirect(url_for("feestru_bp.index"))
    data[cls] = {
        "admission": max(0.0, admission),
        "annual": max(0.0, annual),
        "examination": max(0.0, examination),
        "tuition": max(0.0, tuition),
    }
    save_data(data)
    flash(f'Fees saved for "{cls}".', "ok")
    return redirect(url_for("feestru_bp.index", **{"class": cls}))


@feestru_bp.route("/delete", methods=["POST"])
def delete_class():
    data = load_data()
    cls = (request.form.get("class") or "").strip()
    if not cls or cls not in data:
        flash("Class not found.", "error")
        return redirect(url_for("feestru_bp.index"))
    del data[cls]
    save_data(data)
    flash(f'Class "{cls}" deleted.', "ok")
    return redirect(url_for("feestru_bp.index"))


# ------------------ Register Blueprint ------------------
app.register_blueprint(feestru_bp, url_prefix="/feestru")

if __name__ == "__main__":
    app.run(debug=True)
