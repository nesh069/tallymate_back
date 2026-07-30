from app.extensions import db
from app.models.user import utcnow


class FriendContact(db.Model):
    """A directional friend request from ``user`` to ``friend``."""
    __tablename__ = "friend_contacts"
    __table_args__ = (
        db.UniqueConstraint("user_id", "friend_id", name="uq_friend_contact_direction"),
        db.CheckConstraint("status IN ('pending', 'accepted')", name="ck_friend_status"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    friend_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    user = db.relationship("User", foreign_keys=[user_id], back_populates="sent_friend_requests")
    friend = db.relationship("User", foreign_keys=[friend_id], back_populates="received_friend_requests")
