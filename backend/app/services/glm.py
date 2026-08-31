# ============================================================
# 智绘锡承 - GLM 多模态 Provider（空骨架）
# 位置: backend/app/services/glm.py（阶段9 AI 基础设施）
#
# ⚠️ 本阶段不实现真实 GLM 调用:
#   - 不实现图片理解 / 风格识别真实调用
#   - 真实接入方式待 API 权限与官方文档确认后单独实现
#   - 若指定 AI_PROVIDER=glm 但未实现，工厂返回明确配置错误
# ============================================================
from app.services.base import BaseAIService, UnconfiguredProviderError


class GLMService(BaseAIService):
    """GLM 多模态 Provider（空骨架，未实现）"""

    provider_name = 'glm'

    def generate_3d(self, task):
        raise UnconfiguredProviderError(
            'glm Provider 尚未实现，请使用 AI_PROVIDER=mock'
        )

    def analyze_style(self, task):
        raise UnconfiguredProviderError(
            'glm Provider 尚未实现，请使用 AI_PROVIDER=mock'
        )

    def query_status(self, task):
        raise UnconfiguredProviderError(
            'glm Provider 尚未实现，请使用 AI_PROVIDER=mock'
        )
