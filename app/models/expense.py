from datetime import datetime, timezone

from app.extensions import db

SPLIT_TYPES = ("equal", "unequal", "percentage")


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    split_type = db.Column(db.String(20), nullable=False, default="equal")
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    group = db.relationship("Group", backref=db.backref("expenses", cascade="all, delete-orphan"))
    payer = db.relationship("User", foreign_keys=[paid_by])
    shares = db.relationship(
        "ExpenseShare", backref="expense", cascade="all, delete-orphan", lazy="joined"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "group_id": self.group_id,
            "paid_by": self.paid_by,
            "amount": str(self.amount),
            "description": self.description,
            "split_type": self.split_type,
            "date": self.date.isoformat(),
            "shares": [share.to_dict() for share in self.shares],
        }


class ExpenseShare(db.Model):
    __tablename__ = "expense_shares"

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey("expenses.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    percentage = db.Column(db.Numeric(5, 2), nullable=True)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "amount": str(self.amount),
            "percentage": str(self.percentage) if self.percentage is not None else None,
        }
