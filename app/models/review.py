from app.extensions import db
from datetime import datetime, timezone


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey("evaluators.id"), nullable=False)
    decision = db.Column(db.String(16), default="pending", index=True)
    notes = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student = db.relationship("Student", back_populates="reviews")
    evaluator = db.relationship("Evaluator", back_populates="reviews")

    __table_args__ = (
        db.UniqueConstraint("student_id", "evaluator_id", name="uq_review_student_evaluator"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "evaluator_id": self.evaluator_id,
            "evaluator_name": self.evaluator.name if self.evaluator else None,
            "decision": self.decision,
            "notes": self.notes,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }
