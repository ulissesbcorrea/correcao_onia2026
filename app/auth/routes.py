import bcrypt
from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from app.auth import auth_bp
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import Evaluator


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

    return jsonify({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    })


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


@auth_bp.route("/evaluators/<int:evaluator_id>", methods=["DELETE"])
@admin_required
def delete_evaluator(evaluator_id):
    evaluator = db.session.get(Evaluator, evaluator_id)
    if not evaluator:
        return jsonify({"error": "Not found"}), 404
    evaluator.is_active = False
    db.session.commit()
    return jsonify({"message": "Evaluator deactivated"})
