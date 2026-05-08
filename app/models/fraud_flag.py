from app.extensions import db
from datetime import datetime, timezone


class FraudFlag(db.Model):
    __tablename__ = "fraud_flags"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    source = db.Column(db.String(16), default="manual")
    level = db.Column(db.String(16), default="medium")
    reason = db.Column(db.Text)
    algorithm_name = db.Column(db.String(128))
    related_student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    student = db.relationship("Student", back_populates="fraud_flags", foreign_keys=[student_id])
    related_student = db.relationship("Student", foreign_keys=[related_student_id])

    def to_dict(self):
        school_name = None
        if self.student and self.student.school:
            school_name = self.student.school.name
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.name if self.student else None,
            "school_name": school_name,
            "source": self.source,
            "level": self.level,
            "reason": self.reason,
            "algorithm_name": self.algorithm_name,
            "related_student_id": self.related_student_id,
            "related_student_name": self.related_student.name if self.related_student else None,
            "resolved": self.resolved,
        }
