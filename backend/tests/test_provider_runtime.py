# ============================================================
# 智绘锡承 - Provider 运行时启停治理测试（阶段16-C）
# 覆盖:
#   - factory enabled 运行时校验（AIProviderConfig.enabled=False → 停用）
#   - 无配置记录 → 兼容放行（历史 provider 不受影响）
#   - 表不存在（未跑 migration）→ 兼容放行
#   - API 层停用 Provider → 503（generate-3d / analyze-style）
#   - 恢复启用 → 调用恢复
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


def _register(client, username='run1', email='run1@e.com'):
    resp = client.post('/auth/register', json={
        'username': username, 'email': email, 'password': 'password123',
    })
    assert resp.status_code == 200


def _login(client, email='run1@e.com'):
    resp = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


def _seed_provider(app, name, enabled):
    """直插 AIProviderConfig 记录（模拟后台已配置）"""
    from app.extensions import db as flask_db
    from app.models.ai_provider import AIProviderConfig

    with app.app_context():
        flask_db.session.add(AIProviderConfig(
            name=name, provider_type='3d' if name in ('hunyuan', 'mock') else 'analysis',
            enabled=enabled, cost_config={},
        ))
        flask_db.session.commit()


class TestFactoryRuntimeGate:
    """factory 运行时 enabled 校验"""

    def test_enabled_false_blocks(self, app, db):
        """记录存在且 enabled=False → get_ai_service 抛 AIServiceError"""
        from app.services.factory import get_ai_service
        from app.utils.exceptions import AIServiceError

        _seed_provider(app, 'mock', enabled=False)
        with app.app_context():
            with pytest.raises(AIServiceError) as exc:
                get_ai_service('mock')
            assert '已停用' in str(exc.value)

    def test_enabled_true_allows(self, app, db):
        """记录存在且 enabled=True → 正常返回"""
        from app.services.factory import get_ai_service
        from app.services.mock import MockProvider

        _seed_provider(app, 'mock', enabled=True)
        with app.app_context():
            service = get_ai_service('mock')
            assert isinstance(service, MockProvider)

    def test_no_record_compatible(self, app, db):
        """无记录 → 兼容放行（历史 provider 不受影响）"""
        from app.services.factory import get_ai_service
        from app.services.mock import MockProvider

        with app.app_context():
            service = get_ai_service('mock')
            assert isinstance(service, MockProvider)

    def test_missing_table_compatible(self, app):
        """ai_providers 表不存在（旧库未迁移）→ 兼容放行，不抛错"""
        from app.services.factory import get_ai_service
        from app.services.mock import MockProvider

        # 注意: 本测试故意不 create_all（无 ai_providers 表）
        with app.app_context():
            service = get_ai_service('mock')
            assert isinstance(service, MockProvider)

    def test_default_provider_uses_config(self, app, db):
        """默认走 AI_PROVIDER 配置且同样受 enabled 治理"""
        from app.services.factory import get_ai_service
        from app.utils.exceptions import AIServiceError

        app.config['AI_PROVIDER'] = 'mock'
        _seed_provider(app, 'mock', enabled=False)
        with app.app_context():
            with pytest.raises(AIServiceError):
                get_ai_service()  # 未显式指定 → 用配置 AI_PROVIDER=mock → 停用


class TestAPIRuntimeGate:
    """API 层停用治理"""

    def test_generate_3d_disabled_503(self, client, app, db):
        """Provider 停用 → generate-3d 返回 503 且不扣积分"""
        from app.models.credit import CreditAccount

        _register(client)
        token = _login(client)
        _seed_provider(app, 'mock', enabled=False)

        r = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成一把紫砂壶',
        }, headers=_auth(token))
        assert r.status_code == 503
        assert '已停用' in r.get_json()['message']

        # 未扣费（余额仍 100）
        with app.app_context():
            from app.models.user import User
            user = User.query.filter_by(username='run1').first()
            assert CreditAccount.query.filter_by(user_id=user.id).first().balance == 100

    def test_generate_3d_reenabled_succeeds(self, client, app, db):
        """恢复启用 → generate-3d 正常（200 + 扣费）"""
        from app.models.ai_provider import AIProviderConfig

        _register(client, 'run2', 'run2@e.com')
        token = _login(client, 'run2@e.com')
        _seed_provider(app, 'mock', enabled=False)

        r1 = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '紫砂壶',
        }, headers=_auth(token))
        assert r1.status_code == 503

        # 后台恢复启用
        with app.app_context():
            cfg = AIProviderConfig.query.filter_by(name='mock').first()
            cfg.enabled = True
            db.session.commit()

        r2 = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '紫砂壶',
        }, headers=_auth(token))
        assert r2.status_code == 200
        assert r2.get_json()['data']['status'] == 'SUCCESS'

    def test_analyze_style_disabled_503(self, client, app, db):
        """analyze-style 同样受 enabled 治理（503）"""
        _register(client, 'run3', 'run3@e.com')
        token = _login(client, 'run3@e.com')
        _seed_provider(app, 'mock', enabled=False)

        r = client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                        headers=_auth(token))
        assert r.status_code == 503
        assert '已停用' in r.get_json()['message']

    def test_no_record_api_compatible(self, client, app, db):
        """无 Provider 配置记录 → API 正常调用（历史兼容）"""
        _register(client, 'run4', 'run4@e.com')
        token = _login(client, 'run4@e.com')

        r = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '紫砂壶',
        }, headers=_auth(token))
        assert r.status_code == 200
