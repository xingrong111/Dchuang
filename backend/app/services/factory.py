# ============================================================
# 智绘锡承 - AI Service 工厂
# 位置: backend/app/services/factory.py（阶段9 AI 基础设施）
#
# 规则（严格）:
#   1. AI_PROVIDER=mock      → MockProvider（显式启用）
#   2. AI_PROVIDER=hunyuan   → HunyuanService 真实 3D Provider（阶段12-B2；
#                              凭据缺失 → 明确错误）
#   3. AI_PROVIDER=glm       → GLMService 真实实现（阶段11-B；Key 缺失 → 明确错误）
#   4. AI_PROVIDER 未配置    → 开发环境默认 mock，但必须明确记录 provider=mock
#
# 禁止:
#   - 因 API Key 缺失而自动静默降级为 Mock（用户不能误以为自己调用了真实 AI）
#   - 指定真实 Provider 但未实现时返回 Mock
# ============================================================
from flask import current_app

from app.services.base import UnconfiguredProviderError
from app.services.mock import MockProvider
from app.services.hunyuan import HunyuanService
from app.services.glm import GLMService


def get_ai_service():
    """根据配置 AI_PROVIDER 选择 Provider

    Returns:
        BaseAIService: 选中的 Provider 实例

    Raises:
        UnconfiguredProviderError: 指定真实 Provider 但未实现 / Key 缺失
    """
    provider = (current_app.config.get('AI_PROVIDER') or 'mock').strip().lower()

    if provider == 'mock':
        # 显式启用 Mock
        return MockProvider()

    if provider == 'hunyuan':
        # 真实 Provider（阶段12-B2）: SecretId/SecretKey 缺失 → 明确错误，不自动 Mock
        secret_id = current_app.config.get('TENCENT_SECRET_ID')
        secret_key = current_app.config.get('TENCENT_SECRET_KEY')
        if not secret_id or not secret_key:
            raise UnconfiguredProviderError(
                'AI_PROVIDER=hunyuan 但未配置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY'
            )
        return HunyuanService()

    if provider == 'glm':
        # 真实 Provider（阶段11-B）: Key 缺失 → 明确错误，不自动 Mock
        api_key = current_app.config.get('GLM_API_KEY')
        if not api_key:
            raise UnconfiguredProviderError(
                'AI_PROVIDER=glm 但未配置 GLM_API_KEY'
            )
        return GLMService()

    raise UnconfiguredProviderError(f'未知 AI Provider: {provider}')
