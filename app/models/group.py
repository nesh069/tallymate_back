# Minimal placeholder pending the full Groups feature (Member 2).
# Only the fields/relationships needed for other features (e.g. Expenses) are defined here.
from app.extensions import db

group_members = db.Table(
    "group_members",
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
)


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    members = db.relationship("User", secondary=group_members, backref="groups")

    def has_member(self, user_id):
        return any(member.id == int(user_id) for member in self.members)

    def __repr__(self):
        return f"<Group {self.id} {self.name}>"
