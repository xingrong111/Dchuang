# ============================================================
# 智绘锡承 - 腾讯混元生3D SDK 封装服务测试（阶段12-B1）
# 覆盖: 初始化 / 配置读取 / 凭据缺失报错 / 三个方法结构与请求构造
# 本阶段仅封装：绝不调用真实腾讯 API、不消耗积分
# 凭据全部使用假值（test-fake-*），严禁真实 SecretId/SecretKey
# ============================================================
import base64
import os

import pytest

from app.services.base import UnconfiguredProviderError
from app.utils.exceptions import AIServiceError


@pytest.fixture
def app(tmp_path):
    """测试应用（UPLOAD_FOLDER 临时目录 + 假腾讯凭据）"""
    from app import create_app

    app = create_app('testing')
    uploads = tmp_path / 'uploads'
    uploads.mkdir(exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(uploads)
    # 假凭据（非真实），强制覆盖任何环境值，测试与 .env 隔离
    app.config['TENCENT_SECRET_ID'] = 'test-fake-secret-id'
    app.config['TENCENT_SECRET_KEY'] = 'test-fake-secret-key'
    app.config['TENCENT_HUNYUAN_REGION'] = 'ap-guangzhou'
    app.config['HUNYUAN_3D_MODEL'] = ''
    return app


def _png_bytes():
    return (
        b'\x89PNG\r\n\x1a\n'
        b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
        b'\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
        b'\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def _create_image(app, name='hunyuan3d.png'):
    """在 UPLOAD_FOLDER 创建图片，返回内部 URL"""
    d = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name)
    with open(path, 'wb') as f:
        f.write(_png_bytes())
    return f'/api/static/uploads/images/{name}'


class TestHunyuan3DService:
    """Hunyuan3DService 初始化与配置读取"""

    def test_init_success(self, app):
        """配置假凭据后服务可正常初始化（SDK Client 就绪）"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            assert svc.provider_name == 'hunyuan'
            assert svc.client is not None

    def test_init_reads_config(self, app):
        """环境变量（config）读取正常：SecretId/SecretKey/Region"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            assert svc.secret_id == 'test-fake-secret-id'
            assert svc.secret_key == 'test-fake-secret-key'
            assert svc.region == 'ap-guangzhou'
            assert svc.model == ''  # HUNYUAN_3D_MODEL 未配置时为空

    def test_init_with_explicit_credentials(self, app):
        """显式传参凭据优先于 config"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService(
                secret_id='explicit-id', secret_key='explicit-key', region='na-ashburn'
            )
            assert svc.secret_id == 'explicit-id'
            assert svc.secret_key == 'explicit-key'
            assert svc.region == 'na-ashburn'

    def test_init_missing_credentials_raises(self, app, monkeypatch):
        """SecretId/SecretKey 缺失 → UnconfiguredProviderError（不降级/不伪造）"""
        from app.services.hunyuan3d import Hunyuan3DService

        monkeypatch.setitem(app.config, 'TENCENT_SECRET_ID', '')
        monkeypatch.setitem(app.config, 'TENCENT_SECRET_KEY', '')
        with app.app_context():
            with pytest.raises(UnconfiguredProviderError):
                Hunyuan3DService()


class TestHunyuan3DMethods:
    """三个方法的结构与请求构造（仅封装，不提交）"""

    def test_methods_exist(self, app):
        """方法结构存在：create_text_to_3d / create_image_to_3d / query_task"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            assert hasattr(svc, 'create_text_to_3d') and callable(svc.create_text_to_3d)
            assert hasattr(svc, 'create_image_to_3d') and callable(svc.create_image_to_3d)
            assert hasattr(svc, 'query_task') and callable(svc.query_task)

    def test_create_text_to_3d_request(self, app):
        """文生3D 构造提交请求：GenerateType='Normal'(string) + Prompt"""
        from tencentcloud.ai3d.v20250513 import models

        from app.services.hunyuan3d import GENERATE_TYPE_DEFAULT, Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            req = svc.create_text_to_3d('生成一个惠山泥人阿福')
            assert isinstance(req, models.SubmitHunyuanTo3DProJobRequest)
            assert isinstance(req.GenerateType, str)  # 12-B3-C 防回归: 必须 string
            assert req.GenerateType == GENERATE_TYPE_DEFAULT == 'Normal'
            assert req.Prompt == '生成一个惠山泥人阿福'

    def test_create_text_to_3d_strips_prompt(self, app):
        """prompt 首尾空白被清洗"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            req = svc.create_text_to_3d('  生成一个茶壶  ')
            assert req.Prompt == '生成一个茶壶'

    def test_create_text_to_3d_empty_prompt_raises(self, app):
        """空/空白 prompt → AIServiceError"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            with pytest.raises(AIServiceError):
                svc.create_text_to_3d('')
            with pytest.raises(AIServiceError):
                svc.create_text_to_3d('   ')

    def test_create_image_to_3d_request(self, app):
        """图生3D 构造提交请求：GenerateType='Normal'(string) + ImageBase64 内联（免 COS）"""
        from tencentcloud.ai3d.v20250513 import models

        from app.services.hunyuan3d import GENERATE_TYPE_DEFAULT, Hunyuan3DService

        input_url = _create_image(app)
        with app.app_context():
            svc = Hunyuan3DService()
            req = svc.create_image_to_3d(input_url)
            assert isinstance(req, models.SubmitHunyuanTo3DProJobRequest)
            assert isinstance(req.GenerateType, str)  # 12-B3-C 防回归: 必须 string
            assert req.GenerateType == GENERATE_TYPE_DEFAULT == 'Normal'
            # ImageBase64 为纯 Base64（无 data: 前缀），可解码且等于原图
            assert req.ImageBase64
            assert 'data:' not in req.ImageBase64
            assert base64.b64decode(req.ImageBase64) == _png_bytes()

    def test_create_image_to_3d_missing_file_raises(self, app):
        """图片不存在 → AIServiceError（图片读取失败）"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            with pytest.raises(AIServiceError):
                svc.create_image_to_3d('/api/static/uploads/images/nonexistent.png')

    def test_create_image_to_3d_empty_raises(self, app):
        """空 image_url → AIServiceError"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            with pytest.raises(AIServiceError):
                svc.create_image_to_3d('')

    def test_query_task_done_string_status_glb_preferred(self, app, monkeypatch):
        """12-B3-C 修正: 真实字符串 Status='DONE'（实测）+ OBJ/GLB 双产物 → SUCCESS + GLB 优先"""
        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 'DONE'          # 真实 API 实测字符串状态
            resp.ErrorCode = ''
            resp.ErrorMessage = ''
            obj = type('FakeFile3D', (), {})()
            obj.Type = 'OBJ'
            obj.Url = 'https://cos.example.com/model.obj'
            glb = type('FakeFile3D', (), {})()
            glb.Type = 'GLB'
            glb.Url = 'https://cos.example.com/model.glb'
            resp.ResultFile3Ds = [obj, glb]
            return resp

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task('job-123456')

        assert result['status'] == 'SUCCESS'          # 'DONE' → SUCCESS
        assert result['result_url'] == 'https://cos.example.com/model.glb'  # GLB 优先
        assert result['error_message'] is None

    def test_query_task_done_no_glb_fallback_first(self, app, monkeypatch):
        """12-B3-C 修正: 'DONE' 且仅 OBJ 产物 → SUCCESS + 回退首个有效 Url"""
        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 'DONE'
            resp.ErrorCode = ''
            resp.ErrorMessage = ''
            obj = type('FakeFile3D', (), {})()
            obj.Type = 'OBJ'
            obj.Url = 'https://cos.example.com/model.obj'
            resp.ResultFile3Ds = [obj]
            return resp

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task('job-123456')

        assert result['status'] == 'SUCCESS'
        assert result['result_url'] == 'https://cos.example.com/model.obj'

    def test_query_task_done_string_no_files(self, app, monkeypatch):
        """12-B3-C 修正: 'DONE' 但无产物 → SUCCESS + result_url=None（不崩溃）"""
        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 'DONE'
            resp.ErrorCode = ''
            resp.ErrorMessage = ''
            resp.ResultFile3Ds = []
            return resp

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task('job-123456')
        assert result['status'] == 'SUCCESS'
        assert result['result_url'] is None

    def test_query_task_success(self, app, monkeypatch):
        """阶段12-B3-B: 真实查询成功（Status=3 + 产物 URL）→ 统一 dict"""
        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 3
            resp.ErrorCode = 'Success'
            resp.ErrorMessage = None
            file3d = type('FakeFile3D', (), {})()
            file3d.Type = 'GLB'
            file3d.Url = 'https://model-bucket.cos.ap-guangzhou.myqcloud.com/xxx.glb'
            file3d.PreviewImageUrl = 'https://.../preview.png'
            resp.ResultFile3Ds = [file3d]
            return resp

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task('job-123456')

        assert result['status'] == 'SUCCESS'
        assert result['result_url'].endswith('.glb')
        assert result['error_message'] is None

    def test_query_task_running(self, app, monkeypatch):
        """真实查询生成中（Status=2）→ RUNNING"""
        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 2
            resp.ErrorCode = 'Success'
            resp.ErrorMessage = None
            resp.ResultFile3Ds = []
            return resp

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task('job-123456')
        assert result['status'] == 'RUNNING'
        assert result['result_url'] is None

    def test_query_task_failed(self, app, monkeypatch):
        """真实查询失败（Status=4 + ErrorMessage）→ FAILED + error_message"""
        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 4
            resp.ErrorCode = 'FailedOperation'
            resp.ErrorMessage = '生成失败：提示词违规'
            resp.ResultFile3Ds = []
            return resp

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task('job-123456')
        assert result['status'] == 'FAILED'
        assert '生成失败' in result['error_message']

    def test_query_task_unknown_status_conservative(self, app, monkeypatch):
        """未知状态数值 → 保守 RUNNING（不误判终态）"""
        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 99
            resp.ErrorCode = 'Success'
            resp.ErrorMessage = None
            resp.ResultFile3Ds = []
            return resp

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task('job-123456')
        assert result['status'] == 'RUNNING'

    def test_query_task_sdk_failure_raises(self, app, monkeypatch):
        """SDK 查询异常 → AIServiceError（明确异常）"""
        from tencentcloud.common.exception import TencentCloudSDKException

        from app.services.hunyuan3d import Hunyuan3DService

        def fake_query(request):
            raise TencentCloudSDKException(code='ResourceNotFound', message='任务不存在')

        with app.app_context():
            svc = Hunyuan3DService()
            monkeypatch.setattr(svc.client, 'QueryHunyuanTo3DProJob', fake_query)
            with pytest.raises(AIServiceError) as exc_info:
                svc.query_task('job-missing')
        assert '查询失败' in str(exc_info.value)

    def test_query_task_empty_raises(self, app):
        """空 task_id → AIServiceError"""
        from app.services.hunyuan3d import Hunyuan3DService

        with app.app_context():
            svc = Hunyuan3DService()
            with pytest.raises(AIServiceError):
                svc.query_task('')


class TestHunyuanProvider:
    """阶段12-B2: HunyuanService 接入现有 AI Provider 架构（组合 Hunyuan3DService）"""

    @pytest.fixture
    def cred_app(self, app):
        """带假凭据的应用（HunyuanService 初始化需要）"""
        app.config['TENCENT_SECRET_ID'] = 'test-fake-secret-id'
        app.config['TENCENT_SECRET_KEY'] = 'test-fake-secret-key'
        return app

    @staticmethod
    def _make_task(task_type='text_to_3d', prompt=None, input_url=None):
        """构造内存 AITask（无需 DB）"""
        from app.models.ai_task import AITask

        task = AITask(task_type=task_type, prompt=prompt, input_url=input_url)
        task.status = 'PENDING'
        return task

    def test_provider_registered(self):
        """HunyuanService 是 BaseAIService 子类，provider 名正确（架构注册）"""
        from app.services.base import BaseAIService
        from app.services.hunyuan import HunyuanService

        assert issubclass(HunyuanService, BaseAIService)
        assert HunyuanService.provider_name == 'hunyuan'

    def test_provider_init_with_credentials(self, cred_app):
        """凭据存在 → 初始化成功且组合 SDK 封装层"""
        from app.services.hunyuan import HunyuanService

        with cred_app.app_context():
            svc = HunyuanService()
            assert svc.secret_id == 'test-fake-secret-id'
            assert svc.secret_key == 'test-fake-secret-key'
            assert svc._sdk is not None

    def test_provider_init_missing_credentials_raises(self, app, monkeypatch):
        """无凭据 → UnconfiguredProviderError（不自动 Mock）"""
        from app.services.base import UnconfiguredProviderError
        from app.services.hunyuan import HunyuanService

        monkeypatch.setitem(app.config, 'TENCENT_SECRET_ID', '')
        monkeypatch.setitem(app.config, 'TENCENT_SECRET_KEY', '')
        with app.app_context():
            with pytest.raises(UnconfiguredProviderError):
                HunyuanService()

    def test_provider_interfaces_exist(self, cred_app):
        """统一接口存在: generate_3d / analyze_style / query_status"""
        from app.services.hunyuan import HunyuanService

        with cred_app.app_context():
            svc = HunyuanService()
            assert callable(svc.generate_3d)
            assert callable(svc.analyze_style)
            assert callable(svc.query_status)

    def test_generate_text_to_3d_submit_success(self, cred_app, monkeypatch):
        """阶段12-B3-A: 文生3D 真实提交成功 → JobId + status=RUNNING（参数正确）"""
        from app.services.hunyuan import HunyuanService
        from app.services.hunyuan3d import GENERATE_TYPE_DEFAULT

        captured = {}

        def fake_submit(request):
            captured['request'] = request
            resp = type('FakeSubmitResp', (), {'JobId': 'job-text-123456'})()
            return resp

        task = self._make_task(task_type='text_to_3d', prompt='生成一个惠山泥人阿福')
        with cred_app.app_context():
            svc = HunyuanService()
            monkeypatch.setattr(svc._sdk.client, 'SubmitHunyuanTo3DProJob', fake_submit)
            result = svc.generate_3d(task)

        assert result['status'] == 'RUNNING'
        assert result['external_task_id'] == 'job-text-123456'
        assert result['result_url'] is None
        # 文生3D 参数正确（GenerateType='Normal' string + Prompt）
        req = captured['request']
        assert isinstance(req.GenerateType, str)  # 12-B3-C 防回归: 必须 string
        assert req.GenerateType == GENERATE_TYPE_DEFAULT == 'Normal'
        assert req.Prompt == '生成一个惠山泥人阿福'

    def test_generate_image_to_3d_submit_success(self, cred_app, monkeypatch):
        """阶段12-B3-A: 图生3D 真实提交成功 → JobId + status=RUNNING（参数正确）"""
        from app.services.hunyuan import HunyuanService
        from app.services.hunyuan3d import GENERATE_TYPE_DEFAULT

        captured = {}

        def fake_submit(request):
            captured['request'] = request
            resp = type('FakeSubmitResp', (), {'JobId': 'job-img-654321'})()
            return resp

        input_url = _create_image(cred_app, 'hunyuan_provider.png')
        task = self._make_task(task_type='image_to_3d', input_url=input_url)
        with cred_app.app_context():
            svc = HunyuanService()
            monkeypatch.setattr(svc._sdk.client, 'SubmitHunyuanTo3DProJob', fake_submit)
            result = svc.generate_3d(task)

        assert result['status'] == 'RUNNING'
        assert result['external_task_id'] == 'job-img-654321'
        # 图生3D 参数正确（GenerateType='Normal' string + ImageBase64 纯 Base64 内联 = 原图）
        req = captured['request']
        assert isinstance(req.GenerateType, str)  # 12-B3-C 防回归: 必须 string
        assert req.GenerateType == GENERATE_TYPE_DEFAULT == 'Normal'
        assert req.ImageBase64
        assert 'data:' not in req.ImageBase64
        assert base64.b64decode(req.ImageBase64) == _png_bytes()

    def test_generate_submit_failure_raises(self, cred_app, monkeypatch):
        """阶段12-B3-A: SDK 提交失败 → AIServiceError（明确异常，不伪造成功）"""
        from tencentcloud.common.exception import TencentCloudSDKException

        from app.services.hunyuan import HunyuanService
        from app.utils.exceptions import AIServiceError

        def fake_submit(request):
            raise TencentCloudSDKException(
                code='AuthFailure', message='secret key 无效或权限不足'
            )

        task = self._make_task(task_type='text_to_3d', prompt='生成一个茶壶')
        with cred_app.app_context():
            svc = HunyuanService()
            monkeypatch.setattr(svc._sdk.client, 'SubmitHunyuanTo3DProJob', fake_submit)
            with pytest.raises(AIServiceError) as exc_info:
                svc.generate_3d(task)
        assert '提交失败' in str(exc_info.value)

    def test_generate_submit_response_missing_jobid_raises(self, cred_app, monkeypatch):
        """阶段12-B3-A: 提交响应缺 JobId → AIServiceError"""
        from app.services.hunyuan import HunyuanService
        from app.utils.exceptions import AIServiceError

        def fake_submit(request):
            return type('FakeSubmitResp', (), {'JobId': None})()

        task = self._make_task(task_type='text_to_3d', prompt='生成一个茶壶')
        with cred_app.app_context():
            svc = HunyuanService()
            monkeypatch.setattr(svc._sdk.client, 'SubmitHunyuanTo3DProJob', fake_submit)
            with pytest.raises(AIServiceError) as exc_info:
                svc.generate_3d(task)
        assert 'JobId' in str(exc_info.value)

    def test_generate_text_to_3d_missing_prompt_raises(self, cred_app):
        """文生3D 缺 prompt → AIServiceError（参数错误优先，消息含 prompt）"""
        from app.services.hunyuan import HunyuanService
        from app.utils.exceptions import AIServiceError

        task = self._make_task(task_type='text_to_3d', prompt=None)
        with cred_app.app_context():
            svc = HunyuanService()
            with pytest.raises(AIServiceError) as exc_info:
                svc.generate_3d(task)
        assert 'prompt' in str(exc_info.value)

    def test_generate_image_to_3d_missing_image_raises(self, cred_app):
        """图生3D 图片不存在 → AIServiceError（图片读取失败优先于提交）"""
        from app.services.hunyuan import HunyuanService
        from app.utils.exceptions import AIServiceError

        task = self._make_task(
            task_type='image_to_3d',
            input_url='/api/static/uploads/images/nonexistent.png',
        )
        with cred_app.app_context():
            svc = HunyuanService()
            with pytest.raises(AIServiceError) as exc_info:
                svc.generate_3d(task)
        assert '图片' in str(exc_info.value)

    def test_generate_unsupported_type_raises(self, cred_app):
        """不支持的 task_type → AIServiceError"""
        from app.services.hunyuan import HunyuanService
        from app.utils.exceptions import AIServiceError

        task = self._make_task(task_type='analyze_style')
        with cred_app.app_context():
            svc = HunyuanService()
            with pytest.raises(AIServiceError):
                svc.generate_3d(task)

    def test_analyze_style_not_supported(self, cred_app):
        """analyze_style → UnconfiguredProviderError（风格分析由 GLM 承担）"""
        from app.services.base import UnconfiguredProviderError
        from app.services.hunyuan import HunyuanService

        with cred_app.app_context():
            svc = HunyuanService()
            with pytest.raises(UnconfiguredProviderError):
                svc.analyze_style(None)

    def test_query_status_local_mapping(self, cred_app):
        """query_status 无 JobId 时: 本地状态映射（终态短路 + PENDING/RUNNING 透传）"""
        from app.services.hunyuan import HunyuanService

        with cred_app.app_context():
            svc = HunyuanService()
            t = self._make_task()
            t.status = 'SUCCESS'
            assert svc.query_status(t) == 'SUCCESS'
            t.status = 'FAILED'
            assert svc.query_status(t) == 'FAILED'
            t.status = 'PENDING'
            assert svc.query_status(t) == 'PENDING'
            t.status = 'RUNNING'
            assert svc.query_status(t) == 'RUNNING'

    def test_query_task_real_query_success(self, cred_app, monkeypatch):
        """阶段12-B3-B: query_task 真实查询（Status=3+URL）→ dict SUCCESS"""
        from app.services.hunyuan import HunyuanService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 3
            resp.ErrorCode = 'Success'
            resp.ErrorMessage = None
            file3d = type('FakeFile3D', (), {})()
            file3d.Url = 'https://cos.example.com/model.glb'
            resp.ResultFile3Ds = [file3d]
            return resp

        task = self._make_task(task_type='text_to_3d', prompt='生成紫砂壶')
        task.external_task_id = 'job-abc'
        with cred_app.app_context():
            svc = HunyuanService()
            monkeypatch.setattr(svc._sdk.client, 'QueryHunyuanTo3DProJob', fake_query)
            result = svc.query_task(task)
        assert result['status'] == 'SUCCESS'
        assert result['result_url'] == 'https://cos.example.com/model.glb'

    def test_query_task_missing_jobid_raises(self, cred_app):
        """query_task 缺 JobId → AIServiceError"""
        from app.services.hunyuan import HunyuanService
        from app.utils.exceptions import AIServiceError

        task = self._make_task(task_type='text_to_3d', prompt='生成紫砂壶')
        with cred_app.app_context():
            svc = HunyuanService()
            with pytest.raises(AIServiceError) as exc_info:
                svc.query_task(task)
        assert 'JobId' in str(exc_info.value)

    def test_query_status_real_query(self, cred_app, monkeypatch):
        """阶段12-B3-B: query_status 携带 JobId → 真实查询返回腾讯状态"""
        from app.services.hunyuan import HunyuanService

        def fake_query(request):
            resp = type('FakeQueryResp', (), {})()
            resp.Status = 3
            resp.ErrorCode = 'Success'
            resp.ErrorMessage = None
            resp.ResultFile3Ds = []
            return resp

        task = self._make_task(task_type='text_to_3d', prompt='生成紫砂壶')
        task.external_task_id = 'job-abc'
        with cred_app.app_context():
            svc = HunyuanService()
            monkeypatch.setattr(svc._sdk.client, 'QueryHunyuanTo3DProJob', fake_query)
            assert svc.query_status(task) == 'SUCCESS'

    def test_query_status_query_failure_conservative(self, cred_app, monkeypatch):
        """query_status 查询失败 → 保守 RUNNING（轮询重试，不误判终态）"""
        from tencentcloud.common.exception import TencentCloudSDKException

        from app.services.hunyuan import HunyuanService

        def fake_query(request):
            raise TencentCloudSDKException(code='AuthFailure', message='凭据无效')

        task = self._make_task(task_type='text_to_3d', prompt='生成紫砂壶')
        task.external_task_id = 'job-abc'
        with cred_app.app_context():
            svc = HunyuanService()
            monkeypatch.setattr(svc._sdk.client, 'QueryHunyuanTo3DProJob', fake_query)
            assert svc.query_status(task) == 'RUNNING'
