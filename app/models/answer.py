from app.extensions import db


class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    question_number = db.Column(db.Integer, nullable=False)
    selected_option = db.Column(db.String(1))

    student = db.relationship("Student", back_populates="answers")

    __table_args__ = (
        db.UniqueConstraint("student_id", "question_number", name="uq_answer_student_question"),
        db.Index("idx_answers_option_lookup", "question_number", "selected_option"),
    )

    def to_dict(self):
        return {
            "question_number": self.question_number,
            "selected_option": self.selected_option,
        }
