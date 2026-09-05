# ============================================================
# 智绘锡承 - 腾讯混元生3D SDK 封装服务层
# 位置: backend/app/services/hunyuan3d.py
#
# 定位:
#   - 本类是腾讯云 AI3D 产品（tencentcloud.ai3d.v20250513）的薄封装：
#     统一读取配置、构造 Credential/Client、校验参数、构造提交/查询请求
#   - create_text_to_3d / create_image_to_3d 构造并提交生成请求
#   - query_task 查询异步任务状态并归一化结果
#   - 网络调用仅在对应公开方法被业务层调用时发生
#   - 凭据缺失或调用失败时明确报错，不伪造成功
#
# 配置（backend/.env，严禁提交真实值）:
#   TENCENT_SECRET_ID / TENCENT_SECRET_KEY  腾讯云 CAM API 密钥（成对）
#   TENCENT_HUNYUAN_REGION                  地域（默认 ap-guangzhou）
#   TENCENT_HUNYUAN_ENDPOINT                endpoint（留空用 SDK 默认）
#   HUNYUAN_3D_MODEL                        生3D 模型名（留空用服务端默认）
#
# 异常:
#   - 凭据缺失 → UnconfiguredProviderError（不降级、不伪造）
#   - 参数非法/图片读取失败 → AIServiceError
#
# 注: GenerateType（腾讯云 AI3D SubmitHunyuanTo3DProJob，string 枚举）为
#   【生成风格模式】，非文生/图生区分:
#   - Normal（默认）: 生成带纹理和材质的模型
#   - LowPoly: 生成低面数模型（FaceCount 生效）
#   - Geometry: 生成几何网格模型（EnablePBR 生效）
#   - Sketch: 生成线稿图模型（prompt 与 ImageUrl/ImageBase64 二选一）
#   文生 vs 图生由输入字段决定: 文生只传 Prompt；图生传 ImageBase64/ImageUrl。
# ============================================================
from tencentcloud.ai3d.v20250513 import ai3d_client, models
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile

from app.services.base import UnconfiguredProviderError
from app.utils.exceptions import AIServiceError
from app.utils.files import read_upload_image_as_base64

# 生成风格默认值（string；'Normal' 生成带纹理和材质的常规模型）
# LowPoly/Geometry/Sketch 等风格后续可通过参数扩展（需同步 FaceCount/EnablePBR 等）
GENERATE_TYPE_DEFAULT = 'Normal'

# 腾讯 AI3D 查询任务状态（QueryHunyuanTo3DProJob Response.Status）映射
# 真实联调确认：Status 为字符串枚举，如 'DONE'（已完成）。
# 常见取值: DONE(成功) / FAILED(失败) / RUNNING / PENDING（进行中）
# ⚠️ 若后续真实联调发现新取值，仅需补充本表（集中维护，勿散落硬编码）
TENCENT_JOB_STATUS = {
    # --- 字符串状态（真实 API 实测/官方语义） ---
    'DONE': 'SUCCESS',      # 已完成（产物就绪，实测）
    'SUCCESS': 'SUCCESS',   # 兼容兜底
    'FAILED': 'FAILED',     # 失败
    'RUNNING': 'RUNNING',   # 生成中
    'PENDING': 'RUNNING',   # 排队中 → 统一视为执行中
    # --- 数字状态（历史/兼容防御；未知数值仍保守 RUNNING） ---
    1: 'RUNNING',           # 排队中
    2: 'RUNNING',           # 生成中
    3: 'SUCCESS',           # 成功
    4: 'FAILED',            # 失败
}


def _map_job_status(status_value):
    """腾讯任务状态 → 项目统一状态（未知值保守视为 RUNNING，不误判终态）"""
    return TENCENT_JOB_STATUS.get(status_value, 'RUNNING')


def _pick_result_url(file3ds):
    """从产物列表选择下载地址：优先 Type=GLB（与 Artwork model_format='glb' 一致），
    无 GLB 时回退第一个有效 Url（OBJ/GLTF 等）；无有效产物 → None"""
    first_valid = None
    for item in file3ds or []:
        url = getattr(item, 'Url', None)
        if not url or not str(url).strip():
            continue
        url = str(url).strip()
        if first_valid is None:
            first_valid = url
        file_type = str(getattr(item, 'Type', None) or '').strip().upper()
        if file_type == 'GLB' or url.lower().endswith('.glb'):
            return url
    return first_valid


def _parse_query_response(resp):
    """解析 QueryHunyuanTo3DProJob 响应为统一结构

    Returns:
        dict: {'status': 'RUNNING'|'SUCCESS'|'FAILED',
               'result_url': str|None（成功时取 3D 产物下载地址，GLB 优先）,
               'error_message': str|None}
    """
    status = _map_job_status(getattr(resp, 'Status', None))
    error_message = getattr(resp, 'ErrorMessage', None) or None

    result_url = _pick_result_url(getattr(resp, 'ResultFile3Ds', None))

    return {
        'status': status,
        'result_url': result_url,
        'error_message': error_message,
    }


def _strip_data_url_prefix(data_url):
    """剥离 data:image/<mime>;base64, 前缀，返回纯 Base64（腾讯 ImageBase64 要求）"""
    if isinstance(data_url, str) and ',' in data_url:
        return data_url.split(',', 1)[1]
    return data_url


