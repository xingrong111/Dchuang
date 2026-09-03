# ============================================================
# 智绘锡承 - AI 任务后台 Worker 测试（阶段15-C）
# 覆盖: 扫描 / DONE→SUCCESS / FAILED / SUCCESS 建 Artwork /
#       异常→FAILED / 超时处理 / worker 关闭不影响 API / run_once 幂等
# 全部 mock query service（monkeypatch services.ai_task.get_ai_service），零真实调用
# ============================================================
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录 + Mock Provider）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'  # 显式 Mock（隔离 .env 的 hunyuan）
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


def _make_user(app):
    """创建用户（worker 场景归属）"""
    from app.extensions import db as flask_db
    from app.models.user import User

    with app.app_context():
        user = User(username='wk1', email='wk1@e.com', password='pass123')
        flask_db.session.add(user)
        flask_db.session.commit()
        return user.id


def _seed_running(app, job_id='job-wk-1', minutes_old=0, prompt='任务'):
    """落库一个 RUNNING + JobId 任务，返回 task id"""
    from app.extensions import db as flask_db
    from app.models.ai_task import AITask

    uid = _make_user(app)
    with app.app_context():
        task = AITask(user_id=uid, provider='hunyuan', model='hunyuan-3d',
                      task_type='text_to_3d', prompt=prompt,
                      status='RUNNING', external_task_id=job_id)
        if minutes_old:
            task.updated_at = datetime.utcnow() - timedelta(minutes=minutes_old)
        flask_db.session.add(task)
        flask_db.session.commit()
        return task.id


class StubQueryService:
    """带 query_task 能力的假 Provider"""
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
    return 'https://hunyuan-prod-1258344699.cos.ap-guangzhou.tencentcos.cn/3d/out/model.glb'


