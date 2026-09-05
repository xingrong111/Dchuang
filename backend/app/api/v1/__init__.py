# ============================================================
# 智绘锡承 - API v1 蓝图
#
# 说明（接口前缀约定，重要）:
# 前端 Vite 开发代理 (frontend/vite.config.js) 将 /api 前缀剥除后
# 转发到 http://localhost:8000，因此后端蓝图不挂 /api/v1 前缀，
# 直接以 /health、/auth/login 等形式注册，与 A_qianduan 前端
# axios 调用路径保持一致（详见《智绘锡承项目现状与B同学后端开发实施计划》）。
# ============================================================
from flask import Blueprint

api_bp = Blueprint('api_v1', __name__)

# 注册当前后端模块路由：health、auth、upload、user、artwork、ai、admin
from app.api.v1 import health  # noqa: E402,F401
from app.api.v1 import auth  # noqa: E402,F401
from app.api.v1 import upload  # noqa: E402,F401
from app.api.v1 import user  # noqa: E402,F401
from app.api.v1 import artwork  # noqa: E402,F401
from app.api.v1 import ai  # noqa: E402,F401
from app.api.v1 import admin  # noqa: E402,F401
