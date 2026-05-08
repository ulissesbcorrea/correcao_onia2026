import bcrypt, os, openpyxl
from flask import request, jsonify
from werkzeug.utils import secure_filename
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    jwt_required,
    get_jwt_identity,
)
from app.auth import auth_bp
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import Evaluator


UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    user = Evaluator.query.filter_by(email=data["email"].strip().lower()).first()
    if not user or not user.is_active:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.checkpw(data["password"].encode(), user.password_hash.encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    response = jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    })
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    access_token = create_access_token(identity=user_id)
    return jsonify({"access_token": access_token})


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(Evaluator, int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()})


@auth_bp.route("/evaluators", methods=["GET"])
@jwt_required()
def list_evaluators():
    evaluators = Evaluator.query.filter_by(is_active=True).all()
    return jsonify({"evaluators": [e.to_dict() for e in evaluators]})


@auth_bp.route("/evaluators", methods=["POST"])
@admin_required
def create_evaluator():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("name"):
        return jsonify({"error": "Name and email required"}), 400

    email = data["email"].strip().lower()
    if Evaluator.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    password = data.get("password", "onia2026")
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    evaluator = Evaluator(
        name=data["name"].strip(),
        email=email,
        password_hash=password_hash,
        role="evaluator",
    )
    db.session.add(evaluator)
    db.session.commit()
    return jsonify({"evaluator": evaluator.to_dict()}), 201


@auth_bp.route("/evaluators/batch", methods=["POST"])
@admin_required
def batch_create_evaluators():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".xlsx"):
        return jsonify({"error": "Only .xlsx files accepted"}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
    file.save(filepath)

    wb = openpyxl.load_workbook(filepath, data_only=True)
    ws = wb.active

    # Map columns from header
    header = {}
    for col in range(1, ws.max_column + 1):
        val = str(ws.cell(row=1, column=col).value or "").strip().lower()
        header[val] = col

    name_col = header.get("nome", 1)
    email_col = header.get("email", 2)
    password_col = header.get("senha", header.get("password", 3))

    created = []
    skipped = []
    errors = []

    for row in range(2, ws.max_row + 1):
        name = str(ws.cell(row=row, column=name_col).value or "").strip()
        email = str(ws.cell(row=row, column=email_col).value or "").strip().lower()
        password = str(ws.cell(row=row, column=password_col).value or "").strip()

        if not name or not email:
            continue

        if Evaluator.query.filter_by(email=email).first():
            skipped.append({"row": row, "email": email, "reason": "Email already exists"})
            continue

        if not password:
            password = "onia2026"

        try:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            evaluator = Evaluator(name=name, email=email, password_hash=password_hash, role="evaluator")
            db.session.add(evaluator)
            db.session.flush()
            created.append({"id": evaluator.id, "name": name, "email": email})
        except Exception as e:
            errors.append({"row": row, "email": email, "reason": str(e)})

    db.session.commit()

    return jsonify({
        "message": f"Batch completed: {len(created)} created, {len(skipped)} skipped, {len(errors)} errors",
        "created": created,
        "skipped": skipped,
        "errors": errors,
    }), 201
