from flask import request
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, or_
from app.api.v1 import api_bp
from app.extensions import db
from app.models.shop import Product, CartItem, Order
from app.api.v1.user import _get_authenticated_user_or_401
from app.utils.response import APIResponse
from app.utils.exceptions import ValidationError, ResourceNotFoundError


def _body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('请求必须为 JSON 对象')
    return data


def _quantity(value):
    if type(value) is not int or not 1 <= value <= 99:
        raise ValidationError('数量必须为 1 至 99 的整数')
    return value


@api_bp.get('/shop/products')
def products():
    page = max(1, request.args.get('page', 1, type=int))
    size = max(1, min(100, request.args.get('per_page', 24, type=int)))
    query = Product.query.filter_by(active=True)
    if request.args.get('category'):
        query = query.filter_by(category=request.args['category'])
    keyword = request.args.get('q', '').strip()[:120]
    if keyword:
        query = query.filter(or_(Product.name.contains(keyword, autoescape=True), Product.description.contains(keyword, autoescape=True)))
    for key, operator in [('min_price', '__ge__'), ('max_price', '__le__')]:
        raw = request.args.get(key)
        if raw is not None:
            try:
                cents = int(raw)
            except (ValueError, TypeError):
                raise ValidationError('价格筛选必须使用整数分')
            if cents < 0:
                raise ValidationError('价格不能为负数')
            query = query.filter(getattr(Product.price_cents, operator)(cents))
    if request.args.get('in_stock') == 'true':
        query = query.filter(Product.stock > 0)
    sort = request.args.get('sort', 'newest')
    ordering = {'newest': Product.id.desc(), 'price_asc': Product.price_cents.asc(), 'price_desc': Product.price_cents.desc()}
    if sort not in ordering:
        raise ValidationError('排序方式不支持')
    result = query.order_by(ordering[sort], Product.id.desc()).paginate(page=page, per_page=size, error_out=False)
    return APIResponse.paginated(_products_with_reviews(result.items), result.total, page, size)


def _products_with_reviews(items):
    from app.models.commerce import ProductReview
    ids = [item.id for item in items]
    stats = {pid: (count, rating) for pid, count, rating in db.session.query(ProductReview.product_id,
              func.count(ProductReview.id), func.avg(ProductReview.rating)).filter(ProductReview.product_id.in_(ids))
              .group_by(ProductReview.product_id).all()} if ids else {}
    return [{**item.to_dict(), 'reviewCount': stats.get(item.id, (0, None))[0],
             'rating': round(float(stats[item.id][1]), 1) if item.id in stats else None} for item in items]


@api_bp.get('/shop/products/<int:product_id>')
def product_detail(product_id):
    product = db.session.get(Product, product_id)
    if not product or not product.active:
        raise ResourceNotFoundError('商品不存在或已下架')
    return APIResponse.success(_products_with_reviews([product])[0])


@api_bp.get('/shop/cart')
def cart():
    user = _get_authenticated_user_or_401()
    return APIResponse.success([{**r.product.to_dict(), 'quantity': r.quantity}
                                for r in CartItem.query.filter_by(user_id=user.id).all()])


@api_bp.post('/shop/cart')
def add_cart():
    user = _get_authenticated_user_or_401()
    data = _body()
    if type(data.get('product_id')) is not int:
        raise ValidationError('商品编号必须为整数')
    product = db.session.get(Product, data['product_id'])
    if not product or not product.active:
        raise ResourceNotFoundError('商品不存在或已下架')
    quantity = _quantity(data.get('quantity', 1))
    if (product.specs or {}).get('display_only'):
        raise ValidationError('设计展示尚未实物销售，不能加入购物车')
    row = CartItem.query.filter_by(user_id=user.id, product_id=product.id).first()
    count = (row.quantity if row else 0) + quantity
    if count > min(99, product.stock):
        raise ValidationError('商品库存不足或超出数量上限')
    if not row:
        row = CartItem(user_id=user.id, product_id=product.id, quantity=count)
        db.session.add(row)
    else:
        row.quantity = count
    db.session.commit()
    return APIResponse.success({'product_id': product.id, 'quantity': count})


@api_bp.delete('/shop/cart/<int:product_id>')
def remove_cart(product_id):
    user = _get_authenticated_user_or_401()
    CartItem.query.filter_by(user_id=user.id, product_id=product_id).delete()
    db.session.commit()
    return APIResponse.success()


