# ============================================================
# 智绘锡承 - analyze-style 积分流测试（阶段15-D）
# 覆盖: 成功扣 5 / 失败退款 / 余额不足 402 / 不重复扣费 / generate-3d 不受影响
# fixture 显式 AI_PROVIDER=mock（隔离 .env，禁止真实 GLM/腾讯调用）
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
    app.config['AI_COST_3D_GENERATE'] = 20
    app.config['AI_COST_STYLE_ANALYZE'] = 5
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


def _register(client, username='flow1', email='flow1@e.com'):
    resp = client.post('/auth/register', json={
        'username': username, 'email': email, 'password': 'password123',
    })
    assert resp.status_code == 200


def _login(client, email='flow1@e.com'):
    resp = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


class TestAnalyzeStyleCredit:
    """analyze-style 积分流"""

    def test_success_deducts_5(self, client):
        """风格分析成功 → 扣 5 积分 + AI_ANALYZE_STYLE 流水（审计 description 含 provider）"""
        _register(client)
        token = _login(client)

        resp = client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                           headers=_auth(token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['task']['status'] == 'SUCCESS'

        r = client.get('/user/credits', headers=_auth(token))
        d = r.get_json()['data']
        assert d['balance'] == 95  # 100 - 5
        consume_tx = [t for t in d['transactions'] if t['type'] == 'AI_ANALYZE_STYLE']
        assert len(consume_tx) == 1
        assert consume_tx[0]['amount'] == -5
        # 审计格式 '<TYPE>:<provider>'（mock provider）
        assert consume_tx[0]['description'] == 'AI_ANALYZE_STYLE:mock'

    def test_failure_refunds(self, client, app, monkeypatch):
        """分析失败（mock fail）→ 自动退款，余额恢复 100"""
        from app.services.mock import MockProvider

        monkeypatch.setattr('app.api.v1.ai.get_ai_service',
                            lambda: MockProvider(mock_behavior='fail'))
        _register(client, 'flow2', 'flow2@e.com')
        token = _login(client, 'flow2@e.com')

        resp = client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                           headers=_auth(token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['task']['status'] == 'FAILED'

        r = client.get('/user/credits', headers=_auth(token))
        d = r.get_json()['data']
        assert d['balance'] == 100  # 扣 5 后退回
        types = [t['type'] for t in d['transactions']]
        assert 'AI_ANALYZE_STYLE' in types
        assert 'REFUND' in types

    def test_insufficient_402_no_task(self, client, app):
        """余额不足 → 402 + 不创建任务"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask
        from app.models.credit import CreditAccount

        _register(client, 'flow3', 'flow3@e.com')
        token = _login(client, 'flow3@e.com')
        with app.app_context():
            from app.models.user import User
            user = User.query.filter_by(username='flow3').first()
            acct = CreditAccount.query.filter_by(user_id=user.id).first()
            acct.balance = 3  # < 5
            flask_db.session.commit()

        resp = client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                           headers=_auth(token))
        assert resp.status_code == 402
        assert '积分不足' in resp.get_json()['message']
        with app.app_context():
            assert AITask.query.count() == 0

    def test_no_double_charge_per_task(self, client, app):
        """同任务 reference 不重复扣费: 一次分析恰好 1 条消费流水"""
        from app.models.credit import CreditTransaction

        _register(client, 'flow4', 'flow4@e.com')
        token = _login(client, 'flow4@e.com')
        resp = client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                           headers=_auth(token))
        task_id = resp.get_json()['data']['task']['id']

        with app.app_context():
            from app.models.user import User
            user = User.query.filter_by(username='flow4').first()
            txs = (CreditTransaction.query
                   .filter_by(user_id=user.id, type='AI_ANALYZE_STYLE',
                              reference_id=task_id)
                   .all())
            assert len(txs) == 1  # 恰好一条（幂等）

    def test_generate_3d_unaffected(self, client):
        """generate-3d 流程不受影响（仍扣 20，独立于 style 消费）"""
        _register(client, 'flow5', 'flow5@e.com')
        token = _login(client, 'flow5@e.com')

        client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                    headers=_auth(token))
        g = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成紫砂壶',
        }, headers=_auth(token))
        assert g.status_code == 200

        r = client.get('/user/credits', headers=_auth(token))
        assert r.get_json()['data']['balance'] == 75  # 100 - 5 - 20
        types = [t['type'] for t in r.get_json()['data']['transactions']]
        assert 'AI_ANALYZE_STYLE' in types
        assert 'AI_GENERATE_3D' in types