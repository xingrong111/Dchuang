# ============================================================
# 智绘锡承 - 统一错误响应格式测试（阶段16-D）
# 覆盖: 所有业务错误码 400/401/402/403/404/503 响应体统一为
#   {code, message, data:null}（附 timestamp，与前端 axios 拦截器兼容）
# 通过真实接口触发，验证错误处理器链路而非仅单元构造。
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


def _assert_error_shape(resp, expected_code, keyword=None):
    """统一错误体断言: {code, message, data:null}（timestamp 兼容保留）"""
    assert resp.status_code == expected_code
    body = resp.get_json()
    assert body['code'] == expected_code
    assert isinstance(body['message'], str) and body['message']
    assert body['data'] is None
    if keyword:
        assert keyword in body['message']
    return body


class TestUnifiedErrorBody:
    """400/401/402/403/404/503 → {code, message, data:null}"""

    def test_400_validation_error(self, client):
        """参数校验失败 → 400"""
        # 邮箱格式错误
        resp = client.post('/auth/register', json={
            'username': 'badmail', 'email': 'not-an-email', 'password': 'password123',
        })
        _assert_error_shape(resp, 400, '邮箱')

    def test_401_unauthenticated(self, client):
        """未登录访问受保护接口 → 401"""
        resp = client.get('/user/credits')  # 无 JWT / 无 Session
        _assert_error_shape(resp, 401, '登录')

    def test_402_credit_insufficient(self, client, app):
        """积分不足 → 402"""
        from app.extensions import db as flask_db
        from app.models.credit import CreditAccount
        from app.models.user import User

        _register(client, 'err402', 'err402@e.com')
        token = _login(client, 'err402@e.com')
        with app.app_context():
            user = User.query.filter_by(username='err402').first()
            acct = CreditAccount.query.filter_by(user_id=user.id).first()
            acct.balance = 3  # < 5
            flask_db.session.commit()

        resp = client.post('/ai/analyze-style', json={'input_url': INPUT_URL},
                           headers=_auth(token))
        _assert_error_shape(resp, 402, '积分不足')

    def test_403_permission_denied(self, client):
        """普通用户访问管理接口 → 403"""
        _register(client, 'err403a', 'err403a@e.com')  # id=1 管理员
        _register(client, 'err403b', 'err403b@e.com')  # id=2 普通
        token = _login(client, 'err403b@e.com')
        resp = client.get('/admin/statistics/users', headers=_auth(token))
        _assert_error_shape(resp, 403, '管理员')

    def test_404_resource_not_found(self, client):
        """资源不存在 → 404"""
        resp = client.get('/workshop/works/00000000-0000-0000-0000-000000000000')
        _assert_error_shape(resp, 404, '作品')

    def test_503_ai_service_disabled(self, client, app, db):
        """AI Provider 停用 → 503"""
        from app.extensions import db as flask_db
        from app.models.ai_provider import AIProviderConfig

        _register(client, 'err503', 'err503@e.com')
        token = _login(client, 'err503@e.com')
        with app.app_context():
            flask_db.session.add(AIProviderConfig(
                name='mock', provider_type='3d', enabled=False, cost_config={}))
            flask_db.session.commit()

        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '紫砂壶',
        }, headers=_auth(token))
        _assert_error_shape(resp, 503, '已停用')

    def test_405_method_not_allowed(self, client):
        """路由方法不允许 → 405（Werkzeug 统一 JSON 化）"""
        resp = client.put('/health')
        _assert_error_shape(resp, 405)
