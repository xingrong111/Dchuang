# ============================================================
# 智绘锡承 - 后端应用入口
# 位置: backend/run.py（依据规范 1.5 / 1.3.2: python run.py）
#
# 启动:
#   cd backend
#   python run.py            # 默认 development 配置，端口 8000
#   python run.py production # 指定配置
# ============================================================
import os

from app import create_app

app = create_app(os.getenv('FLASK_CONFIG', 'default'))


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8000'))
    # 前端 Vite 代理 target: http://localhost:8000（frontend/vite.config.js）
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))
