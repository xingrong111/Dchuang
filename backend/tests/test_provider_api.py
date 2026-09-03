# ============================================================
# 智绘锡承 - Provider 运营管理测试（阶段16-B）
# 覆盖: 创建/修改/删除/使用中禁止删除/权限/审计日志生成
# ============================================================
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


class TestProviderAPI:
    """Provider CRUD"""

    def _admin_token(self, client):
        _register(client, 'prov', 'prov@e.com')
        return _login(client, 'prov@e.com')

    def test_create_list_update_delete(self, client):
        """创建 → 列表 → 修改 enabled → 删除"""
        token = self._admin_token(client)

        r = client.post('/admin/providers', json={'name': 'hunyuan', 'type': '3d'},
                        headers=_auth(token))
        assert r.status_code == 200
        pid = r.get_json()['data']['id']

        # 列表
        lst = client.get('/admin/providers', headers=_auth(token))
        items = lst.get_json()['data']['providers']
        assert len(items) == 1
        assert items[0]['name'] == 'hunyuan'
        assert items[0]['enabled'] is True
        assert items[0]['type'] == '3d'

        # 修改 enabled=false
        up = client.put(f'/admin/providers/{pid}', json={'enabled': False},
                        headers=_auth(token))
        assert up.status_code == 200
        assert up.get_json()['data']['enabled'] is False

        # 删除（无任务记录）
        dl = client.delete(f'/admin/providers/{pid}', headers=_auth(token))
        assert dl.status_code == 200
        lst2 = client.get('/admin/providers', headers=_auth(token))
        assert lst2.get_json()['data']['providers'] == []

    def test_duplicate_name_400(self, client):
        token = self._admin_token(client)
        client.post('/admin/providers', json={'name': 'glm', 'type': 'analysis'},
                    headers=_auth(token))
        r2 = client.post('/admin/providers', json={'name': 'glm', 'type': 'analysis'},
                         headers=_auth(token))
        assert r2.status_code == 400

    def test_invalid_type_400(self, client):
        token = self._admin_token(client)
        r = client.post('/admin/providers', json={'name': 'x', 'type': 'video'},
                        headers=_auth(token))
        assert r.status_code == 400

    def test_delete_provider_in_use_400(self, client, app):
        """存在任务记录时禁止删除 → 400"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        token = self._admin_token(client)
        r = client.post('/admin/providers', json={'name': 'mock', 'type': '3d'},
                        headers=_auth(token))
        pid = r.get_json()['data']['id']

        # 造一条 provider=mock 的任务
        with app.app_context():
            from app.models.user import User
            u = User.query.filter_by(username='prov').first()
            flask_db.session.add(AITask(user_id=u.id, provider='mock', model='m',
                                        task_type='text_to_3d', prompt='x',
                                        status='SUCCESS'))
            flask_db.session.commit()

        dl = client.delete(f'/admin/providers/{pid}', headers=_auth(token))
        assert dl.status_code == 400
        assert '禁止删除' in dl.get_json()['message']

    def test_permission(self, client):
        """非管理员 403"""
        _register(client, 'prov1', 'prov1@e.com')
        _login(client, 'prov1@e.com')
        _register(client, 'prov2', 'prov2@e.com')
        token2 = _login(client, 'prov2@e.com')
        r = client.get('/admin/providers', headers=_auth(token2))
        assert r.status_code == 403

    def test_audit_log_generated(self, client, app):
        """创建/更新/删除均写 AdminLog"""
        from app.models.admin_log import AdminLog

        token = self._admin_token(client)
        r = client.post('/admin/providers', json={'name': 'hunyuan2', 'type': '3d'},
                        headers=_auth(token))
        pid = r.get_json()['data']['id']
        client.put(f'/admin/providers/{pid}', json={'enabled': False}, headers=_auth(token))
        with app.app_context():
            actions = [log.action for log in AdminLog.query.order_by(AdminLog.id).all()]
            assert 'provider_create' in actions
            assert 'provider_update' in actions