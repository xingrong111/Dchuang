# ============================================================
# 智绘锡承 - Provider 运行状态测试（阶段16-D）
# 覆盖: GET /admin/providers/status
#   - 配置 + 任务聚合: enabled / running_tasks / last_used_at
#   - 无配置记录的历史 provider → enabled=True（兼容）
#   - 空库 → 空列表
#   - 权限 403
# fixture 显式 AI_PROVIDER=mock + ADMIN_USER_IDS=1（隔离 .env 真实调用）
# ============================================================
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def app(tmp_path):
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    app.config['ADMIN_USER_IDS'] = '1'
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


def _admin_token(client):
    """注册第一个用户 = 管理员（id=1，ADMIN_USER_IDS=1）"""
    _register(client, 'stadmin', 'stadmin@e.com')
    return _login(client, 'stadmin@e.com')


def _seed(app, user_id):
    """配置: hunyuan(enabled=True) / glm(enabled=False)；任务: hunyuan RUNNING×2+SUCCESS / glm FAILED"""
    from app.extensions import db as flask_db
    from app.models.ai_provider import AIProviderConfig
    from app.models.ai_task import AITask

    with app.app_context():
        flask_db.session.add(AIProviderConfig(
            name='hunyuan', provider_type='3d', enabled=True, cost_config={}))
        flask_db.session.add(AIProviderConfig(
            name='glm', provider_type='analysis', enabled=False, cost_config={}))
        base = datetime.utcnow() - timedelta(days=1)
        specs = [
            ('RUNNING', 'hunyuan', base + timedelta(hours=1)),   # 最近更新
            ('RUNNING', 'hunyuan', base + timedelta(hours=2)),
            ('SUCCESS', 'hunyuan', base),
            ('FAILED', 'glm', base),
        ]
        for status, provider, updated in specs:
            task = AITask(user_id=user_id, provider=provider, model='m',
                          task_type='text_to_3d', prompt='s', status=status,
                          external_task_id='job-x' if status == 'RUNNING' else None)
            task.updated_at = updated
            flask_db.session.add(task)
        flask_db.session.commit()


class TestProviderStatus:
    """GET /admin/providers/status"""

    def _status_map(self, client, token):
        r = client.get('/admin/providers/status', headers=_auth(token))
        assert r.status_code == 200
        return {item['provider']: item
                for item in r.get_json()['data']['providers']}

    def test_status_aggregation(self, client, app, db):
        """enabled / running_tasks / last_used_at 正确聚合"""
        token = _admin_token(client)
        resp = client.post('/auth/login', json={
            'email': 'stadmin@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed(app, uid)

        by = self._status_map(client, token)
        # 配置 + 任务都出现；按名升序返回
        names = list(by.keys())
        assert names == sorted(names)
        assert set(by) >= {'hunyuan', 'glm'}

        hunyuan = by['hunyuan']
        assert hunyuan['enabled'] is True
        assert hunyuan['running_tasks'] == 2
        assert hunyuan['last_used_at']  # 非空（最近更新存在）

        glm = by['glm']
        assert glm['enabled'] is False       # 配置记录 enabled=False
        assert glm['running_tasks'] == 0
        assert glm['last_used_at']           # 有 FAILED 任务 → 有更新时间

    def test_historical_provider_default_enabled(self, client, app, db):
        """无配置记录的历史 provider → enabled=True（兼容未治理）"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask
        from app.models.user import User

        token = _admin_token(client)
        with app.app_context():
            u = User.query.filter_by(username='stadmin').first()
            flask_db.session.add(AITask(user_id=u.id, provider='mock', model='m',
                                        task_type='text_to_3d', prompt='s',
                                        status='SUCCESS'))
            flask_db.session.commit()

        by = self._status_map(client, token)
        assert by['mock']['enabled'] is True
        assert by['mock']['running_tasks'] == 0
        assert by['mock']['last_used_at'] is not None

    def test_empty_db_returns_empty(self, client, app, db):
        """无配置无任务 → 空列表"""
        token = _admin_token(client)
        r = client.get('/admin/providers/status', headers=_auth(token))
        assert r.status_code == 200
        assert r.get_json()['data']['providers'] == []

    def test_permission_403(self, client, app, db):
        _register(client, 'stadmin', 'stadmin@e.com')
        _register(client, 'stuser', 'stuser@e.com')
        token = _login(client, 'stuser@e.com')
        r = client.get('/admin/providers/status', headers=_auth(token))
        assert r.status_code == 403
