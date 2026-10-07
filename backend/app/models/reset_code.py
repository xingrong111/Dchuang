from app.extensions import db


class PasswordResetCode(db.Model):
    __tablename__ = 'password_reset_codes'
    email = db.Column(db.String(120), primary_key=True)
    digest = db.Column(db.String(64), nullable=False)
    nonce = db.Column(db.String(32), nullable=False)
    expires = db.Column(db.Double, nullable=False)
    sent_at = db.Column(db.Double, nullable=False)
    attempts = db.Column(db.Integer, nullable=False, default=0)
