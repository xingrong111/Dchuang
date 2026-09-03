# ============================================================
# 智绘锡承 - Worker 生产化 + 统计增强测试（阶段15-D）
# 覆盖: SIGTERM 优雅停止 / 扫描状态日志 / 单任务失败不影响批次 /
#       statistics average_duration / 用户隔离 / 空数据
# 全部 mock query service，零真实第三方调用
# ============================================================
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录 + Mock Provider）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    return app


@pytest.fixture
def db(app):
    """初始化数据库表"""
    from app.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app, db):
    """测试客户端"""
    return app.test_client()


def _make_user(app, name='wpro'):
    from app.extensions import db as flask_db
    from app.models.user import User

    with app.app_context():
        user = User(username=name, email=f'{name}@e.com', password='pass123')
        flask_db.session.add(user)
        flask_db.session.commit()
        return user.id


def _seed_running(app, job_id='job-wp', minutes_old=0, user=None):
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


class TestWorkerGracefulStop:
    """优雅停止"""

    def test_handle_signal_sets_stop(self):
        """信号处理器: SIGTERM/SIGINT → stop 事件置位"""
        import signal

        from app.workers.ai_task_worker import AITaskWorker

        worker = AITaskWorker()
        worker.handle_signal(signal.SIGTERM, None)
        assert worker._stop_event.is_set()
        worker.stop()  # 幂等不抛

    def test_stop_after_current_round(self, app, db, monkeypatch):
        """stop() 后 run_once 仍可完成当前轮（不中断在跑扫描）"""
        from app.services.ai_task import process_running_tasks
        from app.workers.ai_task_worker import AITaskWorker

        tid = _seed_running(app)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'SUCCESS',
                                                  'result_url': _tencent_url(),
                                                  'error_message': None}))
        with app.app_context():
            worker = AITaskWorker()
            worker.stop()  # 先请求停止
            # 当前轮仍执行完成（优雅语义）
            result = worker.run_once()
            assert result['processed'] == 1
            assert result['success'] == 1
            # 16-C: 新增字段 —— Provider 分布 + 本轮耗时
            assert result['providers'] == {'hunyuan': 1}
            assert isinstance(result['cost'], float)


class TestWorkerLogs:
    """扫描状态日志"""

    def test_run_once_logs_stats(self, app, db, monkeypatch, caplog):
        """run_once 输出状态日志（processed/success/failed/running/cost）"""
        import logging

        from app.workers.ai_task_worker import AITaskWorker

        uid = _make_user(app)
        _seed_running(app, job_id='job-log-1', user=uid)
        _seed_running(app, job_id='job-log-2', user=uid)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'SUCCESS',
                                                  'result_url': _tencent_url(),
                                                  'error_message': None}))
        with caplog.at_level(logging.INFO, logger='app.workers.ai_task_worker'):
            with app.app_context():
                result = AITaskWorker().run_once()
        assert result['processed'] == 2
        assert result['success'] == 2
        assert result['providers'] == {'hunyuan': 2}  # 16-C
        assert isinstance(result['cost'], float)      # 16-C
        log_text = caplog.text
        assert 'AI Worker:' in log_text
        assert 'processed=2' in log_text
        assert 'success=2' in log_text
        assert 'cost=' in log_text
        assert 'providers=hunyuan=2' in log_text  # 16-C Provider 分布日志


class TestWorkerBatchIsolation:
    """单任务失败不影响其他任务"""

    def test_one_failure_does_not_stop_batch(self, app, db, monkeypatch):
        """批次中一个任务 query 抛异常（→FAILED），其余任务正常推进"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        uid = _make_user(app)
        tid_ok = _seed_running(app, job_id='job-ok', user=uid)
        tid_bad = _seed_running(app, job_id='job-bad', user=uid)

        class DispatchingService:
            """按任务 JobId 分发的假 Provider"""
            provider_name = 'hunyuan'

            def query_task(self, task):
                if task.external_task_id == 'job-bad':
                    raise RuntimeError('SDK 崩了')
                return {'status': 'SUCCESS', 'result_url': _tencent_url(),
                        'error_message': None}

        monkeypatch.setattr('app.services.ai_task.get_ai_service', DispatchingService)

        with app.app_context():
            from app.services.ai_task import process_running_tasks
            result = process_running_tasks()
            assert result['processed'] == 2
            assert result['success'] == 1
            assert result['failed'] == 1
            assert result['providers'] == {'hunyuan': 2}  # 16-C
            assert isinstance(result['cost'], float)      # 16-C
            ok = flask_db.session.get(AITask, tid_ok)
            bad = flask_db.session.get(AITask, tid_bad)
            assert ok.status == 'SUCCESS'
            assert bad.status == 'FAILED'  # 异常任务独立落 FAILED


class TestStatisticsAverageDuration:
    """GET /ai/tasks/statistics average_duration"""

    def _register_login(self, client, name='statw'):
        client.post('/auth/register', json={
            'username': name, 'email': f'{name}@e.com', 'password': 'password123',
        })
        resp = client.post('/auth/login', json={
            'email': f'{name}@e.com', 'password': 'password123',
        })
        return resp.get_json()['data']['token'], resp.get_json()['data']['id']

    def _seed_success(self, app, user_id, created_delta_minutes, duration_seconds):
        """落库 SUCCESS 任务：created_at 距今 minutes 前，耗时 duration 秒"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        with app.app_context():
            created = datetime.utcnow() - timedelta(minutes=created_delta_minutes)
            task = AITask(user_id=user_id, provider='mock', model='mock-3d',
                          task_type='text_to_3d', prompt='统计', status='SUCCESS')
            task.created_at = created
            task.updated_at = created + timedelta(seconds=duration_seconds)
            flask_db.session.add(task)
            flask_db.session.commit()

    def test_average_duration_computed(self, client, app):
        """SUCCESS 任务平均耗时（updated_at - created_at，秒）"""
        token, uid = self._register_login(client)
        self._seed_success(app, uid, created_delta_minutes=10, duration_seconds=60)
        self._seed_success(app, uid, created_delta_minutes=20, duration_seconds=120)

        r = client.get('/ai/tasks/statistics', headers={'Authorization': f'Bearer {token}'})
        d = r.get_json()['data']
        assert d['success'] == 2
        assert d['average_duration'] == 90.0  # (60+120)/2

    def test_empty_average_duration_zero(self, client, app):
        """无成功任务 → average_duration 0（不除零）"""
        token, _ = self._register_login(client, 'statempty')
        r = client.get('/ai/tasks/statistics', headers={'Authorization': f'Bearer {token}'})
        d = r.get_json()['data']
        assert d['total'] == 0
        assert d['average_duration'] == 0.0

    def test_user_isolated_statistics(self, client, app):
        """统计/平均耗时仅本人任务"""
        token_a, uid_a = self._register_login(client, 'stata')
        self._seed_success(app, uid_a, created_delta_minutes=5, duration_seconds=30)

        token_b, _ = self._register_login(client, 'statb')
        r = client.get('/ai/tasks/statistics', headers={'Authorization': f'Bearer {token_b}'})
        d = r.get_json()['data']
        assert d['total'] == 0  # 看不到 A 的任务
        assert d['average_duration'] == 0.0