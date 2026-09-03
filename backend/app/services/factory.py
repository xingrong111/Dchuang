# ============================================================
# 智绘锡承 - AI Service 工厂
# 位置: backend/app/services/factory.py（阶段9 AI 基础设施 / 阶段16-C 运行治理）
#
# 规则（严格）:
#   1. AI_PROVIDER=mock      → MockProvider（显式启用）
#   2. AI_PROVIDER=hunyuan   → HunyuanService 真实 3D Provider（阶段12-B2；
#                              凭据缺失 → 明确错误）
#   3. AI_PROVIDER=glm       → GLMService 真实实现（阶段11-B；Key 缺失 → 明确错误）
#   4. AI_PROVIDER 未配置    → 开发环境默认 mock，但必须明确记录 provider=mock
#
# 阶段16-C 运行治理:
#   - get_ai_service(provider=None): 支持显式指定 provider（内部/管理调用）
#   - enabled 校验: 若 AIProviderConfig 中存在该 name 且 enabled=False →
#     AIServiceError('该 AI 模型已停用')；记录不存在 → 保持兼容（历史 provider
#     不受影响）；DB 配置优先于默认（覆盖 AI_PROVIDER 语义）。
#
# 禁止:
#   - 因 API Key 缺失而自动静默降级为 Mock（用户不能误以为自己调用了真实 AI）
#   - 指定真实 Provider 但未实现时返回 Mock
# ============================================================
from flask import current_app
from sqlalchemy.exc import OperationalError

from app.models.ai_provider import AIProviderConfig
from app.services.base import UnconfiguredProviderError
from app.services.mock import MockProvider
from app.services.hunyuan import HunyuanService
from app.services.glm import GLMService
from app.utils.exceptions import AIServiceError


def _check_provider_enabled(name):
    """阶段16-C: 运行时 enabled 治理（DB 配置优先；无记录保持兼容）

    AIProviderConfig 存在且 enabled=False → 禁止调用
    兼容性: 表不存在（旧库未跑 16-B migration）或查询异常 → 视同无记录，
    不阻断历史调用（与"记录不存在不拦截"一致）。
    """
    try:
        config = AIProviderConfig.query.filter_by(name=name).first()
    except OperationalError:
        # 表不存在（未执行 ai_providers migration）→ 兼容旧环境
        config = None
    if config is not None and not config.enabled:
        raise AIServiceError(f'该 AI 模型已停用: {name}')


def get_ai_service(provider=None):
    """根据配置/参数选择 Provider（阶段16-C 支持显式 provider）

    Args:
        provider: 可选，显式指定 provider 名（内部调用/管理重试）；None → AI_PROVIDER 配置

    Returns:
        BaseAIService: 选中的 Provider 实例

    Raises:
        UnconfiguredProviderError: 指定真实 Provider 但未实现 / Key 缺失
        AIServiceError: 该 Provider 在 AIProviderConfig 中被停用（enabled=False）
    """
    selected = (provider or current_app.config.get('AI_PROVIDER') or 'mock').strip().lower()

    # 阶段16-C: 停用治理（配置记录存在即生效；不存在不拦截历史 provider）
    _check_provider_enabled(selected)

    if selected == 'mock':
        # 显式启用 Mock
        return MockProvider()

    if selected == 'hunyuan':
        # 真实 Provider（阶段12-B2）: SecretId/SecretKey 缺失 → 明确错误，不自动 Mock
        secret_id = current_app.config.get('TENCENT_SECRET_ID')
        secret_key = current_app.config.get('TENCENT_SECRET_KEY')
        if not secret_id or not secret_key:
            raise UnconfiguredProviderError(
                'AI_PROVIDER=hunyuan 但未配置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY'
            )
        return HunyuanService()

    if selected == 'glm':
        # 真实 Provider（阶段11-B）: Key 缺失 → 明确错误，不自动 Mock
        api_key = current_app.config.get('GLM_API_KEY')
        if not api_key:
            raise UnconfiguredProviderError(
                'AI_PROVIDER=glm 但未配置 GLM_API_KEY'
            )
        return GLMService()

    raise UnconfiguredProviderError(f'未知 AI Provider: {selected}')
