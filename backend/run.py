# ============================================================
# 智绘锡承 - 后端应用入口
# 位置: backend/run.py（依据规范 1.5 / 1.3.2: python run.py）
#
# 启动:
#   cd backend
#   python run.py            # 默认 development 配置，端口 8000
#   python run.py production # 指定配置
#
# AI Worker（阶段15-C/15-D）: AI_WORKER_ENABLED=true 时以 daemon 线程启动
# 后台任务调度；SIGTERM/SIGINT 触发优雅停止（当前轮完成后退出）；默认关闭
# ============================================================
import os
import signal
import sys
import threading

from app import create_app
from app.workers.ai_task_worker import AITaskWorker

app = create_app(os.getenv('FLASK_CONFIG', 'default'))

_worker_thread = None


def _start_ai_worker(app):
    """启动 AI Worker daemon 线程并注册优雅停止信号"""
    global _worker_thread

    worker_interval = app.config.get('AI_WORKER_INTERVAL_SECONDS', 30)
    worker = AITaskWorker(interval_seconds=worker_interval)

    def _loop():
        worker.start(interval_seconds=worker_interval, app=app)

    _worker_thread = threading.Thread(
        target=_loop, daemon=True, name='ai-task-worker',
    )
    _worker_thread.start()
    print(f'AI Worker 已启动（interval={worker_interval}s）')

    def _graceful_stop(signum, frame):
        print(f'收到信号 {signum}，正在停止 AI Worker（等待当前轮完成）...')
        worker.stop()
        if _worker_thread is not None:
            _worker_thread.join(timeout=10)
        print('AI Worker 已优雅停止')
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, _graceful_stop)
        signal.signal(signal.SIGINT, _graceful_stop)
    except (ValueError, OSError):
        pass  # 非主线程/平台不支持 → 跳过


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8000'))

    # 阶段15-C/15-D: AI Worker（默认关闭，避免开发/测试/多实例误启动多个 Worker）
    if app.config.get('AI_WORKER_ENABLED', False):
        _start_ai_worker(app)

    # 前端 Vite 代理 target: http://localhost:8000（frontend/vite.config.js）
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))
