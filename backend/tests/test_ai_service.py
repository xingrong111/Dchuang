# ============================================================
# 智绘锡承 - AI 状态机与 Provider 测试（阶段9）
# 覆盖: 状态转换 / MockProvider / Service 工厂
# 全部使用 Mock，禁止真实 API 调用
# ============================================================
import pytest


class TestStatusMachine:
    """AI 状态机测试"""

    def _make_task(self, status='PENDING'):
        """构造最小任务对象"""
        from app.models.ai_task import AITask

        task = AITask(task_type='text_to_3d')
        task.status = status
        return task

    def test_pending_to_running(self):
        from app.utils.ai_status import transition_status, RUNNING

        task = self._make_task('PENDING')
        transition_status(task, RUNNING)
        assert task.status == 'RUNNING'

    def test_pending_to_success(self):
        from app.utils.ai_status import transition_status, SUCCESS

        task = self._make_task('PENDING')
        transition_status(task, SUCCESS)
        assert task.status == 'SUCCESS'

    def test_pending_to_failed(self):
        from app.utils.ai_status import transition_status, FAILED

        task = self._make_task('PENDING')
        transition_status(task, FAILED)
        assert task.status == 'FAILED'

    def test_running_to_running(self):
        from app.utils.ai_status import transition_status, RUNNING

        task = self._make_task('RUNNING')
        transition_status(task, RUNNING)
        assert task.status == 'RUNNING'

    def test_running_to_success(self):
        from app.utils.ai_status import transition_status, SUCCESS

        task = self._make_task('RUNNING')
        transition_status(task, SUCCESS)
        assert task.status == 'SUCCESS'

    def test_running_to_failed(self):
        from app.utils.ai_status import transition_status, FAILED

        task = self._make_task('RUNNING')
        transition_status(task, FAILED)
        assert task.status == 'FAILED'

    def test_success_cannot_revert(self):
        """SUCCESS → 任何状态 必须失败"""
        from app.utils.ai_status import transition_status, RUNNING
        from app.utils.exceptions import ValidationError

        task = self._make_task('SUCCESS')
        with pytest.raises(ValidationError):
            transition_status(task, RUNNING)
        with pytest.raises(ValidationError):
            transition_status(task, 'PENDING')
        # 状态未被修改
        assert task.status == 'SUCCESS'

    def test_failed_cannot_revert(self):
        """FAILED → 任何状态 必须失败"""
        from app.utils.ai_status import transition_status, RUNNING
        from app.utils.exceptions import ValidationError

        task = self._make_task('FAILED')
        with pytest.raises(ValidationError):
            transition_status(task, SUCCESS if False else 'SUCCESS')
        with pytest.raises(ValidationError):
            transition_status(task, RUNNING)
        assert task.status == 'FAILED'

    def test_invalid_target_status(self):
        """非法目标状态 → 失败"""
        from app.utils.ai_status import transition_status
        from app.utils.exceptions import ValidationError

        task = self._make_task('PENDING')
        with pytest.raises(ValidationError):
            transition_status(task, 'NOT_A_STATUS')


