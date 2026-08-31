# ============================================================
# 智绘锡承 - Mock AI Provider
# 位置: backend/app/services/mock.py（阶段9 AI 基础设施）
#
# MockProvider 用途:
#   - 单元测试（可控成功/失败/状态变化）
#   - 本地开发 / 演示（无真实 API Key 时可用）
#
# 行为说明:
#   - 默认模拟 PENDING → RUNNING → SUCCESS 完整流程
#   - 可通过任务 prompt 中的 "FAIL" 关键字触发失败（测试可控）
#   - 成功时提供模拟 external_task_id 与 result_url
#   - 返回结构化结果（3D 生成 / 风格分析），但【不伪装成真实 AI Provider 响应】
#   - 可通过 query_status 模拟异步轮询（外部任务 ID 固定返回 SUCCESS）
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

    def _should_fail(self, task):
        """测试可控: prompt 含 FAIL 关键字 → 模拟失败"""
        prompt = (task.prompt or '').upper()
        return 'FAIL' in prompt

    def generate_3d(self, task):
        """模拟 3D 生成（默认成功，prompt 含 FAIL 时失败）"""
        if self._should_fail(task):
            return {
                'status': 'FAILED',
                'error_message': 'MockProvider 模拟生成失败（prompt 含 FAIL）',
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
        if self._should_fail(task):
            return {
                'status': 'FAILED',
                'error_message': 'MockProvider 模拟风格分析失败（prompt 含 FAIL）',
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
        if self._should_fail(task):
            return 'FAILED'
        # Mock 外部任务一旦创建即视为成功
        return 'SUCCESS'
