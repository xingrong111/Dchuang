# ============================================================
# 智绘锡承 - GLMService 单元测试（阶段11-B）
# 覆盖: JSON 解析 / 规范化 / HTTP 调用（monkeypatch requests，不联网）
# 不调用真实 GLM API / 不读取真实 Key
# ============================================================
import json as jsonlib
import os

import pytest


@pytest.fixture
def app(tmp_path):
    """测试应用（UPLOAD_FOLDER 临时目录 + 假 GLM_API_KEY）"""
    from app import create_app

    app = create_app('testing')
    uploads = tmp_path / 'uploads'
    uploads.mkdir(exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(uploads)
    # 测试用假 Key（非真实）
    app.config['GLM_API_KEY'] = 'test-fake-key'
    app.config['GLM_MODEL'] = 'glm-4v-flash'
    app.config['GLM_TIMEOUT'] = 5
    return app


def _png_bytes():
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
        b'\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def _make_task(app, input_url=None):
    """构造 AITask（需 app context 写库）"""
    from app.models.ai_task import AITask

    task = AITask(
        user_id=1,
        provider='glm',
        model='glm-4v-flash',
        task_type='analyze_style',
        input_url=input_url,
        status='PENDING',
    )
    return task


def _create_image(app, subdir='images', name='test.png'):
    """在 UPLOAD_FOLDER 创建图片，返回 URL"""
    import os

    d = os.path.join(app.config['UPLOAD_FOLDER'], subdir)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, 'wb') as f:
        f.write(_png_bytes())
    return f'/api/static/uploads/{subdir}/{name}'


class TestExtractJson:
    """_extract_json 解析测试"""

    def test_pure_json(self):
        from app.services.glm import _extract_json

        assert _extract_json('{"style": "huishan"}') == {'style': 'huishan'}

    def test_markdown_wrapped(self):
        from app.services.glm import _extract_json

        text = '```json\n{"style": "xixiu", "features": ["a"]}\n```'
        assert _extract_json(text) == {'style': 'xixiu', 'features': ['a']}

    def test_text_with_json(self):
        from app.services.glm import _extract_json

        text = '分析结果如下：{"style": "zisha", "features": []} 请查收'
        assert _extract_json(text) == {'style': 'zisha', 'features': []}

    def test_not_json_raises(self):
        from app.services.glm import _extract_json
        from app.utils.exceptions import AIServiceError

        with pytest.raises(AIServiceError):
            _extract_json('这根本不是 JSON')
        with pytest.raises(AIServiceError):
            _extract_json('')


class TestNormalizeResult:
    """_normalize_result 规范化测试"""

    def test_valid(self):
        from app.services.glm import _normalize_result

        r = _normalize_result({'style': 'huishan', 'features': ['a'], 'report': {'d': 'x'}})
        assert r['status'] == 'SUCCESS'
        assert r['style'] == 'huishan'
        assert r['features'] == ['a']
        assert r['report'] == {'d': 'x'}

    def test_missing_style_defaults_unknown(self):
        from app.services.glm import _normalize_result

        r = _normalize_result({})
        assert r['style'] == 'unknown'

    def test_features_not_list(self):
        from app.services.glm import _normalize_result

        r = _normalize_result({'style': 'x', 'features': 'single'})
        assert r['features'] == ['single']

    def test_report_not_dict(self):
        from app.services.glm import _normalize_result

        r = _normalize_result({'style': 'x', 'report': 'plain text'})
        assert isinstance(r['report'], dict)

    def test_not_dict_raises(self):
        from app.services.glm import _normalize_result
        from app.utils.exceptions import AIServiceError

        with pytest.raises(AIServiceError):
            _normalize_result(['not', 'dict'])


class TestGLMServiceInit:
    """GLMService 初始化"""

    def test_key_missing_raises(self, app):
        """Key 缺失 → UnconfiguredProviderError"""
        from app.services.glm import GLMService
        from app.services.base import UnconfiguredProviderError

        app.config['GLM_API_KEY'] = ''
        with app.app_context():
            with pytest.raises(UnconfiguredProviderError):
                GLMService()

    def test_init_ok(self, app):
        """有 Key → 正常初始化"""
        from app.services.glm import GLMService

        with app.app_context():
            svc = GLMService()
            assert svc.provider_name == 'glm'
            assert svc.model == 'glm-4v-flash'


