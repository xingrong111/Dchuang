from flask import request
from app.api.v1 import api_bp
from app.api.v1.admin import _admin_user_or_error
from app.extensions import db
from app.models.shop import Order, Product
from app.models.admin_log import AdminLog
from app.utils.response import APIResponse
from app.utils.exceptions import ValidationError, ResourceNotFoundError
import json


def _audit(admin, action, target, detail):
    db.session.add(AdminLog(admin_user_id=admin.id, action=action, target_type='commerce',
                            target_id=str(target), detail=json.dumps(detail, ensure_ascii=False)))


@api_bp.get('/admin/orders')
def admin_orders():
    _admin_user_or_error()
    page = max(1, request.args.get('page', 1, type=int))
    size = max(1, min(100, request.args.get('per_page', 20, type=int)))
    result = Order.query.order_by(Order.created_at.desc()).paginate(page=page, per_page=size, error_out=False)
    return APIResponse.paginated([o.to_dict() for o in result.items], result.total, page, size)


@api_bp.put('/admin/orders/<order_id>')
def update_order(order_id):
    admin = _admin_user_or_error()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('请求格式错误')
    order = db.session.get(Order, order_id)
    if not order:
        raise ResourceNotFoundError('订单不存在')
    transitions = {'待确认': '待发货', '待发货': '已发货', '已发货': '已完成'}
    target = data.get('status')
    previous = order.status
    if transitions.get(previous) != target:
        raise ValidationError('订单状态转换非法')
    changed = Order.query.filter_by(id=order.id, status=previous).update({Order.status: target}, synchronize_session=False)
    if not changed:
        db.session.rollback()
        raise ValidationError('订单已由其他操作更新，请刷新')
    if target == '已发货':
        carrier = data.get('carrier', '').strip() if isinstance(data.get('carrier', ''), str) else ''
        tracking = data.get('tracking_number', '').strip() if isinstance(data.get('tracking_number', ''), str) else ''
        if not carrier or len(carrier) > 80 or not tracking or len(tracking) > 100:
            db.session.rollback()
            raise ValidationError('发货需要有效物流公司与运单号')
        order.carrier = carrier
        order.tracking_number = tracking
    _audit(admin, 'order_status', order.id, {'from': previous, 'to': target})
    db.session.commit()
    db.session.refresh(order)
    return APIResponse.success(order.to_dict())


@api_bp.get('/admin/products')
def admin_products():
    _admin_user_or_error()
    return APIResponse.success([{**p.to_dict(), 'active': p.active, 'price_cents': p.price_cents}
                                for p in Product.query.order_by(Product.id).all()])


@api_bp.post('/admin/products')
@api_bp.put('/admin/products/<int:product_id>')
def save_product(product_id=None):
    admin = _admin_user_or_error()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('请求格式错误')
    product = db.session.get(Product, product_id) if product_id else Product()
    if product_id and not product:
        raise ResourceNotFoundError('商品不存在')
    for name, limit in [('name', 120), ('description', 5000), ('category', 30), ('image', 500)]:
        if name in data:
            value = data[name]
            if not isinstance(value, str) or len(value) > limit:
                raise ValidationError(f'{name} 格式或长度错误')
            if name == 'image' and value and not value.startswith(('/api/static/uploads/', 'https://')):
                raise ValidationError('图片地址必须为本站上传或 https')
            setattr(product, name, value.strip())
    for name in ['price_cents', 'stock']:
        if name in data:
            if type(data[name]) is not int or not 0 <= data[name] <= 100000000:
                raise ValidationError(f'{name} 必须为非负整数')
            setattr(product, name, data[name])
    if not product.name or not product.category or product.price_cents is None or product.stock is None:
        raise ValidationError('商品名称、分类、价格和库存不能为空')
    if 'active' in data:
        if type(data['active']) is not bool:
            raise ValidationError('active 必须为布尔值')
        product.active = data['active']
    if product.active is None:
        product.active = False
    db.session.add(product)
    db.session.flush()
    _audit(admin, 'product_save', product.id, {'name': product.name, 'active': product.active})
    db.session.commit()
    return APIResponse.success({**product.to_dict(), 'active': product.active})
