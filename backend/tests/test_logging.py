# ============================================================
# 智绘锡承 - AI 任务完成日志测试（阶段16-D）
# 覆盖: Worker 轮询/超时清理触发 AI_TASK_DONE 结构化日志
#   AI_TASK_DONE task_id=<id> provider=<p> status=<s> duration=<秒>
#   未终态不记录 / 无任务不记录 / 幂等（终态只记一次）
# 全部 mock query service，零真实第三方调用
# ============================================================
import logging
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def app(tmp_path):
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    return app


@pytest.fixture
def db(app):
    from app.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app, db):
    return app.test_client()


def _make_user(app, name='loguser'):
    from app.extensions import db as flask_db
    from app.models.user import User

    with app.app_context():
        user = User(username=name, email=f'{name}@e.com', password='pass123')
        flask_db.session.add(user)
        flask_db.session.commit()
        return user.id


def _seed_running(app, job_id='job-log', minutes_old=0, user=None):
    from app.extensions import db as flask_db
    from app.models.ai_task import AITask

    uid = user or _make_user(app)
    with app.app_context():
        task = AITask(user_id=uid, provider='hunyuan', model='hunyuan-3d',
                      task_type='text_to_3d', prompt='任务', status='RUNNING',
                      external_task_id=job_id)
        if minutes_old:
            task.updated_at = datetime.utcnow() - timedelta(minutes=minutes_old)
        flask_db.session.add(task)
        flask_db.session.commit()
        return task.id


class StubQueryService:
    provider_name = 'hunyuan'

    def __init__(self, result=None, error=None, exc=None):
        self._result = result
        self._error = error
        self._exc = exc

    def query_task(self, task):
        if self._exc is not None:
            raise self._exc
        if self._error is not None:
            from app.utils.exceptions import AIServiceError
            raise AIServiceError(self._error)
        return self._result


def _stub(result=None, error=None, exc=None):
    return StubQueryService(result=result, error=error, exc=exc)


def _tencent_url():
    return 'https://hunyuan-prod-1258344699.cos.ap-guangzhou.tencentcos.cn/3d/out/m.glb'


class TestTaskDoneLogging:
    """AI_TASK_DONE 结构化日志"""

    def _run(self, app, caplog):
        from app.workers.ai_task_worker import AITaskWorker

        with caplog.at_level(logging.INFO, logger='app.services.ai_task'):
            with app.app_context():
                return AITaskWorker().run_once()

    def test_success_logs_ai_task_done(self, app, db, monkeypatch, caplog):
        """SUCCESS → AI_TASK_DONE task_id/provider/status/duration"""
        tid = _seed_running(app, job_id='job-ok')
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'SUCCESS',
                                                  'result_url': _tencent_url(),
                                                  'error_message': None}))
        self._run(app, caplog)
        log_text = caplog.text
        assert f'AI_TASK_DONE task_id={tid}' in log_text
        assert 'provider=hunyuan' in log_text
        assert 'status=SUCCESS' in log_text
        assert 'duration=' in log_text

    def test_failed_logs_ai_task_done(self, app, db, monkeypatch, caplog):
        """查询返回 FAILED → AI_TASK_DONE status=FAILED"""
        tid = _seed_running(app, job_id='job-fail')
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'FAILED',
                                                  'result_url': None,
                                                  'error_message': '内容不合规'}))
        self._run(app, caplog)
        log_text = caplog.text
        assert f'AI_TASK_DONE task_id={tid}' in log_text
        assert 'status=FAILED' in log_text
        assert 'duration=' in log_text

    def test_timeout_logs_ai_task_done(self, app, db, monkeypatch, caplog):
        """超时清理落 FAILED → AI_TASK_DONE status=FAILED"""
        app.config['AI_TASK_TIMEOUT_SECONDS'] = 1
        tid = _seed_running(app, job_id='job-timeout', minutes_old=30)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'RUNNING',
                                                  'result_url': None,
                                                  'error_message': None}))
        self._run(app, caplog)
        log_text = caplog.text
        assert f'AI_TASK_DONE task_id={tid}' in log_text
        assert 'provider=hunyuan' in log_text
        assert 'status=FAILED' in log_text

    def test_running_keeps_running_no_done_log(self, app, db, monkeypatch, caplog):
        """查询仍 RUNNING（未终态）→ 不产生 AI_TASK_DONE"""
        tid = _seed_running(app, job_id='job-still')
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'RUNNING',
                                                  'result_url': None,
                                                  'error_message': None}))
        self._run(app, caplog)
        assert 'AI_TASK_DONE' not in caplog.text

    def test_no_tasks_no_done_log(self, app, db, caplog):
        """无 RUNNING 任务 → 无 AI_TASK_DONE"""
        self._run(app, caplog)
        assert 'AI_TASK_DONE' not in caplog.text

    def test_done_logged_once(self, app, db, monkeypatch, caplog):
        """终态只记录一次（第二轮不再扫 SUCCESS 任务）"""
        from app.workers.ai_task_worker import AITaskWorker

        tid = _seed_running(app, job_id='job-once')
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'SUCCESS',
                                                  'result_url': _tencent_url(),
                                                  'error_message': None}))
        with caplog.at_level(logging.INFO, logger='app.services.ai_task'):
            with app.app_context():
                AITaskWorker().run_once()
                AITaskWorker().run_once()
        assert caplog.text.count(f'AI_TASK_DONE task_id={tid}') == 1
