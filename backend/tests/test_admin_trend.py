# ============================================================
# 智绘锡承 - AI 趋势分析接口测试（阶段16-B）
# 覆盖: 日期过滤 / day/week/month 分桶 / 空数据 / 权限
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


def _seed(app, user_id, days_ago, status, amount=None, tx_type=None):
    """在 days_ago 天前造一条 AITask（可选同日期消费流水）"""
    from app.extensions import db as flask_db
    from app.models.ai_task import AITask
    from app.models.credit import CreditTransaction

    with app.app_context():
        created = datetime.utcnow() - timedelta(days=days_ago)
        task = AITask(user_id=user_id, provider='hunyuan', model='m',
                      task_type='text_to_3d', prompt='t', status=status)
        flask_db.session.add(task)
        flask_db.session.flush()
        task.created_at = created
        task.updated_at = created + timedelta(seconds=20)
        if amount:
            tx = CreditTransaction(
                user_id=user_id, amount=-amount, type=tx_type or 'AI_GENERATE_3D',
                description='AI_GENERATE_3D:hunyuan', reference_id=task.id)
            tx.created_at = created
            flask_db.session.add(tx)
        flask_db.session.commit()


class TestTrend:
    """趋势分析"""

    def _admin_token(self, client):
        _register(client, 'trd', 'trd@e.com')
        return _login(client, 'trd@e.com')

    def test_trend_day(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={'email': 'trd@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed(app, uid, days_ago=0, status='SUCCESS', amount=20)
        _seed(app, uid, days_ago=0, status='FAILED')
        _seed(app, uid, days_ago=2, status='SUCCESS', amount=5)

        r = client.get('/admin/statistics/trend', headers=_auth(token))
        d = r.get_json()['data']['trend']
        # 3 个日期桶（今天/2 天前）
        assert len(d) == 2
        today = d[0]  # 今天在前（升序按日期：2 天前应在前？升序 → 较早在前）
        # 按升序: days_ago=2 的桶在前
        assert d[0]['total'] == 1 and d[0]['success'] == 1 and d[0]['credits'] == 5
        assert d[1]['total'] == 2 and d[1]['success'] == 1 and d[1]['failed'] == 1
        assert d[1]['credits'] == 20

    def test_trend_group_by_month(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={'email': 'trd@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed(app, uid, days_ago=0, status='SUCCESS')
        _seed(app, uid, days_ago=1, status='FAILED')

        r = client.get('/admin/statistics/trend?group_by=month', headers=_auth(token))
        trend = r.get_json()['data']['trend']
        assert len(trend) == 1  # 同一月聚一桶
        assert trend[0]['total'] == 2
        assert trend[0]['date'].endswith(datetime.utcnow().strftime('-%m'))

    def test_trend_empty(self, client, app):
        token = self._admin_token(client)
        r = client.get('/admin/statistics/trend', headers=_auth(token))
        assert r.status_code == 200
        assert r.get_json()['data']['trend'] == []  # 空数据

    def test_trend_date_filter(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={'email': 'trd@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed(app, uid, days_ago=0, status='SUCCESS')
        _seed(app, uid, days_ago=5, status='FAILED')

        start = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        r = client.get(f'/admin/statistics/trend?start_date={start}', headers=_auth(token))
        trend = r.get_json()['data']['trend']
        assert len(trend) == 1  # 仅今天（5 天前被过滤）

    def test_trend_permission(self, client, app):
        """普通用户 403"""
        _register(client, 'trd1', 'trd1@e.com')
        _login(client, 'trd1@e.com')
        _register(client, 'trd2', 'trd2@e.com')
        token2 = _login(client, 'trd2@e.com')
        r = client.get('/admin/statistics/trend', headers=_auth(token2))
        assert r.status_code == 403

    def test_invalid_group_by_400(self, client, app):
        token = self._admin_token(client)
        r = client.get('/admin/statistics/trend?group_by=hour', headers=_auth(token))
        assert r.status_code == 400