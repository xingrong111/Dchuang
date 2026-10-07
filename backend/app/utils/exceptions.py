# ============================================================
# 智绘锡承 - 自定义异常与统一错误处理
# 位置: backend/app/utils/exceptions.py（依据规范 4.1.1: register_error_handlers）
#
# 统一将 HTTP 错误转换为 JSON 响应，不返回 Flask 默认 HTML 错误页。
# ============================================================
import logging
from datetime import datetime

from flask import jsonify
from werkzeug.exceptions import (
    BadRequest,
    Unauthorized,
    Forbidden,
    NotFound,
    MethodNotAllowed,
    InternalServerError,
    RequestEntityTooLarge,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# 自定义业务异常
# ------------------------------------------------------------
class ApiException(Exception):
    """业务异常基类"""

    def __init__(self, message='请求失败', code=400, errors=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.errors = errors


class ValidationError(ApiException):
    """参数校验失败（400）"""

    def __init__(self, message='参数校验失败', errors=None):
        super().__init__(message=message, code=400, errors=errors)


class AuthenticationError(ApiException):
    """认证失败（401）"""

    def __init__(self, message='认证失败'):
        super().__init__(message=message, code=401)


class PermissionError_(ApiException):
    """权限不足（403）"""

    def __init__(self, message='没有权限访问该资源'):
        super().__init__(message=message, code=403)


class ResourceNotFoundError(ApiException):
    """资源不存在（404）"""

    def __init__(self, message='资源不存在'):
        super().__init__(message=message, code=404)


class AIServiceError(ApiException):
    """AI 服务调用失败（503，规范 4.3.2）"""

    def __init__(self, message='AI 服务调用失败'):
        super().__init__(message=message, code=503)


class CreditInsufficientError(ApiException):
    """平台积分不足（402 Payment Required）"""

    def __init__(self, message='积分不足，请先充值'):
        super().__init__(message=message, code=402)


def _error_response(code, message, errors=None):
    """构造统一错误 JSON"""
    body = {
        'code': code,
        'message': message,
        'data': None,
        'timestamp': datetime.utcnow().isoformat(),
    }
    if errors is not None:
        body['errors'] = errors
    return jsonify(body), code


# ------------------------------------------------------------
# 错误处理器注册
# ------------------------------------------------------------
def register_error_handlers(app):
    """注册全局 HTTP 错误处理器（400/401/403/404/405/500）"""

    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        return _error_response(400, e.description or '请求参数错误')

    @app.errorhandler(Unauthorized)
    def handle_unauthorized(e):
        return _error_response(401, e.description or '未授权，请先登录')

    @app.errorhandler(Forbidden)
    def handle_forbidden(e):
        return _error_response(403, e.description or '没有权限访问该资源')

    @app.errorhandler(NotFound)
    def handle_not_found(e):
        return _error_response(404, e.description or '请求的资源不存在')

    @app.errorhandler(MethodNotAllowed)
    def handle_method_not_allowed(e):
        return _error_response(405, e.description or '请求方法不允许')

    @app.errorhandler(InternalServerError)
    def handle_internal_error(e):
        logger.exception('服务器内部错误: %s', e)
        return _error_response(500, '服务器内部错误，请稍后重试')

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(e):
        """请求体超过 MAX_CONTENT_LENGTH（50MB）→ 统一 JSON 413"""
        return _error_response(413, '文件大小超过限制（最大 50MB）')

    # --- 自定义业务异常 ---
    @app.errorhandler(ApiException)
    def handle_api_exception(e):
        if e.code >= 500:
            logger.error('业务异常 [%s]: %s', e.code, e.message)
        return _error_response(e.code, e.message, getattr(e, 'errors', None))

    # --- 兜底：未知异常 ---
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        logger.exception('未处理异常: %s', e)
        return _error_response(500, '服务器内部错误，请稍后重试')
