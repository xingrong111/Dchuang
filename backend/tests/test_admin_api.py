# ============================================================
# 智绘锡承 - 后台管理 API 测试（阶段16-A）
# 覆盖: 权限（401/403/管理员）/ 用户统计 / 任务列表/详情 /
#       管理员强制重试 / AdminLog 审计生成
# 权限方案: 配置式 ADMIN_USER_IDS（首注册用户 id=1 作为管理员）
# ============================================================
import pytest

INPUT_URL = '/api/static/uploads/images/ab12cd34_test.png'


@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录 + Mock Provider）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    app.config['ADMIN_USER_IDS'] = '1'  # 首注册用户（id=1）为管理员
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


def _register(client, username, email):
    resp = client.post('/auth/register', json={
        'username': username, 'email': email, 'password': 'password123',
    })
    assert resp.status_code == 200


def _login(client, email):
    resp = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


class TestAdminPermission:
    """权限: 未登录 401 / 普通用户 403 / 管理员 200"""

    def test_no_auth_401(self, client):
        r = client.get('/admin/statistics/users')
        assert r.status_code == 401

    def test_normal_user_403(self, client):
        """普通用户（非 ADMIN_USER_IDS）→ 403"""
        _register(client, 'normu', 'normu@e.com')
        token = _login(client, 'normu@e.com')  # id=1 是管理员！
        # 需再注册普通用户（id=2）作为非管理员
        _register(client, 'normu2', 'normu2@e.com')
        token2 = _login(client, 'normu2@e.com')
        r = client.get('/admin/statistics/users', headers=_auth(token2))
        assert r.status_code == 403
        assert r.get_json()['code'] == 403

    def test_admin_success(self, client):
        _register(client, 'admin1', 'admin1@e.com')
        token = _login(client, 'admin1@e.com')
        r = client.get('/admin/statistics/users', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['total_users'] == 1
        assert d['active_users'] == 1
        assert d['new_users_today'] >= 1


class TestAdminUsersStat:
    """用户统计"""

    def test_counts(self, client):
        _register(client, 'adma', 'adma@e.com')
        token = _login(client, 'adma@e.com')
        _register(client, 'admb', 'admb@e.com')
        _login(client, 'admb@e.com')
        r = client.get('/admin/statistics/users', headers=_auth(token))
        d = r.get_json()['data']
        assert d['total_users'] == 2
        assert d['active_users'] == 2


class TestAdminTaskMgmt:
    """任务列表/详情/强制重试"""

    def _seed_tasks(self, app, user_id):
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        with app.app_context():
            for i, status in enumerate(['SUCCESS', 'FAILED', 'RUNNING']):
                task = AITask(user_id=user_id, provider='mock', model='mock-3d',
                              task_type='text_to_3d', prompt=f'任务{i}',
                              status=status, external_task_id=f'job-{i}' if status == 'RUNNING' else None)
                flask_db.session.add(task)
            flask_db.session.commit()

    def _admin_token(self, client):
        _register(client, 'admt', 'admt@e.com')
        return _login(client, 'admt@e.com')

    def test_list_filter_status(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={'email': 'admt@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        self._seed_tasks(app, uid)

        r = client.get('/admin/tasks?status=FAILED', headers=_auth(token))
        assert r.status_code == 200
        items = r.get_json()['data']
        assert len(items) == 1
        assert items[0]['status'] == 'FAILED'
        assert 'user' in items[0]  # 附用户摘要
        assert items[0]['user']['username'] == 'admt'

    def test_detail_aggregated(self, client, app):
        """详情聚合 task+user+credit+artwork"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        token = self._admin_token(client)
        resp = client.post('/auth/login', json={'email': 'admt@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        # 管理员造一个消费过积分的任务（管理员自己 generate）
        g = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '详情任务',
        }, headers=_auth(token))
        task_id = g.get_json()['data']['id']

        r = client.get(f'/admin/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['user']['username'] == 'admt'
        assert d['artwork'] is not None  # SUCCESS 建 Artwork
        assert len(d['credit_transactions']) >= 1  # 扣费流水

    def test_admin_retry_any_user(self, client, app, monkeypatch):
        """管理员强制重试普通用户 FAILED 任务 → 新任务 + AdminLog + 旧任务保留"""
        from app.extensions import db as flask_db
        from app.models.admin_log import AdminLog
        from app.models.ai_task import AITask

        # 管理员先注册（id=1 为 ADMIN_USER_IDS 中管理员）
        _register(client, 'boss', 'boss@e.com')
        token = _login(client, 'boss@e.com')

        # 普通用户（id=2）注册
        _register(client, 'victim', 'victim@e.com')
        vlogin = client.post('/auth/login', json={
            'email': 'victim@e.com', 'password': 'password123'})
        vid = vlogin.get_json()['data']['id']

        # victim 生成失败任务（mock fail 注入）
        from app.services.mock import MockProvider
        monkeypatch.setattr('app.api.v1.ai.get_ai_service',
                            lambda: MockProvider(mock_behavior='fail'))
        vtoken = _login(client, 'victim@e.com')
        fail = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '受害任务',
        }, headers=_auth(vtoken))
        old_id = fail.get_json()['data']['id']
        assert fail.get_json()['data']['status'] == 'FAILED'
        monkeypatch.undo()  # 恢复 mock success 使重试成功

        # 管理员强制重试（任意用户）
        r = client.post(f'/admin/tasks/{old_id}/retry', headers=_auth(token))
        assert r.status_code == 200
        data = r.get_json()['data']
        assert data['new_task']['status'] == 'SUCCESS'  # 重试成功（mock success）
        assert data['old_task']['id'] == old_id  # 旧任务保留
        new_task_id = data['new_task']['id']
        assert new_task_id != old_id

        with app.app_context():
            assert flask_db.session.get(AITask, old_id).status == 'FAILED'  # 未删未改
            new_task = flask_db.session.get(AITask, new_task_id)
            assert new_task.user_id == vid  # 仍属原用户
            logs = AdminLog.query.filter_by(action='task_retry', target_id=old_id).all()
            assert len(logs) == 1  # 审计日志生成
            assert logs[0].admin_user_id == 1
            assert 'new_task_id' in logs[0].detail

    def test_admin_retry_running_allowed(self, client, app):
        """管理员可重试 RUNNING 任务（普通用户不可）；PENDING/SUCCESS 拒绝"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        # 管理员先注册（id=1）
        _register(client, 'rva', 'rva@e.com')
        token = _login(client, 'rva@e.com')
        # 普通用户（id=2）
        _register(client, 'ruser', 'ruser@e.com')
        rlogin = client.post('/auth/login', json={'email': 'ruser@e.com', 'password': 'password123'})
        ruid = rlogin.get_json()['data']['id']

        with app.app_context():
            running = AITask(user_id=ruid, provider='mock', model='mock-3d',
                             task_type='text_to_3d', prompt='r', status='RUNNING',
                             external_task_id='job-r')
            done = AITask(user_id=ruid, provider='mock', model='mock-3d',
                          task_type='text_to_3d', prompt='d', status='SUCCESS')
            flask_db.session.add_all([running, done])
            flask_db.session.commit()
            running_id = running.id
            done_id = done.id

        r_ok = client.post(f'/admin/tasks/{running_id}/retry', headers=_auth(token))
        assert r_ok.status_code == 200  # RUNNING 允许强制重试
        r_bad = client.post(f'/admin/tasks/{done_id}/retry', headers=_auth(token))
        assert r_bad.status_code == 400  # SUCCESS 拒绝