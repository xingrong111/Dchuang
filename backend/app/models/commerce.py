from datetime import datetime
from app.extensions import db


class Address(db.Model):
    __tablename__ = 'shipping_addresses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    receiver = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    is_default = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {key: getattr(self, key) for key in ['id', 'receiver', 'phone', 'address', 'is_default']}


class ProductFavorite(db.Model):
    __tablename__ = 'product_favorites'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ProductReview(db.Model):
    __tablename__ = 'product_reviews'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, index=True)
    order_id = db.Column(db.String(64), db.ForeignKey('orders.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('order_id', 'product_id'),)
    author = db.relationship('User')

    def to_dict(self):
        return {'id': self.id, 'product_id': self.product_id, 'rating': self.rating,
                'content': self.content, 'author': self.author.username,
                'time': self.created_at.isoformat()}
