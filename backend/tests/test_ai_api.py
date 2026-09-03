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

    def test_failed_no_artwork(self, client, app, db, monkeypatch):
        """AI 失败（注入 fail provider）→ 不创建 Artwork，task FAILED"""
        from app.models.artwork import Artwork
        from app.models.ai_task import AITask
        from app.services.mock import MockProvider

        # 注入 mock_behavior='fail' 的 Provider（A4: 显式控制，非 prompt 关键字）
        # 注意: ai.py 中 `from app.services.factory import get_ai_service` 直接引用函数对象，
        # 因此需 patch ai 模块命名空间中的引用。
        monkeypatch.setattr(
            'app.api.v1.ai.get_ai_service',
            lambda: MockProvider(mock_behavior='fail'),
        )

        _register(client, 'aifail', 'aifail@e.com')
        token = _login(client, 'aifail@e.com')
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '正常输入，但 provider 配置为失败',
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


class TestInputUrlSecurity:
    """阶段10 A1: input_url 安全白名单校验"""

    def _setup(self, client):
        _register(client, 'aisec', 'aisec@e.com')
        return _login(client, 'aisec@e.com')

    def test_valid_upload_url(self, client, db):
        """合法上传 URL → 200"""
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'image_to_3d',
            'input_url': '/api/static/uploads/images/ab12cd34_test.png',
        }, headers=_auth(token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['status'] == 'SUCCESS'

    def test_external_https_url_rejected(self, client, db):
        """外部 HTTPS URL → 400"""
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'image_to_3d',
            'input_url': 'https://evil.example/image.png',
        }, headers=_auth(token))
        assert resp.status_code == 400
        assert resp.get_json()['data'] is None

    def test_localhost_rejected(self, client, db):
        """localhost → 400"""
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'image_to_3d',
            'input_url': 'http://localhost:8000/image.png',
        }, headers=_auth(token))
        assert resp.status_code == 400

    def test_127_0_0_1_rejected(self, client, db):
        """127.0.0.1 → 400"""
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'image_to_3d',
            'input_url': 'http://127.0.0.1/secret.png',
        }, headers=_auth(token))
        assert resp.status_code == 400

    def test_empty_input_url_rejected(self, client, db):
        """空字符串 → 400"""
        token = self._setup(client)
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'image_to_3d', 'input_url': '',
        }, headers=_auth(token))
        assert resp.status_code == 400

    def test_illegal_path_rejected(self, client, db):
        """非法路径（uploads 子串但前缀错误/路径穿越）→ 400"""
        token = self._setup(client)
        # 含 uploads 子串但前缀不对
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'image_to_3d',
            'input_url': '/api/other/uploads/xxx.png',
        }, headers=_auth(token))
        assert resp.status_code == 400
        # 路径穿越
        resp2 = client.post('/ai/generate-3d', json={
            'task_type': 'image_to_3d',
            'input_url': '/api/static/uploads/../config.py',
        }, headers=_auth(token))
        assert resp2.status_code == 400

    def test_analyze_style_input_url_security(self, client, db):
        """analyze-style 同样校验 input_url"""
        token = self._setup(client)
        # 合法
        ok = client.post('/ai/analyze-style', json={
            'input_url': '/api/static/uploads/images/ab12cd34_test.png',
        }, headers=_auth(token))
        assert ok.status_code == 200
        # 外部 URL
        bad = client.post('/ai/analyze-style', json={
            'input_url': 'https://evil.example/x.png',
        }, headers=_auth(token))
        assert bad.status_code == 400