class TestGLMServiceAnalyzeStyle:
    """GLMService.analyze_style（monkeypatch requests.post）"""

    def _fake_response(self, content, status_code=200):
        """构造假 requests.Response"""
        import json

        class FakeResp:
            def __init__(self):
                self.status_code = status_code
                self._content = content

            def json(self):
                if isinstance(self._content, str):
                    return json.loads(self._content)
                return self._content

        return FakeResp()

    def test_success(self, app, monkeypatch):
        """正常响应 → SUCCESS + 结构化结果"""
        from app.services.glm import GLMService

        input_url = _create_image(app)
        task = _make_task(app, input_url=input_url)

        def fake_post(url, headers=None, json=None, timeout=None):
            # 验证请求构造
            assert 'Bearer test-fake-key' in headers['Authorization']
            assert json['model'] == 'glm-4v-flash'
            assert json['messages'][0]['role'] == 'system'
            assert json['messages'][1]['content'][0]['type'] == 'image_url'
            assert json['messages'][1]['content'][0]['image_url']['url'].startswith('data:image/png;base64,')
            # GLM 的 content 是 JSON 字符串
            inner = '{"style": "huishan", "features": ["传统"], "report": {"description": "d"}}'
            return self._fake_response(
                '{"choices": [{"message": {"content": ' + jsonlib.dumps(inner) + '}}]}'
            )

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)
        with app.app_context():
            svc = GLMService()
            result = svc.analyze_style(task)
            assert result['status'] == 'SUCCESS'
            assert result['style'] == 'huishan'
            assert result['features'] == ['传统']

    def test_markdown_content(self, app, monkeypatch):
        """GLM 返回 Markdown 包裹 JSON → 正常解析"""
        from app.services.glm import GLMService

        input_url = _create_image(app)
        task = _make_task(app, input_url=input_url)

        def fake_post(url, headers=None, json=None, timeout=None):
            return self._fake_response(
                '{"choices": [{"message": {"content": "```json\\n'
                '{\\"style\\": \\"xixiu\\", \\"features\\": [\\"a\\"]}\\n```"}}]}'
            )

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)
        with app.app_context():
            svc = GLMService()
            result = svc.analyze_style(task)
            assert result['status'] == 'SUCCESS'
            assert result['style'] == 'xixiu'

    def test_http_error(self, app, monkeypatch):
        """HTTP 非 200 → AIServiceError"""
        from app.services.glm import GLMService
        from app.utils.exceptions import AIServiceError

        input_url = _create_image(app)
        task = _make_task(app, input_url=input_url)

        def fake_post(url, headers=None, json=None, timeout=None):
            return self._fake_response('{"error": "bad"}', status_code=500)

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)
        with app.app_context():
            svc = GLMService()
            with pytest.raises(AIServiceError):
                svc.analyze_style(task)

    def test_timeout(self, app, monkeypatch):
        """网络超时 → AIServiceError"""
        import requests

        from app.services.glm import GLMService
        from app.utils.exceptions import AIServiceError

        input_url = _create_image(app)
        task = _make_task(app, input_url=input_url)

        def fake_post(url, headers=None, json=None, timeout=None):
            raise requests.exceptions.Timeout('timeout')

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)
        with app.app_context():
            svc = GLMService()
            with pytest.raises(AIServiceError):
                svc.analyze_style(task)

    def test_network_error(self, app, monkeypatch):
        """网络异常 → AIServiceError"""
        import requests

        from app.services.glm import GLMService
        from app.utils.exceptions import AIServiceError

        input_url = _create_image(app)
        task = _make_task(app, input_url=input_url)

        def fake_post(url, headers=None, json=None, timeout=None):
            raise requests.exceptions.ConnectionError('conn refused')

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)
        with app.app_context():
            svc = GLMService()
            with pytest.raises(AIServiceError):
                svc.analyze_style(task)

    def test_response_not_json(self, app, monkeypatch):
        """响应非 JSON → AIServiceError"""
        from app.services.glm import GLMService
        from app.utils.exceptions import AIServiceError

        input_url = _create_image(app)
        task = _make_task(app, input_url=input_url)

        class FakeResp:
            status_code = 200

            def json(self):
                raise ValueError('not json')

        monkeypatch.setattr('app.services.glm.requests.post', lambda *a, **k: FakeResp())
        with app.app_context():
            svc = GLMService()
            with pytest.raises(AIServiceError):
                svc.analyze_style(task)

    def test_missing_choices_field(self, app, monkeypatch):
        """响应缺 choices → AIServiceError"""
        from app.services.glm import GLMService
        from app.utils.exceptions import AIServiceError

        input_url = _create_image(app)
        task = _make_task(app, input_url=input_url)

        def fake_post(url, headers=None, json=None, timeout=None):
            return self._fake_response('{"unexpected": true}')

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)
        with app.app_context():
            svc = GLMService()
            with pytest.raises(AIServiceError):
                svc.analyze_style(task)

    def test_image_not_found(self, app, monkeypatch):
        """图片不存在 → AIServiceError"""
        from app.services.glm import GLMService
        from app.utils.exceptions import AIServiceError

        task = _make_task(app, input_url='/api/static/uploads/images/nonexistent.png')

        # 不应调用 requests.post
        monkeypatch.setattr('app.services.glm.requests.post', lambda *a, **k: pytest.fail('不应调用 HTTP'))
        with app.app_context():
            svc = GLMService()
            with pytest.raises(AIServiceError):
                svc.analyze_style(task)


