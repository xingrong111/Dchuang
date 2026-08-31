# ============================================================
# 智绘锡承 - Flask 扩展初始化
# 位置: backend/app/extensions.py（依据规范 1.5 / 4.1.1）
# 说明: 各扩展在应用工厂中 init_app 绑定
# ============================================================
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

# --- SQLAlchemy ORM ---
db = SQLAlchemy()

# --- Flask-Migrate 数据库迁移 ---
migrate = Migrate()

# --- 跨域（规范 4.1.1: flask_cors） ---
cors = CORS()
