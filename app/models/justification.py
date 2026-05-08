from app.extensions import db


class Justification(db.Model):
    __tablename__ = "justifications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    photo_url = db.Column(db.Text)
    photo_hash = db.Column(db.String(64), index=True)

    student = db.relationship("Student", back_populates="justifications")

    def to_dict(self):
        return {
            "photo_url": self.photo_url,
            "photo_hash": self.photo_hash,
        }
