# ============================================================
# 智绘锡承 - Flask 扩展初始化
# 位置: backend/app/extensions.py（依据规范 1.5 / 4.1.1）
# 说明: 各扩展在应用工厂中 init_app 绑定
# ============================================================
from datetime import datetime

from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# --- SQLAlchemy ORM ---
db = SQLAlchemy()

# --- Flask-Migrate 数据库迁移 ---
migrate = Migrate()

# --- 跨域（规范 4.1.1: flask_cors） ---
cors = CORS()

# --- JWT 认证（阶段3，规范 4.1.2: flask_jwt_extended） ---
jwt = JWTManager()


def _jwt_error_response(code, message):
    """JWT 错误统一 JSON 响应（与项目 APIResponse 格式一致）"""
    return jsonify({
        'code': code,
        'message': message,
        'data': None,
        'timestamp': datetime.utcnow().isoformat(),
    }), code


# ------------------------------------------------------------
# JWT 错误回调（缺少/无效/过期 Token → 统一 JSON 401）
# 前端 A_qianduan axios 拦截器: status 401 → 提示登录过期并跳转 /login
# ------------------------------------------------------------
@jwt.unauthorized_loader
def handle_missing_token(reason):
    """缺少 Authorization 头或格式错误（无 Bearer）"""
    return _jwt_error_response(401, '缺少登录凭证，请先登录')


@jwt.invalid_token_loader
def handle_invalid_token(reason):
    """Token 无效或格式错误"""
    return _jwt_error_response(401, '登录凭证无效或已过期')


@jwt.expired_token_loader
def handle_expired_token(jwt_header, jwt_payload):
    """Token 过期"""
    return _jwt_error_response(401, '登录凭证已过期，请重新登录')
