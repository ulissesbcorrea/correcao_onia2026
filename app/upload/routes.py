import os
from flask import request, jsonify
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename
from app.upload import upload_bp
from app.upload.xlsx_parser import parse_xlsx
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import ImportLog, FraudFlag, Student, School
from app.fraud.algorithms import run_all_fraud_detection


UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


@upload_bp.route("/xlsx", methods=["POST"])
@admin_required
def upload_xlsx():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".xlsx"):
        return jsonify({"error": "Only .xlsx files accepted"}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    import_log = ImportLog(filename=filename, status="in_progress")
    db.session.add(import_log)
    db.session.commit()

    total, imported, flagged = parse_xlsx(filepath, import_log.id)

    # Run fraud detection algorithms after import
    try:
        fraud_results = run_all_fraud_detection(import_log.id, skip_no_justification=True)
    except Exception as e:
        fraud_results = {"error": str(e)}

    return jsonify({
        "message": "Import completed",
        "batch_id": import_log.id,
        "rows_total": total,
        "rows_imported": imported,
        "rows_flagged": flagged,
        "fraud_detection": fraud_results,
    })


@upload_bp.route("/batches", methods=["GET"])
@admin_required
def list_batches():
    batches = ImportLog.query.order_by(ImportLog.created_at.desc()).limit(20).all()
    return jsonify({"batches": [b.to_dict() for b in batches]})


@upload_bp.route("/batches/<int:batch_id>", methods=["GET"])
@admin_required
def batch_detail(batch_id):
    batch = db.session.get(ImportLog, batch_id)
    if not batch:
        return jsonify({"error": "Batch not found"}), 404
    return jsonify({"batch": batch.to_dict()})
