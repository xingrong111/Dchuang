# ============================================================
# 智绘锡承 - JWT + Session 双认证兼容测试（阶段5.1）
# 覆盖: 登录建立 Session / JWT 上传 / Session 上传 /
#       未认证 401 / 身份伪造 / JWT 优先级 / 无效 JWT / 过期 JWT
# ============================================================
import io
from datetime import timedelta

import pytest


@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
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


def _png():
    """最小合法 PNG（带魔数）"""
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
        b'\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def _register(client, username, email):
    """辅助：注册"""
    resp = client.post('/auth/register', json={
        'username': username,
        'email': email,
        'password': 'password123',
    })
    assert resp.status_code == 200


def _login(client, email, password='password123'):
    """辅助：登录，返回响应（保留 Session Cookie 于测试客户端）"""
    return client.post('/auth/login', json={'email': email, 'password': password})


def _get_token(client, email, password='password123'):
    """辅助：登录并返回 JWT"""
    resp = _login(client, email, password)
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _upload_avatar(client, content=None, filename='a.png', headers=None):
    """辅助：上传头像（不传 Authorization 默认走 Session）"""
    return client.post(
        '/user/upload-avatar',
        data={'file': (io.BytesIO(content or _png()), filename)},
        content_type='multipart/form-data',
        headers=headers or {},
    )


class TestLoginSession:
    """A. 登录 Session 测试"""

    def test_login_sets_session_cookie(self, client):
        """登录成功: 200 + data.token 存在 + Session Cookie 被设置"""
        _register(client, 'sessuser', 'sess@example.com')
        resp = _login(client, 'sess@example.com')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert 'token' in data['data']  # JWT 契约不变
        # Session Cookie 已设置（Flask test client 自动保存）
        with client.session_transaction() as sess:
            assert 'user_id' in sess
            assert isinstance(sess['user_id'], int)

    def test_login_token_contract_unchanged(self, client):
        """登录 data.token 位置不变（前端 userStore 契约）"""
        _register(client, 'tokuser', 'tok@example.com')
        resp = _login(client, 'tok@example.com')
        data = resp.get_json()
        assert 'token' in data['data']
        assert 'access_token' not in data['data']


class TestAvatarJWT:
    """B. JWT 头像上传"""

    def test_jwt_user_upload_avatar(self, client, app, db):
        """Bearer JWT 上传头像 → 200 + avatar 更新 + data.url"""
        _register(client, 'jwtu', 'jwt@example.com')
        token = _get_token(client, 'jwt@example.com')
        resp = _upload_avatar(client, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert 'url' in data['data']
        assert data['data']['url'].startswith('/api/static/uploads/avatars/')

        me = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert me.get_json()['data']['avatar'] == data['data']['url']


class TestAvatarSession:
    """C. Session 头像上传（本阶段最关键）"""

    def test_session_upload_avatar(self, client, app, db):
        """登录后（Session Cookie 自动保存），不传 Authorization 上传头像 → 200 + 正确更新"""
        _register(client, 'sessup', 'sessup@example.com')
        _login(client, 'sessup@example.com')  # Session Cookie 保存在 test client

        resp = _upload_avatar(client)  # 无 Authorization 头
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert 'url' in data['data']

        # 验证更新到 Session 对应用户（用 JWT 查证）
        token = _get_token(client, 'sessup@example.com')
        me = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert me.get_json()['data']['avatar'] == data['data']['url']


class TestUnauthenticated:
    """D. 未认证上传"""

    def test_upload_avatar_no_auth_401(self, client):
        """无 JWT + 无 Session → 401 统一 JSON"""
        resp = _upload_avatar(client)
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None


class TestIdentityForgery:
    """E. 客户端身份伪造"""

    def test_session_upload_ignores_client_user_field(self, client, app, db):
        """Session 用户上传时伪造 user_id/username → 更新仍是 Session 对应用户"""
        _register(client, 'realuser', 'real@example.com')
        _login(client, 'real@example.com')

        resp = client.post(
            '/user/upload-avatar',
            data={
                'file': (io.BytesIO(_png()), 'x.png'),
                'user_id': '999999',
                'username': 'hacker',
            },
            content_type='multipart/form-data',
        )
        assert resp.status_code == 200
        url = resp.get_json()['data']['url']

        # 真实用户（realuser）头像被更新，伪造字段未生效
        token = _get_token(client, 'real@example.com')
        me = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert me.get_json()['data']['avatar'] == url
        assert me.get_json()['data']['username'] == 'realuser'


class TestJWTPriority:
    """F. JWT 优先级"""

    def test_jwt_priority_over_session(self, client, app, db):
        """Session(User A) + JWT(User B) 同时存在 → 更新 User B"""
        # User A: 通过 Session 登录
        _register(client, 'usera', 'a@example.com')
        _login(client, 'a@example.com')  # Session → User A

        # User B: 通过 JWT（同一 client 上额外带 Bearer）
        _register(client, 'userb', 'b@example.com')
        token_b = _get_token(client, 'b@example.com')

        resp = _upload_avatar(client, headers={'Authorization': f'Bearer {token_b}'})
        assert resp.status_code == 200
        url = resp.get_json()['data']['url']

        # User B 头像被更新（JWT 优先）
        me_b = client.get('/auth/user', headers={'Authorization': f'Bearer {token_b}'})
        assert me_b.get_json()['data']['avatar'] == url
        assert me_b.get_json()['data']['username'] == 'userb'

        # User A 头像未被更新（Session 被 JWT 覆盖）
        token_a = _get_token(client, 'a@example.com')
        me_a = client.get('/auth/user', headers={'Authorization': f'Bearer {token_a}'})
        assert me_a.get_json()['data']['avatar'] != url


class TestInvalidJWT:
    """G. 无效 JWT"""

    def test_invalid_jwt_with_valid_session_401(self, client):
        """伪造 JWT + 有效 Session → 401，不得 fallback 到 Session"""
        _register(client, 'forged', 'forged@example.com')
        _login(client, 'forged@example.com')  # 有效 Session 存在

        resp = _upload_avatar(client, headers={'Authorization': 'Bearer invalid.token.value'})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None


class TestExpiredJWT:
    """H. 过期 JWT"""

    def test_expired_jwt_with_valid_session_401(self, app, client):
        """过期 JWT + 有效 Session → 401，不得绕过"""
        from flask_jwt_extended import create_access_token

        _register(client, 'expired', 'expired@example.com')
        _login(client, 'expired@example.com')  # 有效 Session 存在

        # 签发一个已过期的 JWT（-1 小时）
        with app.app_context():
            expired_token = create_access_token(
                identity='1',
                expires_delta=timedelta(hours=-1),
            )

        resp = _upload_avatar(client, headers={'Authorization': f'Bearer {expired_token}'})
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None