class TestWorkerScan:
    """RUNNING 扫描"""

    def test_scan_running_keeps_running(self, app, db, monkeypatch):
        """RUNNING 任务扫描: query RUNNING → 保持 RUNNING + 处理数正确"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask
        from app.services.ai_task import process_running_tasks

        tid = _seed_running(app)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'RUNNING', 'result_url': None,
                                                  'error_message': None}))
        with app.app_context():
            result = process_running_tasks()
            task = flask_db.session.get(AITask, tid)
            assert result['processed'] == 1
            assert task.status == 'RUNNING'  # 未终态，等待下次

    def test_done_to_success(self, app, db, monkeypatch):
        """腾讯返回 DONE(SUCCESS) → 任务 SUCCESS + result_url"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        tid = _seed_running(app)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'SUCCESS',
                                                  'result_url': _tencent_url(),
                                                  'error_message': None}))
        with app.app_context():
            from app.services.ai_task import process_running_tasks
            process_running_tasks()
            task = flask_db.session.get(AITask, tid)
            assert task.status == 'SUCCESS'
            # 域名非白名单 → 下载 fallback 保留腾讯 URL（未真实联网）
            assert task.result_url == _tencent_url()

    def test_failed_result(self, app, db, monkeypatch):
        """腾讯 FAILED → 任务 FAILED + error_message"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        tid = _seed_running(app)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'FAILED',
                                                  'result_url': None,
                                                  'error_message': '内容不合规'}))
        with app.app_context():
            from app.services.ai_task import process_running_tasks
            process_running_tasks()
            task = flask_db.session.get(AITask, tid)
            assert task.status == 'FAILED'
            assert task.error_message == '内容不合规'

    def test_success_creates_artwork(self, app, db, monkeypatch):
        """SUCCESS → 创建 Artwork（方案 B）并回填 artwork_id"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask
        from app.models.artwork import Artwork

        tid = _seed_running(app, prompt='生成惠山泥人')
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'SUCCESS',
                                                  'result_url': _tencent_url(),
                                                  'error_message': None}))
        with app.app_context():
            from app.services.ai_task import process_running_tasks
            process_running_tasks()
            task = flask_db.session.get(AITask, tid)
            assert task.artwork_id is not None
            art = flask_db.session.get(Artwork, task.artwork_id)
            assert art is not None
            assert art.is_ai_generated is True
            assert art.title == '生成惠山泥人'
            assert Artwork.query.count() == 1

    def test_unexpected_exception_to_failed(self, app, db, monkeypatch):
        """查询抛意外异常（非 AIServiceError）→ 任务 FAILED（防僵尸/500）"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        tid = _seed_running(app)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(exc=RuntimeError('SDK 内部错误')))
        with app.app_context():
            from app.services.ai_task import process_running_tasks
            process_running_tasks()
            task = flask_db.session.get(AITask, tid)
            assert task.status == 'FAILED'
            assert '查询异常' in task.error_message

    def test_aiservice_error_keeps_running(self, app, db, monkeypatch):
        """AIServiceError（网络/凭据等）→ 保持 RUNNING（轮询重试，不误判）"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        tid = _seed_running(app)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(error='腾讯查询失败: timeout'))
        with app.app_context():
            from app.services.ai_task import process_running_tasks
            process_running_tasks()
            task = flask_db.session.get(AITask, tid)
            assert task.status == 'RUNNING'

    def test_timeout_task_handled(self, app, db, monkeypatch):
        """超时任务（RUNNING + JobId + updated_at 超阈值）→ FAILED"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        app.config['AI_TASK_TIMEOUT_SECONDS'] = 1800
        tid = _seed_running(app, minutes_old=40)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'RUNNING', 'result_url': None,
                                                  'error_message': None}))
        with app.app_context():
            from app.services.ai_task import process_running_tasks
            process_running_tasks()
            task = flask_db.session.get(AITask, tid)
            assert task.status == 'FAILED'
            assert '超时' in task.error_message


class TestWorkerLifecycle:
    """Worker 生命周期/幂等/API 独立性"""

    def test_worker_stop_api_unaffected(self, app, client):
        """Worker 可停止；关闭不影响 API（GET 任务仍正常）"""
        from app.workers.ai_task_worker import AITaskWorker

        # 注册登录（API 用）
        client.post('/auth/register', json={
            'username': 'wkw', 'email': 'wkw@e.com', 'password': 'password123',
        })
        login = client.post('/auth/login', json={
            'email': 'wkw@e.com', 'password': 'password123',
        })
        token = login.get_json()['data']['token']
        # 造一个本人 RUNNING 任务（API 查询用；无 query 能力 → 保持 RUNNING 200）
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成紫砂壶',
        }, headers={'Authorization': f'Bearer {token}'})
        tid = resp.get_json()['data']['id']

        worker = AITaskWorker()
        worker.stop()  # 停止（未启动也不抛）
        assert worker._stop_event.is_set()

        # API 不受影响
        r = client.get(f'/ai/tasks/{tid}', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200

    def test_run_once_idempotent(self, app, db, monkeypatch):
        """run_once 重复执行幂等: SUCCESS 终态不再扫描/重复建 Artwork"""
        from app.extensions import db as flask_db
        from app.models.artwork import Artwork
        from app.workers.ai_task_worker import AITaskWorker

        tid = _seed_running(app)
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'SUCCESS',
                                                  'result_url': _tencent_url(),
                                                  'error_message': None}))
        with app.app_context():
            worker = AITaskWorker()
            r1 = worker.run_once()
            r2 = worker.run_once()
            assert r1['processed'] == 1
            assert r2['processed'] == 0  # 已 SUCCESS，无 RUNNING 可扫
            assert Artwork.query.count() == 1  # 未重复创建

    def test_worker_run_once_requires_context(self, app, db, monkeypatch):
        """run_once 在 app context 内可执行（不抛错）"""
        monkeypatch.setattr('app.services.ai_task.get_ai_service',
                            lambda: _stub(result={'status': 'RUNNING', 'result_url': None,
                                                  'error_message': None}))
        tid = _seed_running(app)
        from app.workers.ai_task_worker import AITaskWorker
        with app.app_context():
            assert AITaskWorker().run_once()['processed'] == 1