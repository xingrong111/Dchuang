# ============================================================
# 智绘锡承 - Mock AI Provider
# 位置: backend/app/services/mock.py
#
# MockProvider 用途:
#   - 单元测试（可控成功/失败）
#   - 本地开发 / 演示（无真实 API Key 时可用）
#
# 行为说明:
#   - 默认模拟 PENDING → RUNNING → SUCCESS 完整流程
#   - 成功时提供模拟 external_task_id 与 result_url
#   - 返回结构化结果（3D 生成 / 风格分析），但【不伪装成真实 AI Provider 响应】
#
# 安全改进:
#   - 【移除】通过 prompt 含 "FAIL" 触发失败的机制（正常用户输入 "should not fail"
#     会被误判失败，且属于"prompt 内容劫持"式后门）
#   - 【改为】实例属性 mock_behavior 控制: 'success'（默认）| 'fail'
#   - 测试通过直接构造 MockProvider(mock_behavior='fail') 或改实例属性控制，
#     API 层无感知、无请求参数污染、生产用户无法通过任何请求字段触发失败
#   - 该控制仅作用于 MockProvider 实例，不影响真实 Provider（hunyuan/glm）
#
# 注意: 本类仅供测试与演示，不调用任何真实 AI API。
# ============================================================
import uuid

from app.services.base import BaseAIService


class MockProvider(BaseAIService):
    """Mock AI Provider（内部测试/演示用）"""

    provider_name = 'mock'

    # 模拟生成结果 URL 前缀（与上传系统路径一致，便于演示）
    MOCK_RESULT_PREFIX = '/api/static/uploads/models/mock'

    # 允许的 mock 行为
    BEHAVIOR_SUCCESS = 'success'
    BEHAVIOR_FAIL = 'fail'

    def __init__(self, mock_behavior=BEHAVIOR_SUCCESS):
        """初始化 Mock Provider

        Args:
            mock_behavior: 'success'（默认，模拟成功）| 'fail'（模拟失败）
                仅供测试/演示控制；API 层不使用请求参数设置。
        """
        if mock_behavior not in (self.BEHAVIOR_SUCCESS, self.BEHAVIOR_FAIL):
            mock_behavior = self.BEHAVIOR_SUCCESS
        self.mock_behavior = mock_behavior

    def _should_fail(self):
        """是否模拟失败（由实例属性控制，与用户输入无关）"""
        return self.mock_behavior == self.BEHAVIOR_FAIL

    def generate_3d(self, task):
        """模拟 3D 生成（默认成功，mock_behavior='fail' 时失败）"""
        if self._should_fail():
            return {
                'status': 'FAILED',
                'error_message': 'MockProvider 模拟生成失败（mock_behavior=fail）',
            }

        # 模拟成功: 提供外部任务 ID + 结果 URL
        return {
            'status': 'SUCCESS',
            'external_task_id': f'mock-{uuid.uuid4().hex[:12]}',
            'result_url': f'{self.MOCK_RESULT_PREFIX}/{uuid.uuid4().hex[:8]}.glb',
            'error_message': None,
        }

    def analyze_style(self, task):
        """模拟风格分析（结构化结果，非真实 AI 响应格式）"""
        if self._should_fail():
            return {
                'status': 'FAILED',
                'error_message': 'MockProvider 模拟风格分析失败（mock_behavior=fail）',
            }

        return {
            'status': 'SUCCESS',
            'style': 'huishan_clay_figure',
            'features': ['传统造型', '色彩鲜艳', '手工质感'],
            'report': {
                'summary': 'Mock 风格分析报告（演示数据）',
                'traditional_score': 0.85,
                'modern_score': 0.10,
                'creative_score': 0.05,
                'recommendations': ['Mock 建议一', 'Mock 建议二'],
            },
            'error_message': None,
        }

    def query_status(self, task):
        """模拟外部任务状态查询（异步模式）"""
        if self._should_fail():
            return 'FAILED'
        # Mock 外部任务一旦创建即视为成功
        return 'SUCCESS'
