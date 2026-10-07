# ============================================================
# 智绘锡承 - 统一 API 响应工具
# 位置: backend/app/utils/response.py（依据规范 4.3.3）
#
# 响应格式（与 A_qianduan 前端 axios 拦截器约定一致）:
#   成功: {"code": 200, "message": "success", "data": {...}}
#   失败: {"code": 4xx/5xx, "message": "错误说明", "data": null}
# 前端以 response.code === 200 作为成功判断依据，因此业务 code 与 HTTP 状态码保持一致。
# ============================================================
from datetime import datetime

from flask import jsonify


class APIResponse:
    """统一响应包装器"""

    @staticmethod
    def success(data=None, message='success', code=200, meta=None):
        """成功响应

        Args:
            data: 业务数据
            message: 提示信息
            code: 业务码/HTTP 状态码（默认 200）
            meta: 元数据（如分页信息）
        """
        response = {
            'code': code,
            'message': message,
            'data': data,
            'timestamp': datetime.utcnow().isoformat(),
        }
        if meta is not None:
            response['meta'] = meta
        return jsonify(response), code

    @staticmethod
    def error(message='请求失败', code=400, data=None, errors=None):
        """错误响应

        Args:
            message: 错误说明
            code: 业务码/HTTP 状态码
            data: 错误时的数据（默认 null）
            errors: 字段级错误详情（可选）
        """
        response = {
            'code': code,
            'message': message,
            'data': data,
            'timestamp': datetime.utcnow().isoformat(),
        }
        if errors is not None:
            response['errors'] = errors
        return jsonify(response), code

    @staticmethod
    def paginated(items, total, page, page_size, message='success', code=200):
        """分页响应（规范 4.3.3）"""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        meta = {
            'pagination': {
                'total': total,
                'count': len(items),
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1,
            }
        }
        return APIResponse.success(data=items, message=message, code=code, meta=meta)
