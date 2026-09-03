# ============================================================
# 智绘锡承 - Provider 用量统计 / 启停开关测试（阶段16-C）
# 覆盖:
#   - GET /admin/providers/<id>/usage: 任务聚合 + 成本聚合
#   - 404 / 权限 403
#   - POST /admin/providers/<id>/toggle: 翻转 / 显式 enabled / 审计
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
    _register(client, 'usadmin', 'usadmin@e.com')
    return _login(client, 'usadmin@e.com')


def _seed_usage(app, provider_name, task_type='text_to_3d', provider='hunyuan'):
    """造 provider 配置 + 任务 + 消费流水（描述审计 '<TYPE>:<provider>'）"""
    from app.extensions import db as flask_db
    from app.models.ai_provider import AIProviderConfig
    from app.models.credit import CreditTransaction
    from app.models.user import User

    with app.app_context():
        cfg = AIProviderConfig.query.filter_by(name=provider).first()
        if cfg is None:
            cfg = AIProviderConfig(name=provider, provider_type='3d',
                                   enabled=True, cost_config={})
            flask_db.session.add(cfg)
            flask_db.session.flush()
        u = User.query.filter_by(username='usadmin').first()
        # 任务: 2 SUCCESS + 1 FAILED + 1 RUNNING（RUNNING 需 JobId）
        from app.models.ai_task import AITask
        created = datetime.utcnow() - timedelta(days=1)
        for status in ('SUCCESS', 'SUCCESS', 'FAILED', 'RUNNING'):
            task = AITask(
                user_id=u.id, provider=provider, model='hunyuan-3d',
                task_type=task_type, prompt='紫砂壶', status=status,
                external_task_id='job-x' if status == 'RUNNING' else None,
            )
            task.created_at = created
            task.updated_at = created + timedelta(seconds=60)
            flask_db.session.add(task)
            flask_db.session.flush()
            if status == 'SUCCESS':
                # 每次成功消费 20（模拟 15-B 扣费审计格式）
                flask_db.session.add(CreditTransaction(
                    user_id=u.id, amount=-20, type='AI_GENERATE_3D',
                    description=f'AI_GENERATE_3D:{provider}',
                    reference_id=task.id))
        flask_db.session.commit()
        return cfg.id


class TestProviderUsage:
    """GET /admin/providers/<id>/usage"""

    def test_usage_aggregation(self, client, app, db):
        """任务数/状态分布/成本正确聚合"""
        token = _admin_token(client)
        pid = _seed_usage(app, 'hunyuan')

        r = client.get(f'/admin/providers/{pid}/usage', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['provider']['name'] == 'hunyuan'
        assert d['total_tasks'] == 4
        assert d['status_counts']['SUCCESS'] == 2
        assert d['status_counts']['FAILED'] == 1
        assert d['status_counts']['RUNNING'] == 1
        assert d['status_counts']['PENDING'] == 0
        assert d['success_rate'] == round(2 / 4, 4)
        # 成本: 仅 SUCCESS 2 条 × 20（FAILED/RUNNING 未成功不产生净消费）
        assert d['total_cost'] == 40
        assert d['consume_count'] == 2
        assert d['by_task_type']['text_to_3d'] == 4
        assert d['avg_duration'] == 60.0

    def test_usage_other_provider_not_counted(self, client, app, db):
        """不同 provider 的流水不计入（description 解析隔离）"""
        token = _admin_token(client)
        pid = _seed_usage(app, 'hunyuan')
        # 再加一条 glm 消费
        from app.extensions import db as flask_db
        from app.models.credit import CreditTransaction
        from app.models.user import User
        with app.app_context():
            u = User.query.filter_by(username='usadmin').first()
            flask_db.session.add(CreditTransaction(
                user_id=u.id, amount=-5, type='AI_ANALYZE_STYLE',
                description='AI_ANALYZE_STYLE:glm'))
            flask_db.session.commit()

        r = client.get(f'/admin/providers/{pid}/usage', headers=_auth(token))
        d = r.get_json()['data']
        assert d['total_cost'] == 40  # glm 的 5 不计入 hunyuan
        assert d['consume_count'] == 2

    def test_usage_not_found_404(self, client, app, db):
        token = _admin_token(client)
        r = client.get('/admin/providers/9999/usage', headers=_auth(token))
        assert r.status_code == 404

    def test_usage_permission_403(self, client, app, db):
        _register(client, 'usadmin', 'usadmin@e.com')   # id=1 管理员
        _register(client, 'ususer', 'ususer@e.com')     # id=2 普通
        token = _login(client, 'ususer@e.com')
        r = client.get('/admin/providers/1/usage', headers=_auth(token))
        assert r.status_code == 403


class TestProviderToggle:
    """POST /admin/providers/<id>/toggle"""

    def _create(self, client, token, name='toggle1', ptype='3d'):
        r = client.post('/admin/providers', json={'name': name, 'type': ptype},
                        headers=_auth(token))
        assert r.status_code == 200
        return r.get_json()['data']['id']

    def test_toggle_flips(self, client, app, db):
        token = _admin_token(client)
        pid = self._create(client, token)

        r1 = client.post(f'/admin/providers/{pid}/toggle', headers=_auth(token))
        assert r1.status_code == 200
        d1 = r1.get_json()['data']
        assert d1['old_enabled'] is True
        assert d1['new_enabled'] is False
        assert d1['provider']['enabled'] is False

        # 再翻转 → True
        r2 = client.post(f'/admin/providers/{pid}/toggle', headers=_auth(token))
        assert r2.get_json()['data']['new_enabled'] is True

    def test_toggle_explicit_enabled(self, client, app, db):
        token = _admin_token(client)
        pid = self._create(client, token)

        r = client.post(f'/admin/providers/{pid}/toggle', json={'enabled': False},
                        headers=_auth(token))
        assert r.get_json()['data']['new_enabled'] is False

        # 显式 true
        r2 = client.post(f'/admin/providers/{pid}/toggle', json={'enabled': True},
                         headers=_auth(token))
        assert r2.get_json()['data']['new_enabled'] is True

    def test_toggle_audit_log(self, client, app, db):
        """toggle 写 AdminLog（provider_toggle + 前后状态）"""
        from app.models.admin_log import AdminLog

        token = _admin_token(client)
        pid = self._create(client, token)
        client.post(f'/admin/providers/{pid}/toggle', headers=_auth(token))

        with app.app_context():
            logs = AdminLog.query.filter_by(action='provider_toggle').all()
            assert len(logs) == 1
            import json as _json
            detail = _json.loads(logs[0].detail)
            assert detail['old_enabled'] is True
            assert detail['new_enabled'] is False

    def test_toggle_not_found_404(self, client, app, db):
        token = _admin_token(client)
        r = client.post('/admin/providers/9999/toggle', headers=_auth(token))
        assert r.status_code == 404

    def test_toggle_permission_403(self, client, app, db):
        _register(client, 'usadmin', 'usadmin@e.com')
        _register(client, 'ususer', 'ususer@e.com')
        token = _login(client, 'ususer@e.com')
        r = client.post('/admin/providers/1/toggle', headers=_auth(token))
        assert r.status_code == 403
