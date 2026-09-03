# ============================================================
# 智绘锡承 - 文件上传 API 测试（阶段5）
# 覆盖: /workshop/upload + /user/upload-avatar
# 测试使用临时上传目录（不写入真实 static/uploads）
# ============================================================
import os

import pytest


# ------------------------------------------------------------
# 真实文件内容构造（最小合法文件，带正确魔数）
# ------------------------------------------------------------
import io
def _png_bytes():
    """最小 1x1 PNG（含 PNG 魔数）"""
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
        b'\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def _jpg_bytes():
    """最小 JPEG（含 JFIF 魔数）"""
    return (
        b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
        b'\xff\xd9'
    )


def _fake_png_bytes():
    """伪造 .png 扩展名但内容不是 PNG（文本）"""
    return b'this is not a real png file, just plain text padding padding padding'


def _glb_bytes():
    """最小 GLB 头（glTF 魔数 + 版本 + 长度）"""
    import struct
    header = b'glTF' + struct.pack('<II', 2, 12)  # version 2, length 12
    return header + b'\x00' * 4


# ------------------------------------------------------------
# fixtures
# ------------------------------------------------------------
@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录）"""
    from app import create_app

    app = create_app('testing')
    # 上传目录指向临时路径，避免污染真实 static/uploads
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


def _register_and_login(client, username='uploader', email='upload@example.com'):
    """辅助：注册并登录，返回 token 和用户信息"""
    client.post('/auth/register', json={
        'username': username,
        'email': email,
        'password': 'password123',
    })
    resp = client.post('/auth/login', json={
        'email': email,
        'password': 'password123',
    })
    data = resp.get_json()
    return data['data']['token'], data['data']


def _upload_bytes(client, url, content, filename, headers=None):
    """辅助：以 multipart 上传字节内容（BytesIO 确保 werkzeug 正确解析）"""
    return client.post(
        url,
        data={'file': (io.BytesIO(content), filename)},
        content_type='multipart/form-data',
        headers=headers or {},
    )


class TestWorkshopUpload:
    """POST /workshop/upload（阶段12-A: 需要认证，JWT Bearer + Session Cookie 双认证）"""

    @pytest.fixture(autouse=True)
    def auth(self, client):
        """每个测试前注册登录：获取 JWT（Bearer 场景）并建立 Session（兜底场景）"""
        self.token, self.user = _register_and_login(client)

    def _bearer(self):
        return {'Authorization': f'Bearer {self.token}'}

    def test_upload_image_success(self, client, app):
        """登录用户上传 PNG 图片 → data.url"""
        resp = _upload_bytes(
            client, '/workshop/upload', _png_bytes(), 'photo.png', headers=self._bearer()
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert 'url' in data['data']
        assert data['data']['url'].startswith('/api/static/uploads/images/')
        # 文件确实落盘
        rel = data['data']['url'].replace('/api/static/uploads/', '').replace('/', os.sep)
        assert os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], rel))

    def test_upload_model_success(self, client):
        """登录用户上传 GLB 3D 模型 → models 子目录"""
        resp = _upload_bytes(
            client, '/workshop/upload', _glb_bytes(), 'model.glb', headers=self._bearer()
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['data']['url'].startswith('/api/static/uploads/models/')

    def test_upload_anonymous_401(self, client):
        """阶段12-A: 匿名上传（无 Bearer 且无 Session）→ 401"""
        with client.session_transaction() as sess:
            sess.clear()
        resp = _upload_bytes(client, '/workshop/upload', _png_bytes(), 'anon.png')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None

    def test_upload_session_success(self, client, app):
        """阶段12-A: Session Cookie 认证（登录后无 Authorization）→ 200（el-upload 兼容）"""
        resp = _upload_bytes(client, '/workshop/upload', _png_bytes(), 'sess.png')
        assert resp.status_code == 200
        assert resp.get_json()['data']['url'].startswith('/api/static/uploads/images/')

    def test_upload_invalid_token_401(self, client):
        """无效 Bearer Token → 401（不降级 Session）"""
        resp = _upload_bytes(
            client, '/workshop/upload', _png_bytes(), 'x.png',
            headers={'Authorization': 'Bearer bad.token.value'},
        )
        assert resp.status_code == 401

    def test_upload_no_file_field(self, client):
        """缺少 file 字段 → 400"""
        resp = client.post('/workshop/upload', data={}, content_type='multipart/form-data',
                           headers=self._bearer())
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['code'] == 400
        assert data['data'] is None

    def test_upload_empty_filename(self, client):
        """空文件名 → 400"""
        resp = _upload_bytes(client, '/workshop/upload', _png_bytes(), '', headers=self._bearer())
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_upload_disallowed_extension(self, client):
        """不允许的扩展名（.txt / .exe）→ 400"""
        resp = _upload_bytes(client, '/workshop/upload', b'hello', 'evil.txt', headers=self._bearer())
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

        resp = _upload_bytes(client, '/workshop/upload', b'MZ\x90\x00', 'evil.exe', headers=self._bearer())
        assert resp.status_code == 400

    def test_upload_fake_extension(self, client):
        """伪造扩展名（.png 但内容不是图片）→ 400 魔数校验"""
        resp = _upload_bytes(client, '/workshop/upload', _fake_png_bytes(), 'fake.png', headers=self._bearer())
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['code'] == 400
        assert '文件内容' in data['message']

    def test_upload_empty_file(self, client):
        """空文件（0 字节）→ 400"""
        resp = _upload_bytes(client, '/workshop/upload', b'', 'empty.png', headers=self._bearer())
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_upload_path_traversal_sanitized(self, client, app):
        """路径穿越文件名被 secure_filename 清洗，且不越界写入"""
        resp = _upload_bytes(
            client, '/workshop/upload', _png_bytes(), '..\\..\\evil.png', headers=self._bearer()
        )
        assert resp.status_code == 200
        data = resp.get_json()
        url = data['data']['url']
        # URL 中不出现路径穿越片段
        assert '..' not in url
        assert '/../' not in url
        # 文件实际落在 uploads/images 目录内（未越界）
        rel = url.replace('/api/static/uploads/', '').replace('/', os.sep)
        abs_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], rel))
        assert abs_path.startswith(os.path.abspath(app.config['UPLOAD_FOLDER']))
        assert os.path.exists(abs_path)

    def test_upload_url_unique(self, client):
        """两次上传生成不同 URL（UUID 防覆盖）"""
        r1 = _upload_bytes(client, '/workshop/upload', _png_bytes(), 'a.png', headers=self._bearer())
        r2 = _upload_bytes(client, '/workshop/upload', _png_bytes(), 'b.png', headers=self._bearer())
        assert r1.get_json()['data']['url'] != r2.get_json()['data']['url']

    def test_uploaded_file_servable(self, client):
        """上传后 data.url 可经 /static/uploads/<path> 访问（send_from_directory）"""
        resp = _upload_bytes(client, '/workshop/upload', _png_bytes(), 'photo.png', headers=self._bearer())
        url = resp.get_json()['data']['url']
        # /api/static/uploads/xxx → Flask /static/uploads/xxx
        static_path = url.replace('/api/static/', '/static/')
        r = client.get(static_path)
        assert r.status_code == 200
        assert r.data == _png_bytes()

    def test_static_upload_path_traversal_blocked(self, client):
        """静态路由路径穿越被 send_from_directory 拦截 → 404"""
        r = client.get('/static/uploads/../../config.py')
        assert r.status_code in (400, 404)


class TestUserUploadAvatar:
    """POST /user/upload-avatar（强制 JWT，身份来自 token）"""

    def test_upload_avatar_with_token(self, client, app):
        """携带有效 Bearer Token 上传头像 → 200 且 User.avatar 更新"""
        token, user = _register_and_login(client)
        resp = _upload_bytes(
            client, '/user/upload-avatar', _jpg_bytes(), 'avatar.jpg',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert 'url' in data['data']
        assert data['data']['url'].startswith('/api/static/uploads/avatars/')

        # User.avatar 已更新（身份来自 token，非客户端字段）
        me = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert me.get_json()['data']['avatar'] == data['data']['url']

    def test_upload_avatar_no_token(self, client):
        """无 Token → 401 统一 JSON"""
        resp = _upload_bytes(client, '/user/upload-avatar', _png_bytes(), 'a.png')
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None

    def test_upload_avatar_invalid_token(self, client):
        """无效 Token → 401"""
        resp = _upload_bytes(
            client, '/user/upload-avatar', _png_bytes(), 'a.png',
            headers={'Authorization': 'Bearer bad.token.value'},
        )
        assert resp.status_code == 401

    def test_upload_avatar_ignores_client_user_field(self, client, app):
        """客户端提交 user_id/username 等字段被忽略（身份只来自 token）"""
        token, user = _register_and_login(client)
        resp = client.post(
            '/user/upload-avatar',
            data={
                'file': (io.BytesIO(_png_bytes()), 'x.png'),
                'user_id': '999999',          # 伪造的不可信字段
                'username': 'hacker',          # 伪造的不可信字段
            },
            content_type='multipart/form-data',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 200
        # 头像更新到 token 对应的真实用户
        me = client.get('/auth/user', headers={'Authorization': f'Bearer {token}'})
        assert me.get_json()['data']['avatar'] == resp.get_json()['data']['url']
        # 真实用户 id 未被篡改
        assert me.get_json()['data']['id'] == user['id']

    def test_upload_avatar_disallowed_extension(self, client):
        """非图片扩展名 → 400"""
        token, _ = _register_and_login(client)
        resp = _upload_bytes(
            client, '/user/upload-avatar', b'hello world', 'evil.txt',
            headers={'Authorization': f'Bearer {token}'},
        )
        assert resp.status_code == 400


class TestUploadSecurity:
    """上传安全：文件不会污染仓库、不泄露敏感信息"""

    def test_upload_dir_created_automatically(self, app):
        """上传目录自动创建"""
        from app.utils.files import ensure_upload_dir

        target = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
        assert not os.path.exists(target)
        ensure_upload_dir(target)
        assert os.path.isdir(target)

    def test_upload_response_no_sensitive_fields(self, client):
        """上传响应仅含 url，无敏感信息"""
        token, _ = _register_and_login(client, username='securer', email='secure@example.com')
        resp = _upload_bytes(
            client, '/workshop/upload', _png_bytes(), 'a.png',
            headers={'Authorization': f'Bearer {token}'},
        )
        body = resp.get_data(as_text=True)
        assert 'password' not in body
        assert 'token' not in body
        data = resp.get_json()['data']
        assert set(data.keys()) == {'url'}

    def test_static_uploads_gitignored(self):
        """真实上传目录已加入 .gitignore（防提交）"""
        import subprocess
        result = subprocess.run(
            ['git', 'check-ignore', '-v', 'backend/app/static/uploads/test.png'],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')),
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f'uploads 未被 gitignore: {result.stdout} {result.stderr}'
