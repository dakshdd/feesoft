from flask import Blueprint

report_card_bp = Blueprint("report_card_bp", __name__)


@report_card_bp.route("/reportcard")
def card_home():
    return "<h2>Report Card Module</h2><p>Here you can generate student report cards.</p>"