class TestGLMServiceMisc:
    """其他 GLMService 方法"""

    def test_generate_3d_raises(self, app):
        """GLM 不支持 3D → UnconfiguredProviderError"""
        from app.services.glm import GLMService
        from app.services.base import UnconfiguredProviderError

        with app.app_context():
            svc = GLMService()
            with pytest.raises(UnconfiguredProviderError):
                svc.generate_3d(None)

    def test_query_status(self, app):
        """query_status: SUCCESS 任务返回 SUCCESS"""
        from app.services.glm import GLMService

        with app.app_context():
            svc = GLMService()
            assert svc.query_status(_make_task(app)) == 'RUNNING'
            task = _make_task(app)
            task.status = 'SUCCESS'
            assert svc.query_status(task) == 'SUCCESS'


# ------------------------------------------------------------
# 阶段11-D: API 集成 —— AITask.model 与 GLM_MODEL 一致性
# （route 层真实调用链验证，monkeypatch requests，不联网）
# ------------------------------------------------------------


@pytest.fixture
def db(app):
    """初始化数据库表（API 集成测试用）"""
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


class TestAnalyzeStyleAPIModelConsistency:
    """阶段11-D: AITask.model 必须反映实际调用的 GLM_MODEL（不硬编码 'glm-vision'）"""

    @staticmethod
    def _glm_response(content):
        """构造假 requests.Response（GLM chat/completions 格式，content 为 JSON 字符串）"""
        # content(dict) → JSON 文本 → 再序列化为 content 字段的 JSON 字符串值
        inner = jsonlib.dumps(content)
        body = '{"choices": [{"message": {"content": ' + jsonlib.dumps(inner) + '}}]}'

        class FakeResp:
            status_code = 200

            def json(self):
                return jsonlib.loads(body)

        return FakeResp()

    def _register_and_login(self, client, username='glmapi', email='glmapi@e.com'):
        """注册并登录，返回 JWT"""
        r = client.post('/auth/register', json={
            'username': username, 'email': email, 'password': 'password123',
        })
        assert r.status_code == 200
        r = client.post('/auth/login', json={'email': email, 'password': 'password123'})
        assert r.status_code == 200
        return r.get_json()['data']['token']

    def _call_analyze(self, app, client, token):
        """创建真实图片并调用 analyze-style，断言 200，返回 task dict"""
        input_url = _create_image(app)
        resp = client.post('/ai/analyze-style', json={
            'input_url': input_url,
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        return resp.get_json()['data']['task']

    def test_task_model_matches_default_glm_model(self, app, client, monkeypatch):
        """AI_PROVIDER=glm: task.model == GLM_MODEL（默认 glm-4v-flash）== 实际请求 model"""
        app.config['AI_PROVIDER'] = 'glm'
        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured['request_model'] = json['model']
            return self._glm_response({'style': 'huishan', 'features': ['a'], 'report': {'d': 'x'}})

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)

        token = self._register_and_login(client)
        task = self._call_analyze(app, client, token)

        assert task['status'] == 'SUCCESS'
        assert task['model'] == app.config['GLM_MODEL'] == 'glm-4v-flash'
        # 任务元数据与实际请求模型一致（不是硬编码的 'glm-vision'）
        assert task['model'] == captured['request_model']

    def test_task_model_follows_custom_glm_model_config(self, app, client, monkeypatch):
        """GLM_MODEL 配置改变 → task.model 跟随新值（证明未硬编码旧值）"""
        app.config['AI_PROVIDER'] = 'glm'
        app.config['GLM_MODEL'] = 'glm-4v-plus'

        def fake_post(url, headers=None, json=None, timeout=None):
            return self._glm_response({'style': 'huishan', 'features': ['a'], 'report': {'d': 'x'}})

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)

        token = self._register_and_login(client)
        task = self._call_analyze(app, client, token)

        assert task['model'] == 'glm-4v-plus'
        assert task['model'] == app.config['GLM_MODEL']
        assert task['model'] != 'glm-4v-flash'  # 若仍返回旧值则说明硬编码未消除

    def test_mock_model_unchanged(self, app, client):
        """AI_PROVIDER=mock: task.model == 'mock-vision'（Mock 行为不回归）"""
        app.config['AI_PROVIDER'] = 'mock'
        token = self._register_and_login(client, username='glmmock', email='glmmock@e.com')
        task = self._call_analyze(app, client, token)
        assert task['model'] == 'mock-vision'


