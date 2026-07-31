from datetime import datetime
from app.extensions import db

class Settlement(db.Model):
    __tablename__ = "settlements"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    payer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    payee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payer = db.relationship("User", foreign_keys=[payer_id])
    payee = db.relationship("User", foreign_keys=[payee_id])

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "payer_id": self.payer_id,
            "payee_id": self.payee_id,
            "amount": self.amount,
            "created_at": self.created_at.isoformat(),
        }