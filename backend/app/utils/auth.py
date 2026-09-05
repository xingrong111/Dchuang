# ============================================================
# 智绘锡承 - 统一用户身份获取（JWT + Session 双认证）
# 位置: backend/app/utils/auth.py
#
# 目标: 在不修改前端（el-upload 原生 XHR 不携带 Bearer）的前提下，
#       为需要用户身份的接口提供 "JWT 优先 + Session Cookie 兜底" 的
#       安全认证机制。
#
# 身份来源（严格可信，禁止客户端提交字段）:
#   来源一: JWT identity（get_jwt_identity，签名验证）
#   来源二: Flask Session（session['user_id']，HttpOnly Cookie 签名验证）
#
# 安全策略（防止认证降级绕过）:
#   有效 JWT    → 使用 JWT 用户（优先）
#   无 JWT      → 尝试 Session 用户
#   无效/过期 JWT → 401（verify_jwt_in_request 内部抛错，绝不静默降级到 Session）
#   无 JWT 且无 Session → 返回 None（调用方返回统一 401）
# ============================================================
from flask import session
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from app.extensions import db
from app.models.user import User


def get_authenticated_user():
    """统一获取当前认证用户（JWT 优先，Session 兜底）

    Returns:
        User: 已认证用户对象
        None: 未认证（无有效 JWT 且无有效 Session）

    注意:
    - 请求携带【无效/过期】JWT 时，verify_jwt_in_request(optional=True)
      会抛出认证异常（由全局 JWT 错误回调转为 401 JSON），
      本函数不会捕获，也不会降级到 Session —— 防止伪造 JWT 绕过。
    - 绝不读取 request.form / request.json / request.args 中的
      user_id / username 等客户端字段作为身份来源。
    """
    # 1) 校验请求中的 JWT（optional: 无 JWT 不报错；有无效 JWT 直接 401）
    verify_jwt_in_request(optional=True)

    # 2) JWT 优先
    identity = get_jwt_identity()
    if identity is not None:
        try:
            user_id = int(identity)
        except (TypeError, ValueError):
            return None
        user = db.session.get(User, user_id)
        if user and user.is_active:
            return user
        return None

    # 3) JWT 缺失 → Session 兜底（HttpOnly Cookie，服务端签名）
    session_user_id = session.get('user_id')
    if session_user_id is not None:
        try:
            user_id = int(session_user_id)
        except (TypeError, ValueError):
            return None
        user = db.session.get(User, user_id)
        if user and user.is_active:
            return user

    # 4) 均无 → 未认证
    return None
