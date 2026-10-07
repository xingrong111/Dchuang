# ============================================================
# 智绘锡承 - AI 动态成本测试（阶段16-C）
# 覆盖:
#   - CreditService.get_ai_cost: DB cost_config 优先 / 非法值回退默认 /
#     无记录回退配置 / 表不存在兼容
#   - generate-3d / analyze-style 实际按动态成本扣费（审计 description 不变）
# fixture 显式 AI_PROVIDER=mock（隔离 .env，禁止真实 GLM/腾讯调用）
# ============================================================
import pytest

INPUT_URL = '/api/static/uploads/images/ab12cd34_test.png'


@pytest.fixture
def app(tmp_path):
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    app.config['AI_COST_3D_GENERATE'] = 20
    app.config['AI_COST_STYLE_ANALYZE'] = 5
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


def _register(client, username='cost1', email='cost1@e.com'):
    resp = client.post('/auth/register', json={
        'username': username, 'email': email, 'password': 'password123',
    })
    assert resp.status_code == 200


def _login(client, email='cost1@e.com'):
    resp = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


def _seed_cost(app, name, cost_config):
    """直插 AIProviderConfig（cost_config JSON）"""
    from app.extensions import db as flask_db
    from app.models.ai_provider import AIProviderConfig

    with app.app_context():
        flask_db.session.add(AIProviderConfig(
            name=name, provider_type='3d' if name == 'mock' else 'analysis',
            enabled=True, cost_config=cost_config,
        ))
        flask_db.session.commit()


def _user_balance(app, username):
    from app.models.credit import CreditAccount
    from app.models.user import User

    with app.app_context():
        user = User.query.filter_by(username=username).first()
        return CreditAccount.query.filter_by(user_id=user.id).first().balance


class TestGetAICost:
    """CreditService.get_ai_cost 优先级"""

    def test_no_record_uses_config_defaults(self, app, db):
        from app.services.credit import CreditService

        with app.app_context():
            assert CreditService.get_ai_cost('mock', 'generate_3d') == 20
            assert CreditService.get_ai_cost('mock', 'analyze_style') == 5

    def test_no_record_uses_config_overrides(self, app, db):
        from app.services.credit import CreditService

        app.config['AI_COST_3D_GENERATE'] = 30
        app.config['AI_COST_STYLE_ANALYZE'] = 8
        with app.app_context():
            assert CreditService.get_ai_cost('mock', 'generate_3d') == 30
            assert CreditService.get_ai_cost('mock', 'analyze_style') == 8

    def test_db_cost_config_priority(self, app, db):
        """DB cost_config 优先于配置默认"""
        from app.services.credit import CreditService

        _seed_cost(app, 'mock', {'generate_3d': 35, 'analyze_style': 9})
        with app.app_context():
            assert CreditService.get_ai_cost('mock', 'generate_3d') == 35
            assert CreditService.get_ai_cost('mock', 'analyze_style') == 9

    def test_db_invalid_value_falls_back(self, app, db):
        """cost_config 非正整数/缺键 → 回退配置默认"""
        from app.services.credit import CreditService

        _seed_cost(app, 'mock', {'generate_3d': 0, 'analyze_style': -3})
        with app.app_context():
            assert CreditService.get_ai_cost('mock', 'generate_3d') == 20
            assert CreditService.get_ai_cost('mock', 'analyze_style') == 5

        _seed_cost(app, 'hunyuan', {'generate_3d': 'expensive', 'other': 7})
        with app.app_context():
            # 非 int → 回退；缺 analyze_style 键 → 回退
            assert CreditService.get_ai_cost('hunyuan', 'generate_3d') == 20
            assert CreditService.get_ai_cost('hunyuan', 'analyze_style') == 5

    def test_missing_table_compatible(self, app):
        """ai_providers 表不存在（未迁移）→ 回退配置默认，不抛错"""
        from app.services.credit import CreditService

        with app.app_context():  # 故意不 create_all
            assert CreditService.get_ai_cost('mock', 'generate_3d') == 20
            assert CreditService.get_ai_cost('mock', 'analyze_style') == 5


class TestDynamicCostAPI:
    """API 实际扣费使用动态成本"""

    def test_generate_3d_db_cost(self, client, app, db):
        """generate-3d: DB cost_config=35 → 扣 35，审计 description 不变"""
        from app.models.credit import CreditTransaction

        _register(client)
        token = _login(client)
        _seed_cost(app, 'mock', {'generate_3d': 35, 'analyze_style': 9})

        r = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '紫砂壶',
        }, headers=_auth(token))
        assert r.status_code == 200
        assert _user_balance(app, 'cost1') == 65  # 100 - 35

        with app.app_context():
            from app.models.user import User
            user = User.query.filter_by(username='cost1').first()
            txs = CreditTransaction.query.filter_by(
                user_id=user.id, type='AI_GENERATE_3D').all()
            assert len(txs) == 1
            assert txs[0].amount == -35
            # 审计格式 '<TYPE>:<provider>' 不变（成本统计依赖）
            assert txs[0].description == 'AI_GENERATE_3D:mock'

    def test_analyze_style_db_cost(self, client, app, db):
        """analyze-style: DB cost_config=9 → 扣 9（原 5 硬编码被替代）"""
        from app.models.credit import CreditTransaction

        _register(client, 'cost2', 'cost2@e.com')
        token = _login(client, 'cost2@e.com')
        _seed_cost(app, 'mock', {'generate_3d': 20, 'analyze_style': 9})

        r = client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                        headers=_auth(token))
        assert r.status_code == 200
        assert _user_balance(app, 'cost2') == 91  # 100 - 9

        with app.app_context():
            from app.models.user import User
            user = User.query.filter_by(username='cost2').first()
            txs = CreditTransaction.query.filter_by(
                user_id=user.id, type='AI_ANALYZE_STYLE').all()
            assert len(txs) == 1
            assert txs[0].amount == -9
            assert txs[0].description == 'AI_ANALYZE_STYLE:mock'

    def test_insufficient_402_message_uses_db_cost(self, client, app, db):
        """余额不足提示按动态成本给出（成本=30 → 提示需 30）"""
        _register(client, 'cost3', 'cost3@e.com')
        token = _login(client, 'cost3@e.com')
        _seed_cost(app, 'mock', {'generate_3d': 30})

        with app.app_context():
            from app.models.credit import CreditAccount
            from app.models.user import User
            user = User.query.filter_by(username='cost3').first()
            acct = CreditAccount.query.filter_by(user_id=user.id).first()
            acct.balance = 20  # < 30
            db.session.commit()

        r = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '紫砂壶',
        }, headers=_auth(token))
        assert r.status_code == 402
        assert '30' in r.get_json()['message']
