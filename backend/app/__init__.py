# ============================================================
# 智绘锡承 - Flask 应用工厂
# 位置: backend/app/__init__.py（依据规范 4.1.1）
# ============================================================
import logging
import os
import sys

from flask import Flask

from config import config
from app.extensions import db, migrate, cors, jwt


def create_app(config_name='default'):
    """应用工厂函数

    Args:
        config_name: 'development' | 'testing' | 'production' | 'default'
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # --- 初始化扩展 ---
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/*": {"origins": app.config['CORS_ORIGINS']}})
    jwt.init_app(app)

    # --- 导入数据模型（注册到 SQLAlchemy metadata，create_all/migrate 才能识别） ---
    from app import models  # noqa: F401

    # --- 基础日志配置 ---
    _configure_logging(app, config_name)

    # --- 注册蓝图 ---
    # 注意: 前端 Vite 开发代理将 /api 前缀剥除后转发到本服务（localhost:8000），
    # 因此后端蓝图不挂 /api/v1 前缀，直接以 /xxx 注册（与 A_qianduan 前端 axios 路径一致）。
    from app.api.v1 import api_bp
    app.register_blueprint(api_bp)

    # --- 注册统一错误处理器（400/401/403/404/405/500 → JSON） ---
    from app.utils.exceptions import register_error_handlers
    register_error_handlers(app)

    # --- 健康检查 ---
    # GET /health 定义于 app/api/v1/health.py（经 api_bp 注册）

    return app


def _configure_logging(app, config_name='default'):
    """基础日志配置（规范 1.2 基础设施层：日志统一管理）"""
    log_level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
    )
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.info(
        '%s v%s 启动 (config=%s, debug=%s)',
        app.config.get('APP_NAME'),
        app.config.get('APP_VERSION'),
        config_name,
        app.config.get('DEBUG'),
    )