class TestArtworkDeletionAITask:
    """阶段10 A2: Artwork 删除后 AITask 保留，artwork_id 置 NULL"""

    def test_artwork_delete_keeps_aitask(self, client, app, db):
        """删除 Artwork 后 AITask 仍存在且 artwork_id=None"""
        from app.models.artwork import Artwork
        from app.models.ai_task import AITask

        _register(client, 'a2del', 'a2del@e.com')
        token = _login(client, 'a2del@e.com')
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成作品A',
        }, headers=_auth(token))
        data = resp.get_json()['data']
        task_id = data['id']
        artwork_id = data['artwork_id']

        # 删除 Artwork
        with app.app_context():
            artwork = db.session.get(Artwork, artwork_id)
            db.session.delete(artwork)
            db.session.commit()

        # AITask 保留且 artwork_id=None
        with app.app_context():
            task = db.session.get(AITask, task_id)
            assert task is not None, 'AITask 应保留'
            assert task.artwork_id is None, 'artwork_id 应置 NULL'
            assert task.status == 'SUCCESS'


class TestArtworkIdempotency:
    """阶段10 A3: Artwork 创建幂等性自动化测试"""

    def test_repeated_get_no_duplicate_artwork(self, client, app, db):
        """连续 GET /ai/tasks/<id> 不重复创建 Artwork（纯只读）"""
        from app.models.artwork import Artwork
        from app.models.ai_task import AITask

        _register(client, 'aiidem', 'aiidem@e.com')
        token = _login(client, 'aiidem@e.com')
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '幂等性测试作品',
        }, headers=_auth(token))
        data = resp.get_json()['data']
        task_id = data['id']
        artwork_id = data['artwork_id']

        with app.app_context():
            assert Artwork.query.count() == 1

        # 连续 GET 5 次
        for i in range(5):
            r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
            assert r.status_code == 200
            assert r.get_json()['data']['status'] == 'SUCCESS'
            with app.app_context():
                assert Artwork.query.count() == 1, f'第{i+1}次 GET 后 Artwork 重复创建'

        # task.artwork_id / external_task_id 不变
        with app.app_context():
            task = db.session.get(AITask, task_id)
            assert task.artwork_id == artwork_id
            assert task.external_task_id is not None
            updated_after = task.updated_at
            external_after = task.external_task_id

        # 再次 GET 后仍无变化（纯只读）
        client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        with app.app_context():
            task = db.session.get(AITask, task_id)
            assert task.updated_at == updated_after
            assert task.external_task_id == external_after
            assert task.artwork_id == artwork_id
            assert Artwork.query.count() == 1


