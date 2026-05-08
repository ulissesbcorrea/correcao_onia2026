from app.extensions import db


class School(db.Model):
    __tablename__ = "schools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    city = db.Column(db.String(128))
    state = db.Column(db.String(2))
    polo = db.Column(db.String(128))

    students = db.relationship("Student", back_populates="school")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "polo": self.polo,
            "student_count": len(self.students) if self.students else 0,
        }
