# ============================================================
# 智绘锡承 - 后台统计接口测试（阶段16-A）
# 覆盖: AI 任务统计（含时间范围/by_provider/avg）/ 积分统计 /
#       模型成本分析（description 审计解析）
# ============================================================
from datetime import datetime, timedelta

import pytest

INPUT_URL = '/api/static/uploads/images/ab12cd34_test.png'


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


def _seed_ai_tasks(app, user_id):
    """多种状态/provider 任务 + 时长可控 SUCCESS"""
    from app.extensions import db as flask_db
    from app.models.ai_task import AITask

    with app.app_context():
        specs = [
            ('SUCCESS', 'hunyuan', 'text_to_3d', 100),   # 100s
            ('SUCCESS', 'glm', 'analyze_style', 5),       # 5s
            ('FAILED', 'hunyuan', 'text_to_3d', None),
            ('RUNNING', 'hunyuan', 'text_to_3d', None),
            ('SUCCESS', 'mock', 'text_to_3d', 30),        # 30s
        ]
        base = datetime.utcnow() - timedelta(days=2)
        for status, provider, task_type, dur in specs:
            created = base
            updated = base + timedelta(seconds=dur) if dur is not None else base
            task = AITask(user_id=user_id, provider=provider, model='m',
                          task_type=task_type, prompt='s', status=status,
                          external_task_id='job-x' if status == 'RUNNING' else None)
            task.created_at = created
            task.updated_at = updated
            flask_db.session.add(task)
        flask_db.session.commit()


def _seed_credit_tx(app, user_id, username):
    from app.extensions import db as flask_db
    from app.models.credit import CreditTransaction
    from app.models.user import User

    with app.app_context():
        u = flask_db.session.get(User, user_id)
        if u is None:
            u = User(username=username, email=f'{username}@e.com', password='pass123')
            flask_db.session.add(u)
            flask_db.session.commit()
            user_id = u.id
        txs = [
            # (amount, type, description)
            (-20, 'AI_GENERATE_3D', 'AI_GENERATE_3D:hunyuan'),
            (-20, 'AI_GENERATE_3D', 'AI_GENERATE_3D:hunyuan'),
            (-5, 'AI_ANALYZE_STYLE', 'AI_ANALYZE_STYLE:glm'),
            (100, 'RECHARGE', '注册赠送初始积分 100'),
            (-10, 'AI_GENERATE_3D', 'AI_GENERATE_3D:mock'),
        ]
        for amount, tx_type, desc in txs:
            flask_db.session.add(CreditTransaction(
                user_id=user_id, amount=amount, type=tx_type, description=desc))
        flask_db.session.commit()
        return user_id


class TestAdminAIStat:
    """AI 任务统计"""

    def _admin(self, client):
        _register(client, 'aistat', 'aistat@e.com')
        return _login(client, 'aistat@e.com')

    def test_ai_statistics(self, client, app):
        token = self._admin(client)
        resp = client.post('/auth/login', json={
            'email': 'aistat@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed_ai_tasks(app, uid)

        r = client.get('/admin/statistics/ai', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['total_tasks'] == 5
        assert d['success'] == 3
        assert d['failed'] == 1
        assert d['running'] == 1
        assert d['success_rate'] == round(3 / 5, 4)
        # by_provider
        assert d['by_provider']['hunyuan'] == 3
        assert d['by_provider']['glm'] == 1
        assert d['by_provider']['mock'] == 1
        # avg_duration = (100+5+30)/3
        assert d['avg_duration'] == 45.0

    def test_date_range_filter(self, client, app):
        token = self._admin(client)
        resp = client.post('/auth/login', json={
            'email': 'aistat@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed_ai_tasks(app, uid)

        # 范围设为 3 天前到今天 → 不含（任务在 2 天前）？created=2 天前在范围内
        start = (datetime.utcnow() - timedelta(days=3)).strftime('%Y-%m-%d')
        end = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        r = client.get(f'/admin/statistics/ai?start_date={start}&end_date={end}',
                       headers=_auth(token))
        d = r.get_json()['data']
        assert d['total_tasks'] == 5  # 任务均创建于 2 天前（范围内）
        # 非法日期 → 400
        bad = client.get('/admin/statistics/ai?start_date=2026-13-99', headers=_auth(token))
        assert bad.status_code == 400


class TestAdminCreditStat:
    """积分统计"""

    def test_credit_statistics(self, client, app):
        _register(client, 'crstat', 'crstat@e.com')
        token = _login(client, 'crstat@e.com')
        resp = client.post('/auth/login', json={
            'email': 'crstat@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed_credit_tx(app, uid, 'crstat')

        r = client.get('/admin/statistics/credits', headers=_auth(token))
        d = r.get_json()['data']
        assert d['total_consumed'] == 55      # 20+20+5+10
        # 充值 = 注册赠送 100 + seed RECHARGE 100
        assert d['total_recharged'] == 200
        assert d['today_consumed'] == 55      # 消费均为今天创建
        assert len(d['top_users']) == 1
        top = d['top_users'][0]
        assert top['username'] == 'crstat'
        assert top['consumed'] == 55


class TestAdminModelStat:
    """AI 模型成本分析"""

    def test_model_cost_analysis(self, client, app):
        _register(client, 'mdstat', 'mdstat@e.com')
        token = _login(client, 'mdstat@e.com')
        resp = client.post('/auth/login', json={
            'email': 'mdstat@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        _seed_credit_tx(app, uid, 'mdstat')

        r = client.get('/admin/statistics/models', headers=_auth(token))
        d = r.get_json()['data']
        models = {m['provider']: m for m in d['models']}
        assert models['hunyuan']['total_cost'] == 40   # 2×20
        assert models['hunyuan']['count'] == 2
        assert models['hunyuan']['task_type'] == 'AI_GENERATE_3D'
        assert models['glm']['total_cost'] == 5
        assert models['glm']['count'] == 1
        assert models['glm']['task_type'] == 'AI_ANALYZE_STYLE'
        assert models['mock']['total_cost'] == 10

    def test_model_stat_permission(self, client, app):
        """模型统计: 普通用户 403"""
        _register(client, 'md1', 'md1@e.com')
        _login(client, 'md1@e.com')
        _register(client, 'md2', 'md2@e.com')
        token2 = _login(client, 'md2@e.com')
        r = client.get('/admin/statistics/models', headers=_auth(token2))
        assert r.status_code == 403