from flask import request
from sqlalchemy.exc import IntegrityError
from app.api.v1 import api_bp
from app.api.v1.user import _get_authenticated_user_or_401
from app.api.v1.shop import _body
from app.extensions import db
from app.models.commerce import Address, ProductFavorite, ProductReview
from app.models.shop import Product, Order
from app.utils.exceptions import ValidationError, ResourceNotFoundError
from app.utils.response import APIResponse


def _text(data, name, limit):
    value = data.get(name)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValidationError(f'{name} 不能为空且不能超过{limit}字')
    return value.strip()


@api_bp.get('/shop/addresses')
def addresses():
    user = _get_authenticated_user_or_401()
    return APIResponse.success([row.to_dict() for row in Address.query.filter_by(user_id=user.id)
                                .order_by(Address.is_default.desc(), Address.id.desc()).all()])


@api_bp.post('/shop/addresses')
@api_bp.put('/shop/addresses/<int:address_id>')
def save_address(address_id=None):
    user = _get_authenticated_user_or_401()
    data = _body()
    row = Address.query.filter_by(id=address_id, user_id=user.id).first() if address_id else Address(user_id=user.id)
    if row is None:
        raise ResourceNotFoundError('地址不存在')
    if not address_id and Address.query.filter_by(user_id=user.id).count() >= 20:
        raise ValidationError('最多保存20个地址')
    fields = {key: _text(data, key, limit) for key, limit in [('receiver', 80), ('phone', 30), ('address', 500)]}
    default = data.get('is_default', False)
    if type(default) is not bool:
        raise ValidationError('is_default必须为布尔值')
    if row.is_default or (not address_id and not Address.query.filter_by(user_id=user.id).first()):
        default = True
    if default:
        Address.query.filter_by(user_id=user.id).update({Address.is_default: False})
    for key, value in fields.items():
        setattr(row, key, value)
    row.is_default = default
    db.session.add(row)
    db.session.commit()
    return APIResponse.success(row.to_dict())


@api_bp.delete('/shop/addresses/<int:address_id>')
def delete_address(address_id):
    user = _get_authenticated_user_or_401()
    row = Address.query.filter_by(id=address_id, user_id=user.id).first()
    if not row:
        raise ResourceNotFoundError('地址不存在')
    was_default = row.is_default
    db.session.delete(row)
    db.session.flush()
    if was_default:
        replacement = Address.query.filter_by(user_id=user.id).order_by(Address.id.desc()).first()
        if replacement:
            replacement.is_default = True
    db.session.commit()
    return APIResponse.success()


@api_bp.get('/shop/favorites')
def product_favorites():
    user = _get_authenticated_user_or_401()
    return APIResponse.success([p.to_dict() for p in Product.query.join(ProductFavorite)
                                .filter(ProductFavorite.user_id == user.id).order_by(ProductFavorite.created_at.desc()).all()])


@api_bp.put('/shop/favorites/<int:product_id>')
def favorite_product(product_id):
    user = _get_authenticated_user_or_401()
    if not db.session.get(Product, product_id):
        raise ResourceNotFoundError('商品不存在')
    if not db.session.get(ProductFavorite, (user.id, product_id)):
        db.session.add(ProductFavorite(user_id=user.id, product_id=product_id))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if not db.session.get(ProductFavorite, (user.id, product_id)):
                raise
    return APIResponse.success({'favorited': True})


@api_bp.delete('/shop/favorites/<int:product_id>')
def unfavorite_product(product_id):
    user = _get_authenticated_user_or_401()
    ProductFavorite.query.filter_by(user_id=user.id, product_id=product_id).delete()
    db.session.commit()
    return APIResponse.success({'favorited': False})


@api_bp.get('/shop/orders/<order_id>')
def order_detail(order_id):
    user = _get_authenticated_user_or_401()
    order = Order.query.filter_by(id=order_id, user_id=user.id).first()
    if not order:
        raise ResourceNotFoundError('订单不存在')
    return APIResponse.success(order.to_dict())


@api_bp.post('/shop/orders/<order_id>/receive')
def receive_order(order_id):
    user = _get_authenticated_user_or_401()
    changed = Order.query.filter_by(id=order_id, user_id=user.id, status='已发货').update({Order.status: '已完成'})
    if not changed:
        db.session.rollback()
        raise ValidationError('仅本人已发货订单可确认收货')
    db.session.commit()
    return APIResponse.success()


@api_bp.get('/shop/products/<int:product_id>/reviews')
def product_reviews(product_id):
    page = max(1, request.args.get('page', 1, type=int))
    result = ProductReview.query.filter_by(product_id=product_id).order_by(ProductReview.created_at.desc(), ProductReview.id.desc()).paginate(page=page, per_page=10, error_out=False)
    return APIResponse.paginated([row.to_dict() for row in result.items], result.total, page, 10)


@api_bp.post('/shop/orders/<order_id>/reviews')
def add_product_review(order_id):
    user = _get_authenticated_user_or_401()
    data = _body()
    order = Order.query.filter_by(id=order_id, user_id=user.id, status='已完成').first()
    pid = data.get('product_id')
    if not order or type(pid) is not int or not any(item['product_id'] == pid for item in order.items):
        raise ValidationError('仅可评价本人已完成订单中的商品')
    rating = data.get('rating')
    if type(rating) is not int or not 1 <= rating <= 5:
        raise ValidationError('评分应为1至5的整数')
    row = ProductReview(user_id=user.id, order_id=order.id, product_id=pid,
                        rating=rating, content=_text(data, 'content', 1000))
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError('该订单商品已评价')
    return APIResponse.success(row.to_dict())
