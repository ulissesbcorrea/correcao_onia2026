from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.fraud import fraud_bp
from app.fraud.algorithms import run_all_fraud_detection
from app.auth.decorators import admin_required
from app.extensions import db
from app.models import FraudFlag, Student, School
from app.utils.pagination import paginate_query


@fraud_bp.route("/alerts", methods=["GET"])
@jwt_required()
def list_alerts():
    query = FraudFlag.query.join(Student)

    level = request.args.get("level")
    if level:
        query = query.filter(FraudFlag.level == level)

    search = request.args.get("search")
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    school = request.args.get("school")
    if school:
        query = query.join(School).filter(School.name.ilike(f"%{school}%"))

    resolved = request.args.get("resolved")
    if resolved is not None:
        query = query.filter(FraudFlag.resolved == (resolved.lower() == "true"))

    query = query.order_by(FraudFlag.created_at.desc())

    result = paginate_query(query)
    result["items"] = [f.to_dict() for f in result["items"]]
    return jsonify(result)


@fraud_bp.route("/alerts/<int:alert_id>", methods=["GET"])
@jwt_required()
def alert_detail(alert_id):
    flag = db.session.get(FraudFlag, alert_id)
    if not flag:
        return jsonify({"error": "Alert not found"}), 404

    data = flag.to_dict()
    data["student"] = flag.student.to_dict() if flag.student else None
    if flag.related_student:
        data["related_student"] = flag.related_student.to_dict()
        data["related_answers"] = [a.to_dict() for a in flag.related_student.answers]
    data["answers"] = [a.to_dict() for a in flag.student.answers] if flag.student else []

    return jsonify({"alert": data})


@fraud_bp.route("/detect", methods=["POST"])
@admin_required
def trigger_detection():
    data = request.get_json() or {}
    batch_id = data.get("batch_id")
    if not batch_id:
        return jsonify({"error": "batch_id required"}), 400

    results = run_all_fraud_detection(batch_id)
    return jsonify({"message": "Fraud detection completed", "results": results})


@fraud_bp.route("/stats", methods=["GET"])
@jwt_required()
def fraud_stats():
    total_flags = FraudFlag.query.count()
    by_level = db.session.query(FraudFlag.level, db.func.count(FraudFlag.id)).group_by(FraudFlag.level).all()
    by_source = db.session.query(FraudFlag.source, db.func.count(FraudFlag.id)).group_by(FraudFlag.source).all()
    unresolved = FraudFlag.query.filter_by(resolved=False).count()

    return jsonify({
        "total_flags": total_flags,
        "unresolved": unresolved,
        "by_level": {level: count for level, count in by_level},
        "by_source": {source: count for source, count in by_source},
    })
