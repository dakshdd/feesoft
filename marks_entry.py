from flask import Blueprint

marks_entry_bp = Blueprint("marks_entry_bp", __name__)


@marks_entry_bp.route("/marks")
def marks_home():
    return "<h2>Marks Entry Module</h2><p>Here you can enter student marks.</p>"
