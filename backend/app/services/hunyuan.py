# ============================================================
# 智绘锡承 - 腾讯混元 AI Provider（阶段12-B2: 接入 Hunyuan3DService）
# 位置: backend/app/services/hunyuan.py
#
# 定位:
#   - HunyuanService 是面向现有 AI Provider 架构（BaseAIService）的统一实现，
#     内部组合阶段12-B1 的 SDK 封装层 Hunyuan3DService（腾讯云 AI3D 产品）
#   - 职责边界与 GLMService 一致: Route(ai.py) → get_ai_service() →
#     HunyuanService.generate_3d/query_status → Hunyuan3DService(SDK 封装)
#
# 阶段状态:
#   - 12-B2: Provider 注册 + 工厂创建 + 凭据校验 + 参数/请求构造链完整；
#     真实提交/查询（client.SubmitHunyuanTo3DProJob / Query...）在阶段12-B3
#     受控联调时启用 —— 本阶段绝不调用腾讯 API、不消耗积分
#   - analyze_style: 混元不承担风格分析（由 GLM Provider 负责）→ 明确不支持
#
# 配置（backend/.env，严禁提交真实值）:
#   TENCENT_SECRET_ID / TENCENT_SECRET_KEY（凭据缺失 → 明确错误，不自动 Mock）
# ============================================================
from app.services.base import BaseAIService, UnconfiguredProviderError
from app.services.hunyuan3d import Hunyuan3DService
from app.utils.exceptions import AIServiceError


class HunyuanService(BaseAIService):
    """腾讯混元 Provider（3D 生成，SDK 封装层已接入）"""

    provider_name = 'hunyuan'

    def __init__(self):
        """初始化（读取凭据并构建 SDK 封装；凭据缺失立即报错，禁止自动 Mock）"""
        from flask import current_app

        self.secret_id = current_app.config.get('TENCENT_SECRET_ID') or ''
        self.secret_key = current_app.config.get('TENCENT_SECRET_KEY') or ''
        if not self.secret_id or not self.secret_key:
            raise UnconfiguredProviderError(
                'AI_PROVIDER=hunyuan 但未配置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY'
            )

        # 复用 12-B1 SDK 封装服务（凭据已校验；Client 惰性构造，不联网）
        self._sdk = Hunyuan3DService(
            secret_id=self.secret_id, secret_key=self.secret_key
        )
        # 阶段13-B3: model 元数据 —— 反映实际生成模型（HUNYUAN_3D_MODEL 配置或 hunyuan-3d）。
        # 注意: 请求侧 Model 字段用 _sdk.model（配置原值，空则腾讯服务端默认），
        # 此处展示名仅用于 AITask.model 元数据记录
        self.model = current_app.config.get('HUNYUAN_3D_MODEL') or 'hunyuan-3d'

    def generate_3d(self, task):
        """3D 生成（文生3D / 图生3D）——真实提交（阶段12-B3-A）

        调用链: 参数校验 → SDK 请求构造（12-B1）→ submit_job 真实提交
        （client.SubmitHunyuanTo3DProJob）→ 解析 JobId 返回。

        提交成功后任务为异步执行（腾讯侧生成分钟级），返回 RUNNING
        由上层（_execute_generate_3d）保持任务 RUNNING 并等待后续查询。

        Args:
            task: AITask 实例（task_type: text_to_3d | image_to_3d；
                  text_to_3d 需 prompt；image_to_3d 需 input_url）

        Returns:
            dict: {'external_task_id': <腾讯 JobId>, 'status': 'RUNNING',
                   'result_url': None, 'error_message': None}

        Raises:
            AIServiceError: 参数非法 / 图片读取失败 / SDK 提交失败 / 响应缺 JobId
        """
        if task.task_type == 'text_to_3d':
            if not task.prompt or not str(task.prompt).strip():
                raise AIServiceError('文生3D任务必须提供 prompt')
            req = self._sdk.create_text_to_3d(str(task.prompt).strip())
        elif task.task_type == 'image_to_3d':
            if not task.input_url or not str(task.input_url).strip():
                raise AIServiceError('图生3D任务必须提供 input_url')
            # 图片本地 Base64 读取 + 请求构造（图片不存在/超大小/非图片 → AIServiceError）
            req = self._sdk.create_image_to_3d(str(task.input_url).strip())
        else:
            raise AIServiceError(f'hunyuan 不支持的任务类型: {task.task_type}')

        # 真实提交（仅受控联调/真实场景调用，消耗积分）→ 腾讯 JobId
        job_id = self._sdk.submit_job(req)

        return {
            'external_task_id': job_id,
            'status': 'RUNNING',
            'result_url': None,
            'error_message': None,
        }

    def analyze_style(self, task):
        """风格分析由 GLM Provider 承担，混元明确不支持（不伪造）"""
        raise UnconfiguredProviderError('hunyuan Provider 不承担风格分析，请使用 AI_PROVIDER=glm')

    def query_status(self, task):
        """任务状态查询（阶段12-B3-B: 真实 QueryHunyuanTo3DProJob）

        本地终态短路（SUCCESS/FAILED 不再外部查询）；RUNNING/PENDING 且
        有 external_task_id（JobId）→ 真实查询腾讯状态并返回统一内部状态。

        Returns:
            str: 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED'
        """
        if task.status == 'SUCCESS':
            return 'SUCCESS'
        if task.status == 'FAILED':
            return 'FAILED'
        if not task.external_task_id:
            return 'PENDING' if task.status == 'PENDING' else 'RUNNING'
        # 真实查询（失败保守返回 RUNNING，由上层轮询重试，不误判终态）
        try:
            return self._sdk.query_task(task.external_task_id)['status']
        except AIServiceError:
            return 'RUNNING'

    def query_task(self, task):
        """真实查询混元3D异步任务（阶段12-B3-B，供路由轮询刷新）

        Args:
            task: AITask 实例（需 external_task_id = 腾讯 JobId）

        Returns:
            dict: {'status': 'RUNNING'|'SUCCESS'|'FAILED',
                   'result_url': str|None, 'error_message': str|None}

        Raises:
            AIServiceError: 任务缺少 JobId / SDK 查询失败
        """
        if not task.external_task_id:
            raise AIServiceError('任务缺少 external_task_id（JobId），无法查询')
        return self._sdk.query_task(task.external_task_id)
