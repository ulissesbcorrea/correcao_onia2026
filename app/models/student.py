from app.extensions import db
from datetime import datetime, timezone


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    xlsx_id = db.Column(db.String(64), index=True)
    name = db.Column(db.String(255), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=False)
    score = db.Column(db.Integer)
    status = db.Column(db.String(32), default="pending", index=True)
    is_flagged = db.Column(db.Boolean, default=False, index=True)
    flag_level = db.Column(db.String(8))
    xlsx_status = db.Column(db.String(64))
    xlsx_avaliador = db.Column(db.String(255))
    xlsx_situacao = db.Column(db.String(64))
    raw_xlsx_row = db.Column(db.Integer)
    import_batch_id = db.Column(db.Integer, db.ForeignKey("import_logs.id"))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    school = db.relationship("School", back_populates="students")
    answers = db.relationship("Answer", back_populates="student", cascade="all, delete-orphan")
    justifications = db.relationship("Justification", back_populates="student", cascade="all, delete-orphan")
    fraud_flags = db.relationship(
        "FraudFlag",
        back_populates="student",
        foreign_keys="FraudFlag.student_id",
        cascade="all, delete-orphan",
    )
    reviews = db.relationship("Review", back_populates="student", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "xlsx_id": self.xlsx_id,
            "name": self.name,
            "school_name": self.school.name if self.school else None,
            "school_city": self.school.city if self.school else None,
            "school_state": self.school.state if self.school else None,
            "score": self.score,
            "status": self.status,
            "is_flagged": self.is_flagged,
            "flag_level": self.flag_level,
            "xlsx_status": self.xlsx_status,
            "xlsx_avaliador": self.xlsx_avaliador,
            "raw_xlsx_row": self.raw_xlsx_row,
        }
