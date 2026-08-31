# ============================================================
# 智绘锡承 - AI API 测试（阶段9）
# 覆盖: 认证 / 参数 / 权限 / Artwork 集成（方案 B）
# 全部使用 MockProvider，禁止真实 API 调用
# ============================================================
import pytest


@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录 + Mock Provider）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'  # 显式 Mock
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


class TestGenerate3DAuth:
    """generate-3d 认证"""

    def test_no_auth_401(self, client):
        """未登录 generate → 401"""
        resp = client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': 'x'})
        assert resp.status_code == 401
        assert resp.get_json()['code'] == 401

    def test_jwt_generate_success(self, client, db):
        """JWT 用户 generate → 200 + SUCCESS + Artwork 创建"""
        _register(client, 'aijwt', 'aijwt@e.com')
        token = _login(client, 'aijwt@e.com')
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成一个惠山泥人',
        }, headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert data['data']['status'] == 'SUCCESS'
        assert data['data']['result_url']
        assert data['data']['artwork_id']  # 方案 B: 成功后回填

    def test_session_generate_success(self, client, db):
        """Session 用户 generate（无 Authorization）"""
        _register(client, 'aisess', 'aisess@e.com')
        _login(client, 'aisess@e.com')  # Session Cookie
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成一个泥人',
        })
        assert resp.status_code == 200
        assert resp.get_json()['data']['status'] == 'SUCCESS'


class TestGenerate3DParams:
    """generate-3d 参数校验"""

    def _setup(self, client):
        _register(client, 'aiparam', 'aiparam@e.com')
        return _login(client, 'aiparam@e.com')

    def test_empty_json_400(self, client, db):
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={}, headers=_auth(token))
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_text_to_3d_no_prompt_400(self, client, db):
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={'task_type': 'text_to_3d'}, headers=_auth(token))
        assert resp.status_code == 400
        assert 'prompt' in resp.get_json()['message']

    def test_image_to_3d_no_input_url_400(self, client, db):
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={'task_type': 'image_to_3d'}, headers=_auth(token))
        assert resp.status_code == 400
        assert 'input_url' in resp.get_json()['message']

    def test_invalid_task_type_400(self, client, db):
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={'task_type': 'invalid_type', 'prompt': 'x'}, headers=_auth(token))
        assert resp.status_code == 400


class TestTaskQuery:
    """任务查询权限"""

    def test_query_own_task(self, client, db):
        """查询自己的任务 → 200"""
        _register(client, 'aiowner', 'aiowner@e.com')
        token = _login(client, 'aiowner@e.com')
        resp = client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': 'x'}, headers=_auth(token))
        task_id = resp.get_json()['data']['id']

        resp2 = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert resp2.status_code == 200
        data = resp2.get_json()['data']
        assert data['id'] == task_id
        assert data['status'] == 'SUCCESS'
        assert 'artwork_id' in data
        assert 'error_message' in data

    def test_query_other_user_task_404(self, client, db):
        """查询他人任务 → 404（不泄露存在性）"""
        _register(client, 'aiuser1', 'aiuser1@e.com')
        token1 = _login(client, 'aiuser1@e.com')
        resp = client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': 'x'}, headers=_auth(token1))
        task_id = resp.get_json()['data']['id']

        _register(client, 'aiuser2', 'aiuser2@e.com')
        token2 = _login(client, 'aiuser2@e.com')
        resp2 = client.get(f'/ai/tasks/{task_id}', headers=_auth(token2))
        assert resp2.status_code == 404
        assert resp2.get_json()['code'] == 404

    def test_query_nonexistent_task_404(self, client, db):
        """查询不存在任务 → 404"""
        _register(client, 'ainone', 'ainone@e.com')
        token = _login(client, 'ainone@e.com')
        resp = client.get('/ai/tasks/nonexistent-id', headers=_auth(token))
        assert resp.status_code == 404

    def test_query_no_auth_401(self, client):
        """未登录查询 → 401"""
        resp = client.get('/ai/tasks/some-id')
        assert resp.status_code == 401


class TestAnalyzeStyle:
    """风格分析"""

    def test_analyze_style_success(self, client, db):
        """风格分析成功 → style + features + report"""
        _register(client, 'aistyle', 'aistyle@e.com')
        token = _login(client, 'aistyle@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': '/api/static/uploads/images/ab12cd34_test.png',
        }, headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['style']
        assert isinstance(data['features'], list)
        assert isinstance(data['report'], dict)
        assert data['task']['status'] == 'SUCCESS'

    def test_analyze_style_no_input_url_400(self, client, db):
        """缺 input_url → 400"""
        _register(client, 'aistyle2', 'aistyle2@e.com')
        token = _login(client, 'aistyle2@e.com')
        resp = client.post('/ai/analyze-style', json={'input_url': ''}, headers=_auth(token))
        assert resp.status_code == 400
        assert 'input_url' in resp.get_json()['message']

    def test_analyze_style_no_auth_401(self, client):
        """未登录 → 401"""
        resp = client.post('/ai/analyze-style', json={'input_url': 'x'})
        assert resp.status_code == 401


class TestArtworkIntegration:
    """Artwork 集成（方案 B）"""

    def test_success_creates_artwork(self, client, app, db):
        """AI 成功 → 创建 Artwork，字段正确，task.artwork_id 回填"""
        from app.models.artwork import Artwork

        _register(client, 'aiart', 'aiart@e.com')
        token = _login(client, 'aiart@e.com')
        prompt = '生成惠山泥人阿福'
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': prompt,
        }, headers=_auth(token))
        data = resp.get_json()['data']
        task_id = data['id']
        artwork_id = data['artwork_id']

        with app.app_context():
            artwork = db.session.get(Artwork, artwork_id)
            assert artwork is not None
            assert artwork.is_ai_generated is True
            assert artwork.ai_prompt == prompt
            assert artwork.model_url == data['result_url']
            # task.artwork_id 回填正确
            from app.models.ai_task import AITask
            task = db.session.get(AITask, task_id)
            assert task.artwork_id == artwork_id

    def test_failed_no_artwork(self, client, app, db):
        """AI 失败（prompt 含 FAIL）→ 不创建 Artwork，task FAILED"""
        from app.models.artwork import Artwork
        from app.models.ai_task import AITask

        _register(client, 'aifail', 'aifail@e.com')
        token = _login(client, 'aifail@e.com')
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成 FAIL 失败',
        }, headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['status'] == 'FAILED'
        assert data['error_message']
        assert data['artwork_id'] is None

        with app.app_context():
            assert Artwork.query.count() == 0  # 未创建空壳作品
            task = db.session.get(AITask, data['id'])
            assert task.status == 'FAILED'
            assert task.artwork_id is None
