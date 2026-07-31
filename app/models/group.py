from app.extensions import db
from app.models.user import utcnow


# Association table for group members
group_members = db.Table(
    "group_members",
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("joined_at", db.DateTime(timezone=True), nullable=False, default=utcnow),
)


class Group(db.Model):
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    # Relationships
    owner = db.relationship("User", foreign_keys=[created_by], backref="owned_groups")
    members = db.relationship(
        "User",
        secondary=group_members,
        lazy="dynamic",
        backref=db.backref("groups", lazy="dynamic"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "members": [m.to_dict() for m in self.members],
        }