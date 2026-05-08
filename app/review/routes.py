import os
from datetime import datetime, timezone
from flask import request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.review import review_bp
from app.auth.decorators import evaluator_required
from app.extensions import db
from app.models import Student, Review, FraudFlag, Answer, Justification, ApprovalCounter, Evaluator
from app.utils.pagination import paginate_query
from app.upload.image_service import find_student_images, GABARITOS_DIR


@review_bp.route("/queue", methods=["GET"])
@evaluator_required
def review_queue():
    user_id = int(get_jwt_identity())
    user = db.session.get(Evaluator, user_id)

    if user and user.role == "admin":
        # Admin sees all students, grouped by polo, sorted by score desc then name asc
        query = Student.query.join(School).order_by(
            School.polo.asc(),
            Student.score.desc().nullslast(),
            Student.name.asc()
        )

        status = request.args.get("status")
        if status:
            query = query.filter(Student.status == status)

        flagged = request.args.get("flagged")
        if flagged is not None:
            query = query.filter(Student.is_flagged == (flagged.lower() == "true"))

        search = request.args.get("search")
        if search:
            query = query.filter(Student.name.ilike(f"%{search}%"))

        polo = request.args.get("polo")
        if polo:
            query = query.filter(School.polo.ilike(f"%{polo}%"))

        result = paginate_query(query)
        items = []
        for s in result["items"]:
            items.append({
                "student_id": s.id,
                "student_name": s.name,
                "school_name": s.school.name if s.school else None,
                "polo": s.school.polo if s.school else None,
                "score": s.score,
                "is_flagged": s.is_flagged,
                "flag_level": s.flag_level,
                "student_status": s.status,
                "decision": s.status,
            })
        result["items"] = items
        return jsonify(result)

    # Regular evaluator: only assigned students
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


@review_bp.route("/images/<path:img_path>")
@evaluator_required
def serve_image(img_path):
    """Serve justification images from gabaritos folder."""
    full_path = os.path.join(GABARITOS_DIR, img_path)
    if not os.path.isfile(full_path):
        return jsonify({"error": "Image not found"}), 404
    return send_file(full_path)


@review_bp.route("/submissions/<int:student_id>/images")
@evaluator_required
def student_images(student_id):
    """Get all justification images for a student."""
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404
    images = find_student_images(student.xlsx_id, student.name)
    result = []
    for img in images:
        rel = os.path.relpath(img["path"], GABARITOS_DIR)
        result.append({
            "name": img["name"],
            "polo": img["polo"],
            "url": f"/api/review/images/{rel}",
        })
    return jsonify({"images": result, "student_name": student.name})


@review_bp.route("/compare/<int:student1_id>/<int:student2_id>")
@evaluator_required
def compare_students(student1_id, student2_id):
    """Get side-by-side data for two students (fraud comparison)."""
    s1 = db.session.get(Student, student1_id)
    s2 = db.session.get(Student, student2_id)
    if not s1 or not s2:
        return jsonify({"error": "Student not found"}), 404

    def student_data(s):
        images = find_student_images(s.xlsx_id, s.name)
        imgs = []
        for img in images:
            rel = os.path.relpath(img["path"], GABARITOS_DIR)
            imgs.append({"name": img["name"], "url": f"/api/review/images/{rel}"})
        answers = [a.to_dict() for a in Answer.query.filter_by(student_id=s.id).order_by(Answer.question_number).all()]
        return {
            "id": s.id, "name": s.name, "score": s.score,
            "school": s.school.name if s.school else None,
            "images": imgs, "answers": answers,
        }

    return jsonify({"student1": student_data(s1), "student2": student_data(s2)})


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
    user = db.session.get(Evaluator, user_id)
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    data = request.get_json() or {}
    notes = data.get("notes", "")

    review = Review.query.filter_by(student_id=student_id, evaluator_id=user_id).first()
    if not review:
        # Admin can review without prior assignment
        if user and user.role == "admin":
            review = Review(student_id=student_id, evaluator_id=user_id, decision="pending")
            db.session.add(review)
            db.session.flush()
        else:
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


@review_bp.route("/fraud-clusters")
@evaluator_required
def fraud_clusters():
    """Return fraud clusters: same-school student pairs with similar answers."""
    import os as _os
    from app.fraud.ocr import extract_text
    from rapidfuzz import fuzz

    flags = FraudFlag.query.filter(
        FraudFlag.related_student_id.isnot(None),
        FraudFlag.resolved == False,
    ).order_by(FraudFlag.level.desc()).all()

    clusters = {}
    seen_pairs = set()

    for flag in flags:
        s1_id = flag.student_id
        s2_id = flag.related_student_id
        pair_key = tuple(sorted([s1_id, s2_id]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        s1 = db.session.get(Student, s1_id)
        s2 = db.session.get(Student, s2_id)
        if not s1 or not s2:
            continue

        school_name = s1.school.name if s1.school else "Desconhecida"
        if school_name not in clusters:
            clusters[school_name] = []

        imgs1 = find_student_images(s1.xlsx_id, s1.name)
        imgs2 = find_student_images(s2.xlsx_id, s2.name)

        text1 = extract_text(imgs1[0]["path"]) if imgs1 else ""
        text2 = extract_text(imgs2[0]["path"]) if imgs2 else ""

        similarity = 0
        if text1 and text2 and len(text1) > 10 and len(text2) > 10:
            similarity = fuzz.ratio(text1, text2)

        def fmt(s, imgs, txt):
            return {
                "id": s.id, "name": s.name, "score": s.score, "status": s.status,
                "images": [{"name": i["name"], "url": f"/api/review/images/{_os.path.relpath(i['path'], GABARITOS_DIR)}"} for i in imgs],
                "ocr_text": txt[:500] if txt else "",
                "answers": [a.to_dict() for a in Answer.query.filter_by(student_id=s.id).order_by(Answer.question_number).all()],
            }

        clusters[school_name].append({
            "student1": fmt(s1, imgs1, text1),
            "student2": fmt(s2, imgs2, text2),
            "similarity": round(similarity, 1),
            "flag_level": flag.level,
            "flag_reason": flag.reason,
        })

    return jsonify({"clusters": clusters, "total_pairs": len(seen_pairs)})


@review_bp.route("/ai-compare/<int:student1_id>/<int:student2_id>")
@evaluator_required
def ai_compare(student1_id, student2_id):
    """Deep AI comparison of two students' justifications using NVIDIA vision model."""
    from app.fraud.ocr import compare_justifications

    s1 = db.session.get(Student, student1_id)
    s2 = db.session.get(Student, student2_id)
    if not s1 or not s2:
        return jsonify({"error": "Student not found"}), 404

    imgs1 = find_student_images(s1.xlsx_id, s1.name)
    imgs2 = find_student_images(s2.xlsx_id, s2.name)

    if not imgs1 or not imgs2:
        return jsonify({"error": "Images not found for one or both students"}), 404

    result = compare_justifications(imgs1[0]["path"], imgs2[0]["path"])

    return jsonify({
        "student1": {"id": s1.id, "name": s1.name},
        "student2": {"id": s2.id, "name": s2.name},
        "comparison": result,
    })
