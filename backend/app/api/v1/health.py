# ============================================================
# 智绘锡承 - 健康检查接口（阶段16-D 交付收口增强）
# 位置: backend/app/api/v1/health.py
#
# 接口（无需认证）:
#   GET /health        存活探针 → data: {status:'ok', version, timestamp}
#   GET /health/ready  就绪探针 → 数据库连通 + 必要配置齐全 → {ready:true}；
#                        异常 → 503（统一错误体 {code,message,data:null}）
#
# 用途: 容器编排 liveness/readiness 探针（如 Kubernetes / docker healthcheck）
# ============================================================
from datetime import datetime

from flask import current_app

from app.api.v1 import api_bp
from app.extensions import db
from app.utils.response import APIResponse
from sqlalchemy import text

# 就绪检查要求的必要配置键（缺失 → 就绪失败 503）
REQUIRED_CONFIG_KEYS = ('SECRET_KEY', 'JWT_SECRET_KEY', 'SQLALCHEMY_DATABASE_URI')


def _db_ping():
    """数据库连通性探活（SELECT 1，只读；失败抛异常由调用方处理）"""
    db.session.execute(text('SELECT 1'))


@api_bp.route('/health', methods=['GET'])
def health():
    """存活探针: 服务进程在跑即 200（不依赖 DB）"""
    return APIResponse.success(
        data={
            'status': 'ok',
            'version': current_app.config.get('APP_VERSION', '1.0.0'),
            'timestamp': datetime.utcnow().isoformat(),
        },
        message='Backend service is running',
        code=200,
    )


@api_bp.route('/health/ready', methods=['GET'])
def health_ready():
    """就绪探针: 数据库连接 + 必要配置

    检查项:
      1. 数据库连通（SELECT 1）
      2. 必要配置齐全（SECRET_KEY / JWT_SECRET_KEY / SQLALCHEMY_DATABASE_URI）
    全部通过 → data: {ready: true}；任一失败 → 503 统一错误体。
    """
    # 1) 数据库连通
    try:
        _db_ping()
    except Exception as exc:  # noqa: BLE001 - 探针需捕获一切连接异常
        current_app.logger.error('健康检查: 数据库连接失败: %s', exc)
        return APIResponse.error('数据库连接失败，服务未就绪', code=503)

    # 2) 必要配置
    missing = [key for key in REQUIRED_CONFIG_KEYS
               if not current_app.config.get(key)]
    if missing:
        current_app.logger.error('健康检查: 缺少必要配置: %s', missing)
        return APIResponse.error(
            f'缺少必要配置: {",".join(missing)}，服务未就绪', code=503)

    return APIResponse.success(
        data={'ready': True},
        message='服务就绪',
        code=200,
    )
