from app.extensions import db
from datetime import datetime, timezone


class ImportLog(db.Model):
    __tablename__ = "import_logs"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    rows_total = db.Column(db.Integer, default=0)
    rows_imported = db.Column(db.Integer, default=0)
    rows_flagged = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default="in_progress")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "rows_total": self.rows_total,
            "rows_imported": self.rows_imported,
            "rows_flagged": self.rows_flagged,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
