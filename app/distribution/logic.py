"""Round-robin student distribution among evaluators."""

from app.extensions import db
from app.models import Student, Review, Evaluator


def distribute_round_robin(batch_id=None):
    """Assign unassigned students to evaluators using round-robin."""
    query = Student.query.filter(Student.status == "pending")

    if batch_id:
        query = query.filter_by(import_batch_id=batch_id)

    # Only students without any review assigned
    students_with_reviews = db.session.query(Review.student_id).distinct()
    pending_students = query.filter(~Student.id.in_(students_with_reviews)).all()

    evaluators = Evaluator.query.filter_by(role="evaluator", is_active=True).all()
    if not evaluators:
        return {"error": "No active evaluators found"}

    assigned = 0
    for i, student in enumerate(pending_students):
        evaluator = evaluators[i % len(evaluators)]
        review = Review(
            student_id=student.id,
            evaluator_id=evaluator.id,
            decision="pending",
        )
        db.session.add(review)
        assigned += 1

    db.session.commit()
    return {
        "assigned": assigned,
        "evaluators": len(evaluators),
        "per_evaluator": assigned // len(evaluators) if evaluators else 0,
    }


def redistribute(batch_id=None):
    """Reassign students whose pending reviews to balance workload."""
    # Remove unreviewed (still pending) assignments
    query = Review.query.filter_by(decision="pending")
    if batch_id:
        query = query.join(Student).filter(Student.import_batch_id == batch_id)

    removed = query.delete(synchronize_session=False)
    db.session.commit()

    # Redistribute
    result = distribute_round_robin(batch_id)
    result["removed"] = removed
    return result
