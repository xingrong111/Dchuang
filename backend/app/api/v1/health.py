# ============================================================
# 智绘锡承 - 健康检查接口
# GET /health （无需认证）
# ============================================================
from app.api.v1 import api_bp
from app.utils.response import APIResponse


@api_bp.route('/health', methods=['GET'])
def health():
    """服务健康检查"""
    return APIResponse.success(
        data={'status': 'healthy'},
        message='Backend service is running',
        code=200,
    )
