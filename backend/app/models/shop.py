"""商品、购物车和订单；金额以分存储，订单保留服务端价格快照。"""
import uuid
from datetime import datetime
from app.extensions import db


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    category = db.Column(db.String(30), nullable=False)
    price_cents = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(500))
    specs = db.Column(db.JSON, default=dict)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'description': self.description,
                'category': self.category, 'price': self.price_cents / 100,
                'stock': self.stock, 'image': self.image, 'specs': self.specs or {},
                'reviews': [], 'sales': 0, 'reviewCount': 0, 'rating': None}


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id'),)
    product = db.relationship(Product)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    request_key = db.Column(db.String(64), nullable=False)
    items = db.Column(db.JSON, nullable=False)
    total_cents = db.Column(db.Integer, nullable=False)
    receiver = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    note = db.Column(db.String(500), default='')
    status = db.Column(db.String(30), nullable=False, default='待确认')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    carrier = db.Column(db.String(80))
    tracking_number = db.Column(db.String(100))
    __table_args__ = (db.UniqueConstraint('user_id', 'request_key'),)

    def to_dict(self):
        return {'id': self.id, 'items': self.items, 'total': self.total_cents / 100,
                'receiver': self.receiver, 'phone': self.phone, 'address': self.address,
                'note': self.note, 'status': self.status, 'created_at': self.created_at.isoformat(),
                'carrier': self.carrier, 'tracking_number': self.tracking_number}
