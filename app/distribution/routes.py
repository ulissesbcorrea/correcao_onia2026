from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.distribution import distribution_bp
from app.distribution.logic import distribute_round_robin, redistribute
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import Evaluator, Review, Student
from sqlalchemy import func


@distribution_bp.route("/status", methods=["GET"])
@admin_required
def distribution_status():
    evaluators = Evaluator.query.filter_by(is_active=True).all()
    status_list = []
    for e in evaluators:
        assigned = Review.query.filter_by(evaluator_id=e.id).count()
        pending = Review.query.filter_by(evaluator_id=e.id, decision="pending").count()
        approved = Review.query.filter_by(evaluator_id=e.id, decision="approved").count()
        rejected = Review.query.filter_by(evaluator_id=e.id, decision="rejected").count()
        status_list.append({
            "evaluator_id": e.id,
            "name": e.name,
            "email": e.email,
            "assigned": assigned,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
        })

    total_pending = Student.query.filter_by(status="pending").count()
    total_assigned = db.session.query(func.count(func.distinct(Review.student_id))).scalar() or 0
    unassigned = total_pending - db.session.query(func.count(func.distinct(Review.student_id))).filter(
        Review.student_id.in_(
            db.session.query(Student.id).filter(Student.status == "pending")
        )
    ).scalar() or 0

    return jsonify({
        "evaluators": status_list,
        "total_pending_students": total_pending,
        "total_assigned": total_assigned,
        "unassigned": max(0, unassigned),
    })


@distribution_bp.route("/assign", methods=["POST"])
@admin_required
def assign():
    data = request.get_json() or {}
    batch_id = data.get("batch_id")
    result = distribute_round_robin(batch_id)
    return jsonify({"message": "Distribution completed", "result": result})


@distribution_bp.route("/redistribute", methods=["POST"])
@admin_required
def do_redistribute():
    data = request.get_json() or {}
    batch_id = data.get("batch_id")
    result = redistribute(batch_id)
    return jsonify({"message": "Redistribution completed", "result": result})
