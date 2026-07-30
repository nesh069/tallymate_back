# Minimal placeholder pending the full Accounts & Friends feature (Member 1).
# Only the fields needed for other features (e.g. Expenses) to hold FKs are defined here.
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User {self.id} {self.email}>"