@api_bp.put('/shop/cart/<int:product_id>')
def update_cart(product_id):
    user = _get_authenticated_user_or_401()
    quantity = _quantity(_body().get('quantity'))
    row = CartItem.query.filter_by(user_id=user.id, product_id=product_id).first()
    if not row:
        raise ResourceNotFoundError('购物车商品不存在')
    if not row.product.active or quantity > row.product.stock:
        raise ValidationError('商品已下架或库存不足')
    row.quantity = quantity
    db.session.commit()
    return APIResponse.success({'product_id': product_id, 'quantity': quantity})


@api_bp.post('/shop/orders')
def create_order():
    user = _get_authenticated_user_or_401()
    data = _body()
    key = data.get('request_key')
    if not isinstance(key, str) or not 8 <= len(key) <= 64:
        raise ValidationError('请提供订单幂等 request_key')
    old = Order.query.filter_by(user_id=user.id, request_key=key).first()
    if old:
        return APIResponse.success(old.to_dict())
    fields = {}
    for name, limit in [('receiver', 80), ('phone', 30), ('address', 500), ('note', 500)]:
        value = data.get(name, '')
        if not isinstance(value, str) or len(value.strip()) > limit or (name != 'note' and not value.strip()):
            raise ValidationError(f'{name} 不能为空且需符合长度要求')
        fields[name] = value.strip()
    raw = data.get('items')
    if not isinstance(raw, list) or not 1 <= len(raw) <= 50:
        raise ValidationError('请提交 1 至 50 件商品')
    quantities = {}
    for item in raw:
        if not isinstance(item, dict) or type(item.get('product_id')) is not int:
            raise ValidationError('商品格式错误')
        pid = item['product_id']
        quantities[pid] = _quantity(quantities.get(pid, 0) + _quantity(item.get('quantity')))
    snapshots, total = [], 0
    try:
        # 固定顺序扣库存，避免并发超卖；整个订单在同一事务中提交。
        for pid, quantity in sorted(quantities.items()):
            product = db.session.get(Product, pid)
            if not product or not product.active:
                raise ValidationError('商品不存在或已下架')
            if (product.specs or {}).get('display_only'):
                raise ValidationError('设计展示尚未实物销售，不能提交订单')
            changed = (Product.query.filter(Product.id == pid, Product.active.is_(True),
                                           Product.stock >= quantity)
                       .update({Product.stock: Product.stock - quantity}, synchronize_session=False))
            if changed != 1:
                raise ValidationError(f'{product.name} 库存不足')
            snapshots.append({'product_id': pid, 'name': product.name, 'quantity': quantity,
                              'price': product.price_cents / 100, 'price_cents': product.price_cents})
            total += product.price_cents * quantity
        order = Order(user_id=user.id, request_key=key, items=snapshots, total_cents=total, **fields)
        db.session.add(order)
        CartItem.query.filter_by(user_id=user.id).filter(CartItem.product_id.in_(quantities)).delete(synchronize_session=False)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        old = Order.query.filter_by(user_id=user.id, request_key=key).first()
        if old:
            return APIResponse.success(old.to_dict())
        raise ValidationError('订单提交冲突，请重试')
    except Exception:
        db.session.rollback()
        raise
    return APIResponse.success(order.to_dict(), message='订单已记录，等待商家确认')


@api_bp.get('/shop/orders')
def orders():
    user = _get_authenticated_user_or_401()
    page = max(1, request.args.get('page', 1, type=int))
    size = max(1, min(50, request.args.get('per_page', 12, type=int)))
    query = Order.query.filter_by(user_id=user.id)
    if request.args.get('status'):
        query = query.filter_by(status=request.args['status'])
    result = query.order_by(Order.created_at.desc(), Order.id.desc()).paginate(page=page, per_page=size, error_out=False)
    return APIResponse.paginated([o.to_dict() for o in result.items], result.total, page, size)


@api_bp.post('/shop/orders/<order_id>/cancel')
def cancel_order(order_id):
    user = _get_authenticated_user_or_401()
    order = Order.query.filter_by(id=order_id, user_id=user.id).first()
    if not order:
        raise ResourceNotFoundError('订单不存在')
    changed = Order.query.filter_by(id=order.id, status='待确认').update({Order.status: '已取消'}, synchronize_session=False)
    if not changed:
        raise ValidationError('仅待确认订单可取消')
    for item in order.items:
        Product.query.filter_by(id=item['product_id']).update({Product.stock: Product.stock + item['quantity']}, synchronize_session=False)
    db.session.commit()
    db.session.refresh(order)
    return APIResponse.success(order.to_dict())