class TestAnalyzeStyleArtworkIntegration:
    """阶段11-C: analyze-style 可选 artwork_id + 分析结果持久化

    覆盖: JWT / Session / 无效 JWT 不降级 /
          本人作品写入 / 他人作品 403 / 不存在作品 404 / 不传保持旧行为
    全部使用 MockProvider，禁止真实 API 调用
    """

    INPUT_URL = '/api/static/uploads/images/ab12cd34_test.png'

    def _create_artwork(self, client, token, title='待分析作品'):
        """辅助：通过 /workshop/save 创建作品，返回 artwork_id"""
        resp = client.post('/workshop/save', json={'title': title}, headers=_auth(token))
        assert resp.status_code == 200
        return resp.get_json()['data']['id']

    def test_jwt_analyze_style_success(self, client, db):
        """JWT 认证 analyze-style → 200 + 结构化结果"""
        _register(client, 'asjwt', 'asjwt@e.com')
        token = _login(client, 'asjwt@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': self.INPUT_URL,
        }, headers=_auth(token))
        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['style']
        assert isinstance(data['features'], list)
        assert isinstance(data['report'], dict)
        assert data['task']['status'] == 'SUCCESS'

    def test_session_analyze_style_success(self, client, db):
        """Session 认证 analyze-style（无 Authorization）→ 200"""
        _register(client, 'assess', 'assess@e.com')
        _login(client, 'assess@e.com')  # Session Cookie 保存在 test client
        resp = client.post('/ai/analyze-style', json={
            'input_url': self.INPUT_URL,
        })
        assert resp.status_code == 200
        assert resp.get_json()['data']['task']['status'] == 'SUCCESS'

    def test_invalid_jwt_no_fallback(self, client, db):
        """伪造 JWT + 有效 Session → 401，不得降级到 Session"""
        _register(client, 'asforged', 'asforged@e.com')
        _login(client, 'asforged@e.com')  # 有效 Session 存在
        resp = client.post('/ai/analyze-style', json={
            'input_url': self.INPUT_URL,
        }, headers={'Authorization': 'Bearer invalid.token.value'})
        assert resp.status_code == 401
        assert resp.get_json()['code'] == 401
        assert resp.get_json()['data'] is None

    def test_own_artwork_id_persisted(self, client, app, db):
        """本人 artwork_id → 200 + artwork.style_analysis 持久化"""
        from app.models.artwork import Artwork
        from app.models.ai_task import AITask

        _register(client, 'asown', 'asown@e.com')
        token = _login(client, 'asown@e.com')
        artwork_id = self._create_artwork(client, token)

        with app.app_context():
            assert Artwork.query.count() == 1
            assert db.session.get(Artwork, artwork_id).style_analysis is None  # 分析前为空

        resp = client.post('/ai/analyze-style', json={
            'input_url': self.INPUT_URL,
            'artwork_id': artwork_id,
        }, headers=_auth(token))
        assert resp.status_code == 200
        task_id = resp.get_json()['data']['task']['id']

        with app.app_context():
            artwork = db.session.get(Artwork, artwork_id)
            assert artwork.style_analysis is not None
            assert artwork.style_analysis['status'] == 'SUCCESS'
            assert artwork.style_analysis['style'] == 'huishan_clay_figure'
            assert isinstance(artwork.style_analysis['features'], list)
            assert isinstance(artwork.style_analysis['report'], dict)
            # 设计决策: task.artwork_id 不回填（其语义是"方案B成功后创建的作品"，
            # analyze-style 针对已存在作品，仅回写分析结果字段）
            task = db.session.get(AITask, task_id)
            assert task.artwork_id is None

    def test_other_user_artwork_rejected(self, client, app, db):
        """他人 artwork_id → 403，且不写入分析结果"""
        from app.models.artwork import Artwork

        # 用户 A 创建作品
        _register(client, 'asowner', 'asowner@e.com')
        token_a = _login(client, 'asowner@e.com')
        artwork_id = self._create_artwork(client, token_a, title='A的作品')

        # 用户 B 尝试分析并写入 A 的作品
        _register(client, 'asother', 'asother@e.com')
        token_b = _login(client, 'asother@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': self.INPUT_URL,
            'artwork_id': artwork_id,
        }, headers=_auth(token_b))
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

        # A 的作品未被修改（禁止越权写入）
        with app.app_context():
            artwork = db.session.get(Artwork, artwork_id)
            assert artwork.style_analysis is None

    def test_nonexistent_artwork_404(self, client, app, db):
        """不存在的 artwork_id → 404（fail-fast，不产生任务记录）"""
        from app.models.ai_task import AITask

        _register(client, 'asnone', 'asnone@e.com')
        token = _login(client, 'asnone@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': self.INPUT_URL,
            'artwork_id': 'nonexistent-artwork-id',
        }, headers=_auth(token))
        assert resp.status_code == 404
        assert resp.get_json()['code'] == 404

        with app.app_context():
            assert AITask.query.count() == 0  # 无效请求不留下任务记录

    def test_no_artwork_id_keeps_old_behavior(self, client, app, db):
        """不传 artwork_id → 200 纯分析，不修改/不创建 Artwork"""
        from app.models.artwork import Artwork

        _register(client, 'asold', 'asold@e.com')
        token = _login(client, 'asold@e.com')
        artwork_id = self._create_artwork(client, token, title='既有作品')

        resp = client.post('/ai/analyze-style', json={
            'input_url': self.INPUT_URL,
        }, headers=_auth(token))
        assert resp.status_code == 200

        with app.app_context():
            assert Artwork.query.count() == 1  # 未创建新作品
            artwork = db.session.get(Artwork, artwork_id)
            assert artwork.style_analysis is None  # 既有作品未被修改


