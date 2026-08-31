# ============================================================
# 智绘锡承 - AI Provider 基础服务
# 位置: backend/app/services/base.py（阶段9 AI 基础设施）
#
# 职责边界:
#   - Route (api/v1/ai.py): 参数校验、认证、组装 APIResponse
#   - Service (本模块 + 具体 Provider): 调用 Provider、状态流转、持久化
#   - Provider (mock/hunyuan/glm): 与第三方 AI API 通信
#
# BaseAIService 是统一 Provider 接口:
#   - 不包含 Flask Route
#   - 不直接返回 HTTP Response（返回结构化 dict 或更新任务对象）
#   - 具体 Provider 实现细节与 API 层完全分离
#
# 真实 Provider（hunyuan/glm）本阶段仅空骨架:
#   - 明确抛出 NotImplemented / 配置错误
#   - 不伪造真实 API 调用，不实现签名
# ============================================================
from app.utils.exceptions import AIServiceError


class BaseAIService:
    """AI Provider 统一接口（抽象基类）

    子类需实现: generate_3d / analyze_style / query_status
    """

    provider_name = 'base'

    # ------------------------------------------------------------
    # 必须由子类实现
    # ------------------------------------------------------------
    def generate_3d(self, task):
        """执行 3D 生成任务（文生3D / 图生3D）

        Args:
            task: AITask 实例（含 prompt / input_url / task_type 等）

        Returns:
            dict: {'status': ..., 'external_task_id': ..., 'result_url': ...,
                   'error_message': ...}

        子类实现时更新 task 状态（通过状态机），不直接返回 HTTP。
        """
        raise NotImplementedError('generate_3d 未实现')

    def analyze_style(self, task):
        """执行风格分析任务

        Args:
            task: AITask 实例（含 input_url）

        Returns:
            dict: {'status': ..., 'style': ..., 'features': [...],
                   'report': {...}, 'error_message': ...}
        """
        raise NotImplementedError('analyze_style 未实现')

    def query_status(self, task):
        """查询外部任务状态（异步模式）

        Args:
            task: AITask 实例（含 external_task_id）

        Returns:
            str: 最新状态（PENDING/RUNNING/SUCCESS/FAILED）
        """
        raise NotImplementedError('query_status 未实现')


class UnconfiguredProviderError(AIServiceError):
    """Provider 配置错误（如指定真实 Provider 但 Key 缺失/未实现）

    注意: AIServiceError.__init__ 仅接受 message（code 固定 503，由父类设定）
    """

    def __init__(self, message='AI Provider 配置错误'):
        super().__init__(message=message)
