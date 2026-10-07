# ============================================================
# 智绘锡承 - 用户中心 API
# 位置: backend/app/api/v1/user.py
#
# 接口前缀约定: 前端 Vite 代理剥 /api，后端路由无前缀:
#   GET /user/credits   （前端 GET /api/user/credits）
# ============================================================
from flask import request

from app.api.v1 import api_bp
from app.models.credit import CreditTransaction
from app.services.credit import CreditService
from app.utils.auth import get_authenticated_user
from app.utils.exceptions import AuthenticationError
from app.utils.response import APIResponse
from app.extensions import db
from app.models.user import User
from app.models.artwork import Artwork
from app.models.collection import Collection
from app.utils.exceptions import ValidationError
from sqlalchemy.exc import IntegrityError


@api_bp.route('/user/profile', methods=['PUT'])
def update_profile():
    user = _get_authenticated_user_or_401()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError('请提交资料对象')
    limits = {'username': 50, 'bio': 500, 'location': 100, 'website': 255}
    for field, limit in limits.items():
        if field in data:
            value = data[field]
            if not isinstance(value, str) or len(value.strip()) > limit:
                raise ValidationError(f'{field} 格式或长度不正确')
            value = value.strip()
            if field == 'username' and len(value) < 2:
                raise ValidationError('用户名至少 2 个字符')
            if field == 'website' and value and not value.startswith(('https://', 'http://')):
                raise ValidationError('网站地址必须为 http 或 https')
            setattr(user, field, value)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ValidationError('用户名已被使用')
    return APIResponse.success(user.to_dict(include_sensitive=True))


@api_bp.route('/user/password', methods=['PUT'])
def update_password():
    user = _get_authenticated_user_or_401()
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        raise ValidationError('请求格式错误')
    current, new = data.get('current_password'), data.get('new_password')
    if not isinstance(current, str) or not user.check_password(current):
        raise ValidationError('当前密码不正确')
    if not isinstance(new, str) or not 8 <= len(new) <= 128:
        raise ValidationError('新密码需为 8 至 128 个字符')
    if new == current:
        raise ValidationError('新密码不能与旧密码相同')
    user.set_password(new)
    db.session.commit()
    return APIResponse.success(message='密码已修改')


@api_bp.route('/user/collections', methods=['GET'])
def get_collections():
    user = _get_authenticated_user_or_401()
    page = max(1, request.args.get('page', 1, type=int))
    size = max(1, min(50, request.args.get('per_page', 12, type=int)))
    query = (Artwork.query.join(Collection).filter(Collection.user_id == user.id)
             .filter(db.or_(Artwork.is_public.is_(True), Artwork.user_id == user.id))
             .order_by(Collection.created_at.desc(), Collection.id.desc()))
    result = query.paginate(page=page, per_page=size, error_out=False)
    return APIResponse.paginated([w.to_dict() for w in result.items], result.total, page, size)


@api_bp.get('/user/works')
def get_own_works():
    user = _get_authenticated_user_or_401()
    page = max(1, request.args.get('page', 1, type=int))
    size = max(1, min(100, request.args.get('per_page', 20, type=int)))
    from app.models.like import Like
    from sqlalchemy import select
    query = Artwork.query.filter_by(user_id=user.id)
    visibility = request.args.get('visibility')
    if visibility in ('public', 'private'):
        query = query.filter(Artwork.is_public.is_(visibility == 'public'))
    if request.args.get('sort') == 'likes':
        count = select(db.func.count(Like.id)).where(Like.artwork_id == Artwork.id).correlate(Artwork).scalar_subquery()
        query = query.order_by(count.desc())
    result = query.order_by(Artwork.created_at.desc(), Artwork.id.desc()).paginate(page=page, per_page=size, error_out=False)
    ids = [w.id for w in result.items]
    counts = dict(db.session.query(Like.artwork_id, db.func.count(Like.id)).filter(
        Like.artwork_id.in_(ids)).group_by(Like.artwork_id).all()) if ids else {}
    items = [{**w.to_dict(), 'like_count': counts.get(w.id, 0)} for w in result.items]
    return APIResponse.paginated(items, result.total, page, size)


@api_bp.get('/user/statistics')
def get_user_statistics():
    user = _get_authenticated_user_or_401()
    from app.models.like import Like
    likes = db.session.query(db.func.count(Like.id)).join(
        Artwork, Like.artwork_id == Artwork.id).filter(Artwork.user_id == user.id).scalar()
    collections = Collection.query.join(Artwork).filter(
        Collection.user_id == user.id,
        db.or_(Artwork.is_public.is_(True), Artwork.user_id == user.id)).count()
    return APIResponse.success({'works': Artwork.query.filter_by(user_id=user.id).count(),
                                'collections': collections, 'likes': likes})


def _get_authenticated_user_or_401():
    """获取认证用户，未认证抛 401"""
    user = get_authenticated_user()
    if user is None:
        raise AuthenticationError('登录凭证无效或已过期')
    return user


@api_bp.route('/user/credits', methods=['GET'])
def get_user_credits():
    """用户积分余额与流水（仅本人）

    认证: get_authenticated_user()
    查询参数: page（默认1）, per_page（默认10, 最大50）
    响应: data={balance, transactions:[{amount, type, description,
           reference_id, created_at, ...}]}，分页信息在 meta.pagination
    """
    user = _get_authenticated_user_or_401()

    balance = CreditService.get_balance(user.id)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 50))

    query = (CreditTransaction.query
             .filter_by(user_id=user.id)
             .order_by(CreditTransaction.created_at.desc(),
                       CreditTransaction.id.desc()))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    total = pagination.total
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    meta = {
        'pagination': {
            'total': total,
            'count': len(pagination.items),
            'page': page,
            'page_size': per_page,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
        }
    }

    return APIResponse.success(
        data={
            'balance': balance,
            'transactions': [t.to_dict() for t in pagination.items],
        },
        message='获取积分信息成功',
        code=200,
        meta=meta,
    )