# ------------------------------------------------------------
# 阶段11-F: Provider 异常 → AITask 落 FAILED 终态（不僵尸 PENDING/RUNNING）
# （route 层真实调用链验证，monkeypatch requests，不联网）
# ------------------------------------------------------------


def _register_login_jwt(client, username, email):
    """注册并登录，返回 JWT（阶段11-F 测试辅助）"""
    r = client.post('/auth/register', json={
        'username': username, 'email': email, 'password': 'password123',
    })
    assert r.status_code == 200
    r = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert r.status_code == 200
    return r.get_json()['data']['token']


class TestAnalyzeStyleFailureState:
    """阶段11-F: GLM 调用失败（抛异常）→ AITask 必须落 FAILED 终态并 commit

    覆盖: HTTP 500 / Timeout / 网络异常 / 非 JSON / 成功回归 /
          Mock 业务失败回归 / artwork_id 失败不写入
    """

    @staticmethod
    def _resp(status_code, body=None, raise_on_json=False):
        """构造假 requests.Response（可选 json() 抛 ValueError）"""
        import json as _j

        class Resp:
            def __init__(self):
                self.status_code = status_code

            def json(self):
                if raise_on_json:
                    raise ValueError('invalid json')
                return body if body is not None else {}

        return Resp()

    def _latest_task(self, app):
        """查询最近创建的 AITask（每测试仅一个任务，first 即目标）"""
        from app.models.ai_task import AITask

        return AITask.query.order_by(AITask.created_at.desc()).first()

    def test_http_500_marks_failed(self, app, client, monkeypatch):
        """A. HTTP 500 → API 503 + AITask.status == FAILED + error_message"""
        from app.models.ai_task import AITask

        app.config['AI_PROVIDER'] = 'glm'
        monkeypatch.setattr(
            'app.services.glm.requests.post',
            lambda *a, **k: self._resp(500),
        )

        token = _register_login_jwt(client, 'f500', 'f500@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': _create_image(app),
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 503
        assert resp.get_json()['code'] == 503
        with app.app_context():
            task = self._latest_task(app)
            assert task is not None
            assert task.status == 'FAILED'
            assert task.error_message
            assert task.status not in ('PENDING', 'RUNNING')
            assert AITask.query.filter(AITask.status == 'PENDING').count() == 0

    def test_timeout_marks_failed(self, app, client, monkeypatch):
        """B. requests Timeout → API 503 + AITask.status == FAILED"""
        import requests

        app.config['AI_PROVIDER'] = 'glm'

        def fake_post(url, headers=None, json=None, timeout=None):
            raise requests.exceptions.Timeout('timeout')

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)

        token = _register_login_jwt(client, 'ftime', 'ftime@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': _create_image(app),
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 503
        with app.app_context():
            task = self._latest_task(app)
            assert task.status == 'FAILED'
            assert task.error_message
            assert '超时' in task.error_message

    def test_request_exception_marks_failed(self, app, client, monkeypatch):
        """C. requests 网络异常（ConnectionError）→ API 503 + AITask FAILED"""
        import requests

        app.config['AI_PROVIDER'] = 'glm'

        def fake_post(url, headers=None, json=None, timeout=None):
            raise requests.exceptions.ConnectionError('connection refused')

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)

        token = _register_login_jwt(client, 'fconn', 'fconn@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': _create_image(app),
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 503
        with app.app_context():
            task = self._latest_task(app)
            assert task.status == 'FAILED'
            assert task.error_message

    def test_non_json_response_marks_failed(self, app, client, monkeypatch):
        """D. HTTP 200 但响应非 JSON → API 503 + AITask FAILED + 不伪造成功"""
        app.config['AI_PROVIDER'] = 'glm'
        monkeypatch.setattr(
            'app.services.glm.requests.post',
            lambda *a, **k: self._resp(200, raise_on_json=True),
        )

        token = _register_login_jwt(client, 'fnjson', 'fnjson@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': _create_image(app),
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 503
        assert resp.get_json()['data'] is None  # 不返回伪造结果
        with app.app_context():
            task = self._latest_task(app)
            assert task.status == 'FAILED'
            assert task.error_message
            assert task.result_url is None  # 无成功产物

    def test_success_still_success(self, app, client, monkeypatch):
        """E. 成功回归: PENDING → RUNNING → SUCCESS，style/features/report 正常"""
        app.config['AI_PROVIDER'] = 'glm'

        def fake_post(url, headers=None, json=None, timeout=None):
            inner = jsonlib.dumps({
                'style': 'huishan', 'features': ['传统'], 'report': {'d': 'x'},
            })
            body = '{"choices": [{"message": {"content": ' + jsonlib.dumps(inner) + '}}]}'
            return self._resp(200, body=jsonlib.loads(body))

        monkeypatch.setattr('app.services.glm.requests.post', fake_post)

        token = _register_login_jwt(client, 'fok', 'fok@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': _create_image(app),
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 200
        data = resp.get_json()['data']
        assert data['task']['status'] == 'SUCCESS'
        assert data['style'] == 'huishan'
        assert data['features'] == ['传统']
        assert isinstance(data['report'], dict)
        with app.app_context():
            task = self._latest_task(app)
            assert task.status == 'SUCCESS'
            assert task.error_message is None

    def test_mock_business_fail_regression(self, app, client, monkeypatch):
        """F. MockProvider 业务失败回归: 返回 FAILED dict（非异常）→ 行为不变"""
        from app.services.mock import MockProvider

        # Mock fail 走"业务失败结果"路径（不抛异常），新增异常处理不得改变其行为
        monkeypatch.setattr(
            'app.api.v1.ai.get_ai_service',
            lambda: MockProvider(mock_behavior='fail'),
        )

        token = _register_login_jwt(client, 'fmock', 'fmock@e.com')
        resp = client.post('/ai/analyze-style', json={
            'input_url': _create_image(app),
        }, headers={'Authorization': f'Bearer {token}'})

        assert resp.status_code == 200  # 业务失败结果 → API 200 + task FAILED（原行为）
        data = resp.get_json()['data']['task']
        assert data['status'] == 'FAILED'
        assert data['error_message']
        with app.app_context():
            task = self._latest_task(app)
            assert task.status == 'FAILED'
            assert task.error_message

    def test_artwork_failure_no_write(self, app, client, monkeypatch):
        """G. 本人 artwork_id + GLM 失败 → task FAILED + style_analysis 不被写入/覆盖"""
        from app.extensions import db
        from app.models.ai_task import AITask
        from app.models.artwork import Artwork

        app.config['AI_PROVIDER'] = 'glm'
        monkeypatch.setattr(
            'app.services.glm.requests.post',
            lambda *a, **k: self._resp(500),
        )

        token = _register_login_jwt(client, 'fgw', 'fgw@e.com')
        headers = {'Authorization': f'Bearer {token}'}

        # 创建本人作品
        ar = client.post('/workshop/save', json={'title': '作品A'}, headers=headers)
        assert ar.status_code == 200
        artwork_id = ar.get_json()['data']['id']

        # 预置初始分析值，验证失败调用不会覆盖
        with app.app_context():
            art = db.session.get(Artwork, artwork_id)
            art.style_analysis = {'style': 'initial'}
            db.session.commit()

        resp = client.post('/ai/analyze-style', json={
            'input_url': _create_image(app),
            'artwork_id': artwork_id,
        }, headers=headers)
        assert resp.status_code == 503

        with app.app_context():
            task = self._latest_task(app)
            assert task.status == 'FAILED'
            assert task.error_message
            assert AITask.query.filter(AITask.status == 'PENDING').count() == 0
            art = db.session.get(Artwork, artwork_id)
            assert art.style_analysis == {'style': 'initial'}  # 失败不写入/不覆盖