class TestMockProvider:
    """MockProvider 测试"""

    def _make_task(self, prompt='生成一个泥人', task_type='text_to_3d', input_url=None):
        from app.models.ai_task import AITask

        return AITask(prompt=prompt, task_type=task_type, input_url=input_url)

    def test_generate_success(self):
        """Mock 生成成功: external_task_id + result_url"""
        from app.services.mock import MockProvider

        provider = MockProvider()
        task = self._make_task()
        result = provider.generate_3d(task)
        assert result['status'] == 'SUCCESS'
        assert result['external_task_id']
        assert result['result_url'].startswith('/api/static/uploads/models/mock')
        assert result['error_message'] is None

    def test_generate_failed(self):
        """Mock 生成失败（mock_behavior='fail'）"""
        from app.services.mock import MockProvider

        provider = MockProvider(mock_behavior='fail')
        task = self._make_task(prompt='正常用户输入不应触发失败')
        result = provider.generate_3d(task)
        assert result['status'] == 'FAILED'
        assert result['error_message']

    def test_generate_not_fooled_by_prompt_keyword(self):
        """正常用户输入含 'fail' 单词不应触发失败（阶段10 A4）"""
        from app.services.mock import MockProvider

        provider = MockProvider()  # 默认 success
        task = self._make_task(prompt='This model should not fail')
        result = provider.generate_3d(task)
        assert result['status'] == 'SUCCESS'  # 不再因 prompt 含 fail 误判

    def test_analyze_style_success(self):
        """Mock 风格分析: style + features + report"""
        from app.services.mock import MockProvider

        provider = MockProvider()
        task = self._make_task(task_type='analyze_style', input_url='/api/static/uploads/images/x.png')
        result = provider.analyze_style(task)
        assert result['status'] == 'SUCCESS'
        assert result['style']
        assert isinstance(result['features'], list)
        assert isinstance(result['report'], dict)

    def test_analyze_style_failed(self):
        from app.services.mock import MockProvider

        provider = MockProvider(mock_behavior='fail')
        task = self._make_task(task_type='analyze_style', input_url='/api/static/uploads/images/x.png')
        result = provider.analyze_style(task)
        assert result['status'] == 'FAILED'

    def test_query_status(self):
        from app.services.mock import MockProvider

        provider = MockProvider()
        assert provider.query_status(self._make_task()) == 'SUCCESS'
        fail_provider = MockProvider(mock_behavior='fail')
        assert fail_provider.query_status(self._make_task()) == 'FAILED'


class TestServiceFactory:
    """Service 工厂测试"""

    @pytest.fixture
    def app(self):
        from app import create_app

        app = create_app('testing')
        # 阶段11-L: 显式指定 Mock，隔离 backend/.env 的 AI_PROVIDER（load_dotenv 会加载真实配置）
        app.config['AI_PROVIDER'] = 'mock'
        return app

    def test_factory_mock(self, app):
        """AI_PROVIDER=mock → MockProvider"""
        from app.services.factory import get_ai_service
        from app.services.mock import MockProvider

        with app.app_context():
            service = get_ai_service()
            assert isinstance(service, MockProvider)
            assert service.provider_name == 'mock'

    def test_factory_hunyuan_without_key_error(self, app):
        """AI_PROVIDER=hunyuan 但 SecretId/SecretKey 缺失 → 明确错误（不自动 Mock）"""
        from app.services.factory import get_ai_service
        from app.services.base import UnconfiguredProviderError

        app.config['AI_PROVIDER'] = 'hunyuan'
        app.config['TENCENT_SECRET_ID'] = ''
        app.config['TENCENT_SECRET_KEY'] = ''
        with app.app_context():
            with pytest.raises(UnconfiguredProviderError):
                get_ai_service()

    def test_factory_hunyuan_with_credentials(self, app):
        """阶段12-B2: AI_PROVIDER=hunyuan + 凭据存在 → HunyuanService（真实 Provider）"""
        from app.services.factory import get_ai_service
        from app.services.hunyuan import HunyuanService

        app.config['AI_PROVIDER'] = 'hunyuan'
        app.config['TENCENT_SECRET_ID'] = 'test-fake-secret-id'
        app.config['TENCENT_SECRET_KEY'] = 'test-fake-secret-key'
        with app.app_context():
            service = get_ai_service()
            assert isinstance(service, HunyuanService)
            assert service.provider_name == 'hunyuan'

    def test_factory_glm_without_key_error(self, app):
        """AI_PROVIDER=glm 但 Key 缺失 → 明确错误（不自动 Mock）"""
        from app.services.factory import get_ai_service
        from app.services.base import UnconfiguredProviderError

        app.config['AI_PROVIDER'] = 'glm'
        app.config['GLM_API_KEY'] = ''
        with app.app_context():
            with pytest.raises(UnconfiguredProviderError):
                get_ai_service()

    def test_factory_unknown_provider(self, app):
        """未知 Provider → 明确错误"""
        from app.services.factory import get_ai_service
        from app.services.base import UnconfiguredProviderError

        app.config['AI_PROVIDER'] = 'unknown_xyz'
        with app.app_context():
            with pytest.raises(UnconfiguredProviderError):
                get_ai_service()
