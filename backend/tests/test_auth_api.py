# ============================================================
# 智绘锡承 - 用户认证 API 测试（阶段3 JWT）
# 覆盖: 注册 / 登录 / 当前用户 / 安全（password_hash 不外泄）
# ============================================================
import pytest


@pytest.fixture
def app():
    """创建测试应用（SQLite 内存库，无需 MySQL）"""
    from app import create_app

    app = create_app('testing')
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
    """测试客户端（含已建表）"""
    return app.test_client()


def _register(client, username='testuser', email='test@example.com', password='password123'):
    """辅助：发起注册请求"""
    return client.post('/auth/register', json={
        'username': username,
        'email': email,
        'password': password,
    })


def _login(client, email='test@example.com', password='password123'):
    """辅助：发起登录请求"""
    return client.post('/auth/login', json={
        'email': email,
        'password': password,
    })


def _create_user(app, db, username='testuser', email='test@example.com',
                 password='password123', is_active=True):
    """辅助：直接创建用户（绕过 API）"""
    from app.models.user import User

    with app.app_context():
        user = User(username=username, email=email, password=password)
        user.is_active = is_active
        db.session.add(user)
        db.session.commit()
        return user


class TestRegister:
    """POST /auth/register"""

    def test_register_success(self, client):
        """正常注册"""
        resp = _register(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert data['message'] == '注册成功'
        assert data['data']['username'] == 'testuser'
        assert data['data']['email'] == 'test@example.com'
        # 不自动登录：注册响应不返回 token
        assert 'token' not in data['data']

    def test_register_missing_fields(self, client):
        """缺少字段（username/email/password）"""
        resp = client.post('/auth/register', json={'username': 'onlyname'})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['code'] == 400
        assert data['data'] is None

    def test_register_invalid_email(self, client):
        """非法 email"""
        resp = _register(client, email='not-an-email')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['code'] == 400
        assert '邮箱' in data['message']

    def test_register_short_password(self, client):
        """密码过短（< 6 位）"""
        resp = _register(client, password='123')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['code'] == 400
        assert '密码' in data['message']

    def test_register_duplicate_username(self, client, app, db):
        """重复 username"""
        _create_user(app, db, username='testuser', email='other@example.com')
        resp = _register(client)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['code'] == 400
        assert '已存在' in data['message']

    def test_register_duplicate_email(self, client, app, db):
        """重复 email"""
        _create_user(app, db, username='otheruser', email='test@example.com')
        resp = _register(client)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['code'] == 400
        assert '已存在' in data['message']

    def test_register_creates_profile(self, client, app, db):
        """注册同时创建 UserProfile"""
        _register(client)
        from app.models.user import User, UserProfile

        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            assert user is not None
            assert user.profile is not None
            assert isinstance(user.profile, UserProfile)
            assert user.profile.user_id == user.id


class TestLogin:
    """POST /auth/login"""

    def test_login_success(self, client, app, db):
        """正确登录"""
        _create_user(app, db)
        resp = _login(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert data['message'] == '登录成功'
        # Token 必须位于 data.token（前端 userStore 契约）
        assert 'token' in data['data']
        assert data['data']['token']
        assert data['data']['username'] == 'testuser'
        assert data['data']['email'] == 'test@example.com'

    def test_login_wrong_password(self, client, app, db):
        """错误密码"""
        _create_user(app, db)
        resp = _login(client, password='wrongpass123')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None

    def test_login_user_not_found(self, client, db):
        """不存在的用户"""
        resp = _login(client)
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401

    def test_login_disabled_user(self, client, app, db):
        """禁用用户拒绝登录"""
        _create_user(app, db, is_active=False)
        resp = _login(client)
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert '禁用' in data['message']

    def test_login_response_has_token_field(self, client, app, db):
        """登录响应存在 data.token"""
        _create_user(app, db)
        resp = _login(client)
        data = resp.get_json()
        assert 'token' in data['data']

    def test_login_response_no_password_hash(self, client, app, db):
        """登录响应没有 password_hash"""
        _create_user(app, db)
        resp = _login(client)
        body = resp.get_data(as_text=True)
        assert 'password_hash' not in body
        assert '"password"' not in body.replace('password_hash', '')


class TestCurrentUser:
    """GET /auth/user"""

    def _login_get_token(self, client, app, db):
        _create_user(app, db)
        resp = _login(client)
        return resp.get_json()['data']['token']

    def test_get_user_with_valid_token(self, client, app, db):
        """有效 Token 获取用户"""
        token = self._login_get_token(client, app, db)
        resp = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert data['data']['id'] == 1
        assert data['data']['username'] == 'testuser'
        assert data['data']['email'] == 'test@example.com'
        assert 'avatar' in data['data']
        assert 'bio' in data['data']

    def test_get_user_no_token(self, client):
        """无 Token"""
        resp = client.get('/auth/user')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None

    def test_get_user_invalid_token(self, client):
        """无效 Token"""
        resp = client.get('/auth/user', headers={'Authorization': 'Bearer invalid.token.here'})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401

    def test_get_user_token_valid_but_user_missing(self, app, client, db):
        """Token 有效但用户不存在（用户被删除）"""
        from app.models.user import User

        token = self._login_get_token(client, app, db)
        # 删除用户
        with app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            db.session.delete(user)
            db.session.commit()

        resp = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401


class TestSecurity:
    """安全：任何用户接口不泄露密码信息"""

    def test_no_password_hash_in_any_user_response(self, client, app, db):
        """注册/登录/用户信息响应均不出现 password / password_hash"""
        # 注册响应
        resp_reg = _register(client)
        assert 'password_hash' not in resp_reg.get_data(as_text=True)
        # 登录响应（用户刚注册，直接登录）
        resp_login = _login(client)
        assert resp_login.status_code == 200
        body = resp_login.get_data(as_text=True)
        assert 'password_hash' not in body
        # 用户信息响应
        token = resp_login.get_json()['data']['token']
        resp_user = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert 'password_hash' not in resp_user.get_data(as_text=True)
