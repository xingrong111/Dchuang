# ============================================================
# 智绘锡承 - 腾讯混元 AI Provider（空骨架）
# 位置: backend/app/services/hunyuan.py（阶段9 AI 基础设施）
#
# ⚠️ 本阶段不实现真实 HY-3D 调用:
#   - 不实现 HMAC 签名 / SecretKey 签名 / SDK 调用
#   - 真实接入方式待 API 权限与官方文档确认后单独实现
#   - 若指定 AI_PROVIDER=hunyuan 但未实现，工厂返回明确配置错误
# ============================================================
from app.services.base import BaseAIService, UnconfiguredProviderError


class HunyuanService(BaseAIService):
    """腾讯混元 Provider（空骨架，未实现）"""

    provider_name = 'hunyuan'

    def generate_3d(self, task):
        raise UnconfiguredProviderError(
            'hunyuan Provider 尚未实现，请使用 AI_PROVIDER=mock'
        )

    def analyze_style(self, task):
        raise UnconfiguredProviderError(
            'hunyuan Provider 尚未实现，请使用 AI_PROVIDER=mock'
        )

    def query_status(self, task):
        raise UnconfiguredProviderError(
            'hunyuan Provider 尚未实现，请使用 AI_PROVIDER=mock'
        )
