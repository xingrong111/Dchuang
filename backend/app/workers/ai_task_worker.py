# ============================================================
# 智绘锡承 - AI 任务后台 Worker
# 位置: backend/app/workers/ai_task_worker.py
#
# 职责: 扫描 AITask.status == RUNNING 的异步任务（腾讯混元 3D JobId），
#       调用公共服务刷新（query_task → SUCCESS/FAILED + 产物转存 + Artwork）。
#       业务逻辑零复制 —— 全部复用 services/ai_task.py。
#
# 运行方式:
#   1. 手动模式（测试/一次性）: AITaskWorker().run_once()
#      （需在 Flask app context 内执行）
#   2. 后台循环模式: worker = AITaskWorker(); worker.start(interval_seconds, app)
#      或命令行: python -m app.workers.ai_task_worker
#   3. run.py 集成: AI_WORKER_ENABLED=true 时以 daemon 线程启动 start()
#
# 配置:
#   AI_WORKER_ENABLED（默认 false，开发/测试不自动启动）
#   AI_WORKER_INTERVAL_SECONDS（默认 30）
# ============================================================
import logging
import signal
import threading
import time

logger = logging.getLogger(__name__)


class AITaskWorker:
    """AI 任务调度 Worker"""

    def __init__(self, interval_seconds=30):
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()

    # ------------------------------------------------------------
    # 手动模式（测试/一次性扫描）
    # ------------------------------------------------------------
    def run_once(self):
        """执行一次扫描：超时清理 + 刷新全部 RUNNING+JobId 任务

        需在 Flask app context 内调用（SQLAlchemy 依赖）。
        输出本轮状态日志: processed/success/failed/running/cost/providers

        Returns:
            dict: {'processed', 'success', 'failed', 'running',
                   'providers', 'cost'} 状态明细（含 Provider 分布与耗时）
        """
        from app.services.ai_task import process_running_tasks

        result = process_running_tasks()
        # Provider 分布以逗号连接（无任务时为空）
        provider_text = ','.join(
            f'{name}={count}' for name, count in
            sorted((result.get('providers') or {}).items())
        )
        logger.info(
            'AI Worker: processed=%d success=%d failed=%d running=%d cost=%.2fs'
            ' providers=%s',
            result.get('processed', 0), result.get('success', 0),
            result.get('failed', 0), result.get('running', 0),
            float(result.get('cost', 0.0) or 0.0), provider_text,
        )
        return result

    # ------------------------------------------------------------
    # 后台循环模式
    # ------------------------------------------------------------
    def start(self, interval_seconds=None, app=None):
        """阻塞循环：每 interval 秒扫描一次 RUNNING 任务

        优雅停止: 调用 stop() 或接收 SIGTERM/SIGINT（handle_signal）后，
        当前扫描完成后退出循环并输出停止日志（不立即中断在跑任务）。

        Args:
            interval_seconds: 轮询间隔（缺省用构造值/配置）
            app: Flask app（每轮在其 app context 内执行；None 时调用方须保证 context）
        """
        interval = interval_seconds or self.interval_seconds
        logger.info('AI Worker 启动: interval=%ss', interval)
        while not self._stop_event.is_set():
            try:
                if app is not None:
                    with app.app_context():
                        self.run_once()
                else:
                    self.run_once()
            except Exception:
                logger.exception('AI Worker 扫描异常（下轮重试）')
            # 等待间隔；stop 事件可中断等待（即时退出）
            self._stop_event.wait(interval)
        logger.info('AI Worker 已优雅停止')

    def stop(self):
        """请求停止（当前轮完成后退出循环）"""
        self._stop_event.set()

    def handle_signal(self, signum, frame):
        """信号处理器: SIGTERM/SIGINT → 优雅停止（不立即退出，等当前轮完成）

        注册示例:
            signal.signal(signal.SIGTERM, worker.handle_signal)
            signal.signal(signal.SIGINT, worker.handle_signal)
        """
        logger.info('AI Worker 收到信号 %s，正在优雅停止...', signum)
        self.stop()


def run_once():
    """模块级便捷: 执行一次扫描（手动/测试）"""
    return AITaskWorker().run_once()


def start(interval_seconds=30, app=None):
    """模块级便捷: 启动后台循环（阻塞；供 run.py daemon 线程或 CLI 调用）"""
    worker = AITaskWorker(interval_seconds=interval_seconds)
    # CLI 场景注册信号（run.py 线程场景由 run.py 注册后调用 worker.stop）
    _install_signal_handlers(worker)
    worker.start(interval_seconds, app)


def _install_signal_handlers(worker):
    """主线程可用的信号注册（SIGTERM/SIGINT → worker 优雅停止）"""
    try:
        signal.signal(signal.SIGTERM, worker.handle_signal)
        signal.signal(signal.SIGINT, worker.handle_signal)
    except (ValueError, OSError):
        # 非主线程/平台不支持 → 跳过（调用方可用 stop()）
        logger.debug('信号处理器未注册（非主线程或平台不支持）')


if __name__ == '__main__':
    # CLI: python -m app.workers.ai_task_worker
    from app import create_app

    logging.basicConfig(level=logging.INFO)
    _app = create_app()
    _interval = _app.config.get('AI_WORKER_INTERVAL_SECONDS', 30)
    start(interval_seconds=_interval, app=_app)
