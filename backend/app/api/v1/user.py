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