class TestAsyncTaskRefresh:
    """阶段12-B3-B: GET /ai/tasks/<id> 轮询刷新真实异步任务（hunyuan RUNNING + JobId）"""

    def _register_get_uid(self, client, name):
        _register(client, name, f'{name}@e.com')
        resp = client.post('/auth/login', json={
            'email': f'{name}@e.com', 'password': 'password123',
        })
        data = resp.get_json()['data']
        return data['token'], data['id']

    def _create_running_task(self, app, user_id, job_id='job-test-001'):
        """直接落库一个 RUNNING + JobId 的 hunyuan 异步任务"""
        from app.extensions import db
        from app.models.ai_task import AITask

        with app.app_context():
            task = AITask(
                user_id=user_id, provider='hunyuan', model='hunyuan3d-pro',
                task_type='text_to_3d', prompt='生成惠山泥人阿福',
                status='RUNNING', external_task_id=job_id,
            )
            db.session.add(task)
            db.session.commit()
            return task.id

    def _stub_service(self, result=None, error=None):
        """构造带 query_task 能力的假 hunyuan Provider"""
        from app.utils.exceptions import AIServiceError

        class StubHunyuan:
            provider_name = 'hunyuan'

            def query_task(self, task):
                if error:
                    raise AIServiceError(error)
                return result

        return StubHunyuan()

    def test_refresh_success_creates_artwork_once(self, client, app, monkeypatch):
        """SUCCESS 刷新: task→SUCCESS + result_url + 建 Artwork；重复 GET 幂等"""
        from app.models.artwork import Artwork

        token, uid = self._register_get_uid(client, 'hyrsucc')
        task_id = self._create_running_task(app, uid)
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_service(
            result={'status': 'SUCCESS', 'result_url': 'https://cos.example.com/model.glb',
                    'error_message': None},
        ))

        r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['status'] == 'SUCCESS'
        assert d['result_url'] == 'https://cos.example.com/model.glb'
        assert d['artwork_id']  # Artwork 只在 SUCCESS 后创建
        with app.app_context():
            assert Artwork.query.count() == 1

        # SUCCESS 终态不再进入刷新 → 重复 GET 不重复创建 Artwork（幂等）
        client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        with app.app_context():
            assert Artwork.query.count() == 1

    def test_refresh_failed(self, client, app, monkeypatch):
        """FAILED 刷新: task→FAILED + error_message；不建 Artwork"""
        from app.models.artwork import Artwork

        token, uid = self._register_get_uid(client, 'hyrsfail')
        task_id = self._create_running_task(app, uid)
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_service(
            result={'status': 'FAILED', 'result_url': None,
                    'error_message': '生成失败：内容不合规'},
        ))

        r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['status'] == 'FAILED'
        assert d['error_message'] == '生成失败：内容不合规'
        assert d['artwork_id'] is None
        with app.app_context():
            assert Artwork.query.count() == 0

    def test_refresh_still_running(self, client, app, monkeypatch):
        """RUNNING 刷新: 任务保持 RUNNING（轮询中，不落终态）"""
        token, uid = self._register_get_uid(client, 'hyrsrun')
        task_id = self._create_running_task(app, uid)
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_service(
            result={'status': 'RUNNING', 'result_url': None, 'error_message': None},
        ))

        r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['status'] == 'RUNNING'
        assert d['artwork_id'] is None

    def test_refresh_query_failure_keeps_running(self, client, app, monkeypatch):
        """腾讯查询异常: 任务保持 RUNNING + 接口仍 200（不中断读取、不误判）"""
        token, uid = self._register_get_uid(client, 'hyrserr')
        task_id = self._create_running_task(app, uid)
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_service(
            error='腾讯混元3D任务查询失败: RequestTimeout',
        ))

        r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['status'] == 'RUNNING'  # 保守保持，由下次轮询重试
        assert d['artwork_id'] is None

    def test_refresh_success_downloads_local(self, client, app, monkeypatch):
        """阶段13-B2: SUCCESS 时产物下载转存成功 → task/Artwork.model_url 为本地稳定地址"""
        from app.extensions import db as flask_db
        from app.models.artwork import Artwork

        tencent_url = ('https://hunyuan-prod-1258344699.cos.ap-guangzhou.tencentcos.cn/'
                       '3d/output/xxx/model.glb?q-sign-time=123')
        token, uid = self._register_get_uid(client, 'hy13b2ok')
        task_id = self._create_running_task(app, uid)
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_service(
            result={'status': 'SUCCESS', 'result_url': tencent_url, 'error_message': None},
        ))
        monkeypatch.setattr(
            'app.services.ai_task.download_model_to_local',
            lambda remote_url: '/api/static/uploads/models/abc123def456.glb',
        )

        r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['status'] == 'SUCCESS'
        assert d['result_url'] == '/api/static/uploads/models/abc123def456.glb'  # 本地地址
        with app.app_context():
            art = flask_db.session.get(Artwork, d['artwork_id'])
            assert art.model_url == '/api/static/uploads/models/abc123def456.glb'

    def test_refresh_success_download_fail_fallback(self, client, app, monkeypatch):
        """阶段13-B2: 下载转存失败 → 保留腾讯 result_url 作为 fallback"""
        from app.extensions import db as flask_db
        from app.models.artwork import Artwork
        from app.utils.exceptions import ValidationError

        tencent_url = ('https://hunyuan-prod-1258344699.cos.ap-guangzhou.tencentcos.cn/'
                       '3d/output/xxx/model.glb?q-sign-time=123')
        token, uid = self._register_get_uid(client, 'hy13b2fb')
        task_id = self._create_running_task(app, uid)
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_service(
            result={'status': 'SUCCESS', 'result_url': tencent_url, 'error_message': None},
        ))
        monkeypatch.setattr(
            'app.services.ai_task.download_model_to_local',
            lambda remote_url: (_ for _ in ()).throw(ValidationError('网络不可达')),
        )

        r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['status'] == 'SUCCESS'
        assert d['result_url'] == tencent_url  # fallback 保留腾讯 URL
        with app.app_context():
            art = flask_db.session.get(Artwork, d['artwork_id'])
            assert art.model_url == tencent_url

    def test_refresh_timeout_marks_failed(self, client, app, monkeypatch):
        """阶段13-B3: RUNNING 超过 AI_TASK_TIMEOUT_SECONDS → 直接 FAILED（超时保护）"""
        from datetime import datetime, timedelta

        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        app.config['AI_TASK_TIMEOUT_SECONDS'] = 1800
        token, uid = self._register_get_uid(client, 'hyto')
        task_id = self._create_running_task(app, uid)
        # 把 updated_at 拨到 40 分钟前（模拟长时间 RUNNING）
        with app.app_context():
            task = flask_db.session.get(AITask, task_id)
            task.updated_at = datetime.utcnow() - timedelta(minutes=40)
            flask_db.session.commit()

        r = client.get(f'/ai/tasks/{task_id}', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['status'] == 'FAILED'  # 超时保护：不再无限轮询
        assert '超时' in d['error_message']
        assert d['artwork_id'] is None

    def test_generate_hunyuan_model_metadata(self, client, app, monkeypatch):
        """阶段13-B3: hunyuan Provider 生成任务 model 元数据正确（非 'mock-3d'）"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        class StubHunyuanGen:
            provider_name = 'hunyuan'
            model = 'hunyuan-3d'

            def generate_3d(self, task):
                return {'status': 'RUNNING', 'external_task_id': 'job-model-1',
                        'result_url': None, 'error_message': None}

        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: StubHunyuanGen())
        _register(client, 'hymodel', 'hymodel@e.com')
        token = _login(client, 'hymodel@e.com')

        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成一个紫砂壶',
        }, headers=_auth(token))
        assert resp.status_code == 200
        d = resp.get_json()['data']
        assert d['provider'] == 'hunyuan'
        assert d['model'] == 'hunyuan-3d'  # 不再错误记录为 mock-3d
        assert d['status'] == 'RUNNING'
        assert d['external_task_id'] == 'job-model-1'
        # 落库核对
        with app.app_context():
            task = flask_db.session.get(AITask, d['id'])
            assert task.model == 'hunyuan-3d'


class TestTaskList:
    """阶段13-B3: GET /ai/tasks 任务列表（仅本人，分页倒序）"""

    def _create_tasks(self, app, user_id, count=3):
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        with app.app_context():
            for i in range(count):
                task = AITask(
                    user_id=user_id, provider='mock', model='mock-3d',
                    task_type='text_to_3d', prompt=f'任务{i}', status='SUCCESS',
                )
                flask_db.session.add(task)
            flask_db.session.commit()

    def test_list_own_tasks_paginated(self, client, app):
        """本人任务列表 → 分页返回 + 倒序 + 字段完整"""
        _register(client, 'tl1', 'tl1@e.com')
        resp = client.post('/auth/login', json={'email': 'tl1@e.com', 'password': 'password123'})
        data = resp.get_json()['data']
        self._create_tasks(app, data['id'], count=3)

        r = client.get('/ai/tasks', headers=_auth(data['token']))
        assert r.status_code == 200
        body = r.get_json()
        assert body['code'] == 200
        pagination = body['meta']['pagination']
        assert pagination['total'] == 3
        assert len(body['data']) == 3
        first = body['data'][0]
        for key in ('id', 'provider', 'model', 'task_type', 'status', 'external_task_id',
                    'result_url', 'artwork_id', 'error_message'):
            assert key in first
        # 倒序：最新创建在前
        created = [item['created_at'] for item in body['data']]
        assert created == sorted(created, reverse=True)

    def test_list_isolated_per_user(self, client, app):
        """他人任务不可见（隔离）"""
        _register(client, 'tl2a', 'tl2a@e.com')
        r1 = client.post('/auth/login', json={'email': 'tl2a@e.com', 'password': 'password123'})
        self._create_tasks(app, r1.get_json()['data']['id'], count=2)

        _register(client, 'tl2b', 'tl2b@e.com')
        r2 = client.post('/auth/login', json={'email': 'tl2b@e.com', 'password': 'password123'})
        data2 = r2.get_json()['data']

        r = client.get('/ai/tasks', headers=_auth(data2['token']))
        assert r.get_json()['meta']['pagination']['total'] == 0  # 用户 B 看不到用户 A 的任务

    def test_list_empty(self, client, app):
        """无任务 → total 0 + 空 items"""
        _register(client, 'tl3', 'tl3@e.com')
        resp = client.post('/auth/login', json={'email': 'tl3@e.com', 'password': 'password123'})
        data = resp.get_json()['data']
        r = client.get('/ai/tasks', headers=_auth(data['token']))
        assert r.status_code == 200
        body = r.get_json()
        assert body['meta']['pagination']['total'] == 0
        assert body['data'] == []

    def test_list_no_auth_401(self, client):
        """未登录 → 401"""
        r = client.get('/ai/tasks')
        assert r.status_code == 401

    def test_list_pagination_params(self, client, app):
        """分页参数生效（page/per_page）"""
        _register(client, 'tl4', 'tl4@e.com')
        resp = client.post('/auth/login', json={'email': 'tl4@e.com', 'password': 'password123'})
        data = resp.get_json()['data']
        self._create_tasks(app, data['id'], count=5)

        r = client.get('/ai/tasks?page=2&per_page=2', headers=_auth(data['token']))
        body = r.get_json()
        pagination = body['meta']['pagination']
        assert pagination['total'] == 5
        assert len(body['data']) == 2
        assert pagination['page'] == 2

    def test_list_triggers_timeout_cleanup(self, client, app):
        """阶段13-B4: 列表路径批量超时清理 —— RUNNING+JobId 超时任务 → FAILED"""
        from datetime import datetime, timedelta

        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        app.config['AI_TASK_TIMEOUT_SECONDS'] = 1800
        _register(client, 'tlto', 'tlto@e.com')
        resp = client.post('/auth/login', json={'email': 'tlto@e.com', 'password': 'password123'})
        data = resp.get_json()['data']

        # 造两个 RUNNING+JobId 任务：一个超时（40 分钟前），一个正常（刚提交）
        with app.app_context():
            old = AITask(user_id=data['id'], provider='hunyuan', model='hunyuan-3d',
                         task_type='text_to_3d', prompt='旧任务', status='RUNNING',
                         external_task_id='job-old')
            old.updated_at = datetime.utcnow() - timedelta(minutes=40)
            fresh = AITask(user_id=data['id'], provider='hunyuan', model='hunyuan-3d',
                           task_type='text_to_3d', prompt='新任务', status='RUNNING',
                           external_task_id='job-fresh')
            flask_db.session.add_all([old, fresh])
            flask_db.session.commit()
            old_id, fresh_id = old.id, fresh.id

        r = client.get('/ai/tasks', headers=_auth(data['token']))
        assert r.status_code == 200
        body = r.get_json()['data']
        by_id = {item['id']: item for item in body}
        # 超时任务已被清理为 FAILED
        assert by_id[old_id]['status'] == 'FAILED'
        assert '超时' in by_id[old_id]['error_message']
        # 正常任务保持 RUNNING
        assert by_id[fresh_id]['status'] == 'RUNNING'
        # DB 核对
        with app.app_context():
            assert flask_db.session.get(AITask, old_id).status == 'FAILED'
            assert flask_db.session.get(AITask, fresh_id).status == 'RUNNING'


class TestTaskStatistics:
    """阶段13-C1: GET /ai/tasks/statistics 任务统计（仅本人）"""

    def _seed_tasks(self, app, user_id, statuses):
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        with app.app_context():
            for i, status in enumerate(statuses):
                task = AITask(
                    user_id=user_id, provider='mock', model='mock-3d',
                    task_type='text_to_3d', prompt=f'统计任务{i}', status=status,
                )
                flask_db.session.add(task)
            flask_db.session.commit()

    def test_statistics_counts(self, client, app):
        """统计: total/success/running/failed/pending + success_rate"""
        _register(client, 'stat1', 'stat1@e.com')
        resp = client.post('/auth/login', json={'email': 'stat1@e.com', 'password': 'password123'})
        data = resp.get_json()['data']
        # 6 SUCCESS + 1 RUNNING + 2 FAILED + 1 PENDING = 10
        self._seed_tasks(app, data['id'], ['SUCCESS'] * 6 + ['RUNNING'] + ['FAILED'] * 2 + ['PENDING'])

        r = client.get('/ai/tasks/statistics', headers=_auth(data['token']))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['total'] == 10
        assert d['success'] == 6
        assert d['running'] == 1
        assert d['failed'] == 2
        assert d['pending'] == 1
        assert d['success_rate'] == round(6 / 10, 4) == 0.6

    def test_statistics_empty(self, client, app):
        """无任务 → total 0 + success_rate 0（不除零）"""
        _register(client, 'stat2', 'stat2@e.com')
        resp = client.post('/auth/login', json={'email': 'stat2@e.com', 'password': 'password123'})
        data = resp.get_json()['data']
        r = client.get('/ai/tasks/statistics', headers=_auth(data['token']))
        d = r.get_json()['data']
        assert d['total'] == 0
        assert d['success_rate'] == 0.0

    def test_statistics_isolated_per_user(self, client, app):
        """统计仅含本人任务"""
        _register(client, 'stat3a', 'stat3a@e.com')
        r1 = client.post('/auth/login', json={'email': 'stat3a@e.com', 'password': 'password123'})
        self._seed_tasks(app, r1.get_json()['data']['id'], ['SUCCESS'] * 5)

        _register(client, 'stat3b', 'stat3b@e.com')
        r2 = client.post('/auth/login', json={'email': 'stat3b@e.com', 'password': 'password123'})
        data2 = r2.get_json()['data']
        r = client.get('/ai/tasks/statistics', headers=_auth(data2['token']))
        assert r.get_json()['data']['total'] == 0

    def test_statistics_no_auth_401(self, client):
        """未登录 → 401"""
        r = client.get('/ai/tasks/statistics')
        assert r.status_code == 401


class TestDuplicateGeneration:
    """阶段13-C1: 重复生成保护（同用户/同类型/同输入 RUNNING 任务命中）"""

    def _stub_running(self):
        """Provider stub: 生成返回 RUNNING（模拟 hunyuan 异步）"""
        class StubHunyuanGen:
            provider_name = 'hunyuan'
            model = 'hunyuan-3d'

            def generate_3d(self, task):
                return {'status': 'RUNNING', 'external_task_id': 'job-dup-1',
                        'result_url': None, 'error_message': None}

        return StubHunyuanGen()

    def test_same_prompt_returns_existing_running(self, client, app, monkeypatch):
        """同用户同 prompt 重复提交（首个 RUNNING 中）→ 返回已有任务，不新建"""
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_running())
        _register(client, 'dup1', 'dup1@e.com')
        token = _login(client, 'dup1@e.com')

        body = {'task_type': 'text_to_3d', 'prompt': '生成惠山泥人阿福'}
        r1 = client.post('/ai/generate-3d', json=body, headers=_auth(token))
        r2 = client.post('/ai/generate-3d', json=body, headers=_auth(token))
        assert r1.status_code == 200 and r2.status_code == 200
        d1 = r1.get_json()['data']
        d2 = r2.get_json()['data']
        assert d1['id'] == d2['id']  # 同一任务
        assert d1['status'] == 'RUNNING'
        assert '正在执行' in r2.get_json()['message']
        with app.app_context():
            from app.models.ai_task import AITask
            assert AITask.query.count() == 1  # 仅 1 条（未重复创建）

    def test_different_prompt_creates_new(self, client, app, monkeypatch):
        """不同 prompt → 创建新任务"""
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_running())
        _register(client, 'dup2', 'dup2@e.com')
        token = _login(client, 'dup2@e.com')

        r1 = client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': '紫砂壶'},
                         headers=_auth(token))
        r2 = client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': '惠山泥人'},
                         headers=_auth(token))
        assert r1.get_json()['data']['id'] != r2.get_json()['data']['id']

    def test_terminal_task_allows_regenerate(self, client, app, monkeypatch):
        """终态（SUCCESS）同 prompt → 允许重新生成（不拦截）"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: self._stub_running())
        _register(client, 'dup3', 'dup3@e.com')
        resp = client.post('/auth/login', json={'email': 'dup3@e.com', 'password': 'password123'})
        data = resp.get_json()['data']

        # 预置一个 SUCCESS 终态同 prompt 任务
        with app.app_context():
            done = AITask(user_id=data['id'], provider='hunyuan', model='hunyuan-3d',
                          task_type='text_to_3d', prompt='重复测试', status='SUCCESS')
            flask_db.session.add(done)
            flask_db.session.commit()
            done_id = done.id  # 会话内读取，避免 detached refresh

        r = client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': '重复测试'},
                        headers=_auth(data['token']))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['id'] != done_id  # 新建任务（终态不拦截）
        assert d['status'] == 'RUNNING'