class Hunyuan3DService:
    """腾讯混元生3D SDK 封装服务

    真实调用链:
        service.create_text_to_3d(prompt)        # → SubmitXxxRequest
        resp = service.client.SubmitHunyuanTo3DProJob(req)
        service.query_task(job_id)               # → QueryXxxRequest
        resp = service.client.QueryHunyuanTo3DProJob(req)
    """

    provider_name = 'hunyuan'

    def __init__(self, secret_id=None, secret_key=None, region=None, endpoint=None):
        """初始化腾讯云凭据与 AI3D 客户端

        凭据优先级: 显式参数 > Flask config（backend/.env 加载）
        凭据缺失 → UnconfiguredProviderError（禁止自动降级/伪造）
        """
        from flask import current_app

        self.secret_id = secret_id or current_app.config.get('TENCENT_SECRET_ID') or ''
        self.secret_key = secret_key or current_app.config.get('TENCENT_SECRET_KEY') or ''
        if not self.secret_id or not self.secret_key:
            raise UnconfiguredProviderError(
                'AI_PROVIDER=hunyuan 但未配置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY'
            )

        self.region = region or current_app.config.get('TENCENT_HUNYUAN_REGION') or 'ap-guangzhou'
        self.endpoint = endpoint or current_app.config.get('TENCENT_HUNYUAN_ENDPOINT') or ''
        self.model = current_app.config.get('HUNYUAN_3D_MODEL') or ''

        cred = credential.Credential(self.secret_id, self.secret_key)
        http_profile = HttpProfile()
        if self.endpoint:
            http_profile.endpoint = self.endpoint
        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        # Client 构造为惰性（不联网），仅完成 SDK 客户端就绪
        self.client = ai3d_client.Ai3dClient(cred, self.region, client_profile)

    def create_text_to_3d(self, prompt):
        """创建文生3D任务（构造提交请求）

        文生 3D: 仅输入 Prompt（GenerateType 为生成风格，默认 'Normal'）

        Args:
            prompt: 生成描述文本（必填）

        Returns:
            SubmitHunyuanTo3DProJobRequest（已填 GenerateType='Normal' + Prompt）

        Raises:
            AIServiceError: prompt 为空/非法
        """
        if not prompt or not str(prompt).strip():
            raise AIServiceError('文生3D必须提供 prompt')

        req = models.SubmitHunyuanTo3DProJobRequest()
        req.GenerateType = GENERATE_TYPE_DEFAULT
        req.Prompt = str(prompt).strip()
        if self.model:
            req.Model = self.model
        return req

    def create_image_to_3d(self, image_url):
        """创建图生3D任务（构造提交请求）

        图生 3D: 仅输入图片（ImageBase64 内联，GenerateType 保持默认 'Normal'）。
        图片经 read_upload_image_as_base64 本地读取并内联为 ImageBase64
        （无需 COS 公网地址；沿用项目 Base64 安全读取与大小/魔数校验）

        Args:
            image_url: 本项目上传图片路径（/api/static/uploads/...）

        Returns:
            SubmitHunyuanTo3DProJobRequest（已填 GenerateType='Normal' + ImageBase64）

        Raises:
            AIServiceError: image_url 为空/图片读取失败（路径非法/不存在/超大小/非图片）
        """
        if not image_url or not str(image_url).strip():
            raise AIServiceError('图生3D必须提供 image_url')

        try:
            data_url = read_upload_image_as_base64(str(image_url).strip())
        except Exception as e:
            # read_upload_image_as_base64 抛 ValidationError；统一转 AIServiceError
            raise AIServiceError(f'图片读取失败: {e}')

        req = models.SubmitHunyuanTo3DProJobRequest()
        req.GenerateType = GENERATE_TYPE_DEFAULT
        req.ImageBase64 = _strip_data_url_prefix(data_url)
        if self.model:
            req.Model = self.model
        return req

    def query_task(self, task_id):
        """真实查询混元3D任务

        调用链: task_id → client.QueryHunyuanTo3DProJob → 解析状态/错误/产物 URL。
        本方法只允许在受控联调/真实场景使用。

        Args:
            task_id: 腾讯云 JobId

        Returns:
            dict: {'status': 'RUNNING'|'SUCCESS'|'FAILED',
                   'result_url': str|None, 'error_message': str|None}

        Raises:
            AIServiceError: task_id 为空 / SDK 查询失败
        """
        if not task_id or not str(task_id).strip():
            raise AIServiceError('查询任务需要提供 task_id')

        req = models.QueryHunyuanTo3DProJobRequest()
        req.JobId = str(task_id).strip()
        try:
            resp = self.client.QueryHunyuanTo3DProJob(req)
        except Exception as e:
            # SDK 异常（含 TencentCloudSDKException：凭据/权限/限流/任务不存在等）
            raise AIServiceError(f'腾讯混元3D任务查询失败: {e}')

        return _parse_query_response(resp)

    def submit_job(self, request):
        """真实提交混元生3D任务

        调用链: request → client.SubmitHunyuanTo3DProJob → 解析 JobId
        本方法只允许在受控联调/真实场景使用（消耗积分）。

        Args:
            request: SubmitHunyuanTo3DProJobRequest（create_text_to_3d /
                     create_image_to_3d 构造产物）

        Returns:
            str: 腾讯云 JobId

        Raises:
            AIServiceError: SDK 调用失败 / 响应缺少 JobId
        """
        try:
            resp = self.client.SubmitHunyuanTo3DProJob(request)
        except Exception as e:
            # SDK 异常（含 TencentCloudSDKException：凭据/权限/限流/参数等）
            raise AIServiceError(f'腾讯混元3D任务提交失败: {e}')

        job_id = getattr(resp, 'JobId', None)
        if not job_id or not str(job_id).strip():
            raise AIServiceError('腾讯混元3D提交响应缺少 JobId')
        return str(job_id).strip()
