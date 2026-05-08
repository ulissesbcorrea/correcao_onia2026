from datetime import datetime, timezone
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.review import review_bp
from app.auth.decorators import evaluator_required
from app.extensions import db
from app.models import Student, Review, FraudFlag, Answer, Justification, ApprovalCounter
from app.utils.pagination import paginate_query


@review_bp.route("/queue", methods=["GET"])
@evaluator_required
def review_queue():
    user_id = int(get_jwt_identity())

    query = Review.query.filter_by(evaluator_id=user_id).join(Student).order_by(
        Student.is_flagged.desc(), Student.name.asc()
    )

    status = request.args.get("status")
    if status:
        query = query.filter(Review.decision == status)

    flagged = request.args.get("flagged")
    if flagged is not None:
        query = query.filter(Student.is_flagged == (flagged.lower() == "true"))

    search = request.args.get("search")
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    result = paginate_query(query)

    items = []
    for review in result["items"]:
        r = review.to_dict()
        s = review.student
        r["student_name"] = s.name if s else None
        r["school_name"] = s.school.name if s and s.school else None
        r["score"] = s.score if s else None
        r["is_flagged"] = s.is_flagged if s else False
        r["flag_level"] = s.flag_level if s else None
        r["student_status"] = s.status if s else None
        items.append(r)

    result["items"] = items
    return jsonify(result)


@review_bp.route("/submissions/<int:student_id>", methods=["GET"])
@evaluator_required
def submission_detail(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    fraud_flags = FraudFlag.query.filter_by(student_id=student.id).all()
    answers = Answer.query.filter_by(student_id=student.id).order_by(Answer.question_number).all()
    justifications = Justification.query.filter_by(student_id=student.id).all()

    data = student.to_dict()
    data["answers"] = [a.to_dict() for a in answers]
    data["justifications"] = [j.to_dict() for j in justifications]
    data["fraud_flags"] = [f.to_dict() for f in fraud_flags]

    review = Review.query.filter_by(
        student_id=student.id, evaluator_id=int(get_jwt_identity())
    ).first()
    data["review"] = review.to_dict() if review else None

    return jsonify({"submission": data})


@review_bp.route("/submissions/<int:student_id>/approve", methods=["POST"])
@evaluator_required
def approve(student_id):
    return _make_decision(student_id, "approved")


@review_bp.route("/submissions/<int:student_id>/reject", methods=["POST"])
@evaluator_required
def reject(student_id):
    return _make_decision(student_id, "rejected")


def _make_decision(student_id, decision):
    user_id = int(get_jwt_identity())
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json() or {}
    notes = data.get("notes", "")

    review = Review.query.filter_by(student_id=student_id, evaluator_id=user_id).first()
    if not review:
        return jsonify({"error": "Student not assigned to you"}), 403

    if review.decision != "pending":
        return jsonify({"error": f"Already reviewed: {review.decision}"}), 409

    now = datetime.now(timezone.utc)
    review.decision = decision
    review.notes = notes
    review.reviewed_at = now

    student.status = decision

    if decision == "approved":
        counter = db.session.get(ApprovalCounter, 1)
        if counter:
            counter.count = (counter.count or 0) + 1
            if counter.count >= counter.goal:
                counter.alert_triggered = True

    db.session.commit()

    counter = db.session.get(ApprovalCounter, 1)
    return jsonify({
        "message": f"Student {decision}",
        "review": review.to_dict(),
        "approval_count": counter.to_dict() if counter else None,
    })
