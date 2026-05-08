from app.extensions import db


class ApprovalCounter(db.Model):
    __tablename__ = "approval_counter"

    id = db.Column(db.Integer, primary_key=True, default=1)
    count = db.Column(db.Integer, default=0)
    goal = db.Column(db.Integer, default=200)
    alert_triggered = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "count": self.count,
            "goal": self.goal,
            "percentage": round(self.count / self.goal * 100, 1) if self.goal else 0,
            "alert": self.alert_triggered or self.count >= self.goal,
            "remaining": max(0, self.goal - self.count),
        }
