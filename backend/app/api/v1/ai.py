# ============================================================
# 智绘锡承 - AI 多模态 API（安全、任务与 Artwork 集成 /
#                          GLM 集成 + Artwork 分析结果持久化 /
#                          AI 异常任务状态一致性）
# 位置: backend/app/api/v1/ai.py
#
# 接口前缀约定: 前端 Vite 代理剥 /api 后转发，本蓝图路由无 /api 前缀:
#   POST /ai/generate-3d        （文生3D / 图生3D 任务创建）
#   GET  /ai/tasks/<task_id>    （任务查询，仅本人）
#   POST /ai/analyze-style      （风格分析，支持可选 artwork_id 持久化）
#
# 认证: 全部使用 get_authenticated_user()（JWT 优先 + Session 兜底；
#        无效 JWT → 401，绝不降级到 Session）
# Provider: 通过 get_ai_service() 工厂选择（mock / hunyuan / glm）
#
# Artwork 集成（方案 B）: 任务 SUCCESS 后才创建 Artwork 并回填 task.artwork_id；
#                         失败不创建（不产生空壳作品）。
#
# analyze-style 支持可选 artwork_id ——
#   - 不传: 保持原行为（纯分析，不触碰 Artwork）
#   - 传且作品属于当前用户: 分析成功后写入 artwork.style_analysis
#   - 传但作品不存在 → 404；属于他人 → 403（禁止越权修改，fail-fast）
#   - 注意: task.artwork_id 不回填（其语义是"方案B成功后创建的作品"，
#     analyze-style 针对的是已存在作品，仅回写分析结果字段）
#
# 安全: input_url 仅允许本项目上传服务产生的 URL（/api/static/uploads/...），
#                   严格前缀 + 路径解析校验，防 SSRF（真实 Provider 主动访问 input_url 时）。
# ============================================================
from urllib.parse import urlparse

from flask import request, current_app

from app.api.v1 import api_bp
from app.extensions import db
from app.models.ai_task import AITask
from app.models.artwork import Artwork
from app.models.credit import (
    CREDIT_TYPE_AI_GENERATE_3D,
    CREDIT_TYPE_AI_ANALYZE_STYLE,
    CREDIT_TYPE_REFUND,
)
from app.services.ai_task import (
    refresh_task,
    fail_timeout_tasks,
    create_artwork_from_task,
)
from app.services.credit import CreditService
from app.services.factory import get_ai_service
from app.utils.ai_status import (
    PENDING,
    RUNNING,
    SUCCESS,
    FAILED,
    transition_status,
)
from app.utils.auth import get_authenticated_user
from app.utils.exceptions import (
    ValidationError,
    AuthenticationError,
    PermissionError_,
    ResourceNotFoundError,
    CreditInsufficientError,
)
from app.utils.response import APIResponse

# 合法任务类型
TASK_TYPES = {'text_to_3d', 'image_to_3d', 'analyze_style'}

# 本项目上传服务产生的 URL 前缀（utils/files.py build_file_url 唯一输出格式）
# 例如: /api/static/uploads/images/xxx.png
UPLOAD_URL_PREFIX = '/api/static/uploads/'
# 允许的上传子目录
UPLOAD_SUBDIRS = ('images', 'models', 'avatars')


def _validate_input_url(input_url):
    """严格校验 input_url 必须是本项目上传服务产生的 URL

    安全设计（防 SSRF / 防绕过）:
    - 必须是无 scheme/host 的相对路径（拒绝 http://、https://、ftp:// 等外部 URL）
    - 必须以 /api/static/uploads/ 精确前缀开头
    - 路径中不允许出现 ..（路径穿越）或连续 //
    - 必须位于允许的上传子目录（images/models/avatars）
    - 必须有合法文件扩展名

    注意: 不使用简单的 `if 'uploads' in url` 子串判断（易被绕过）。
    """
    if not input_url:
        raise ValidationError('input_url 不能为空')

    value = input_url.strip()
    if not value:
        raise ValidationError('input_url 不能为空')

    parsed = urlparse(value)
    # 拒绝任何带 scheme / netloc 的绝对 URL（外部地址、内网地址）
    if parsed.scheme or parsed.netloc:
        raise ValidationError('input_url 必须是本项目的上传路径，不接受外部 URL')

    if not value.startswith(UPLOAD_URL_PREFIX):
        raise ValidationError('input_url 必须是本项目上传服务产生的路径')

    # 提取前缀之后的相对路径（如 images/xxx.png）
    rel = value[len(UPLOAD_URL_PREFIX):]

    # 路径穿越 / 连续斜杠防护
    if '..' in rel.split('/') or '//' in rel:
        raise ValidationError('input_url 路径不合法')

    # 必须位于允许的上传子目录
    top_dir = rel.split('/')[0] if '/' in rel else rel
    if top_dir not in UPLOAD_SUBDIRS:
        raise ValidationError('input_url 路径不合法')

    # 必须有合法文件扩展名
    if '.' not in rel.split('/')[-1]:
        raise ValidationError('input_url 必须指向具体文件')

    return value


def _get_authenticated_user_or_401():
    """获取认证用户，未认证抛 401"""
    user = get_authenticated_user()
    if user is None:
        raise AuthenticationError('登录凭证无效或已过期')
    return user


def _fail_timed_out_tasks():
    """批量超时清理（薄包装 → services.ai_task.fail_timeout_tasks）

    对全部 RUNNING + JobId 且超时的任务置 FAILED（纯本地 DB，无外部调用）
    """
    return fail_timeout_tasks()


def _get_task_or_404(task_id, user):
    """按 ID 获取任务，仅本人可见；不存在或他人任务 → 404（不泄露存在性）"""
    task = db.session.get(AITask, task_id)
    if task is None or task.user_id != user.id:
        raise ResourceNotFoundError('任务不存在')
    return task


def _refund_ai(user_id, task_id, cost, label='AI 任务'):
    """AI 任务失败自动退款（同 reference 的 REFUND 幂等）

    在任务 FAILED（业务失败或执行异常落 FAILED 后）调用，将已扣积分退回
    """
    try:
        CreditService().recharge(
            user_id, cost,
            transaction_type=CREDIT_TYPE_REFUND,
            reference_id=task_id,
            description=f'{label}失败自动退款',
        )
    except Exception:
        # 退款失败不应掩盖原错误/中断响应——记录日志，交由后续对账处理
        current_app.logger.error('AI 任务退款失败 user=%s task=%s', user_id, task_id)


def _refund_generate_3d(user_id, task_id, cost):
    """AI 3D 生成失败退款（薄包装）"""
    return _refund_ai(user_id, task_id, cost, label='AI 3D 生成')


def _refund_style_analyze(user_id, task_id, cost):
    """AI 风格分析失败退款（薄包装）"""
    return _refund_ai(user_id, task_id, cost, label='AI 风格分析')


def _find_running_duplicate(user_id, task_type, prompt, input_url):
    """查找进行中的重复生成任务

    去重键: user_id + task_type + （text_to_3d: prompt | image_to_3d: input_url）
    仅匹配 RUNNING（进行中未终态）任务；SUCCESS/FAILED 终态不拦截（允许重新生成）。
    RUNNING 即"短时间未完成"的自然窗口（超时保护会把失联 RUNNING 转 FAILED，
    之后可重新提交）。

    Returns:
        AITask | None: 命中的已有 RUNNING 任务
    """
    query = AITask.query.filter_by(
        user_id=user_id, task_type=task_type, status=RUNNING
    )
    if task_type == 'text_to_3d' and prompt:
        query = query.filter(AITask.prompt == prompt)
    elif task_type == 'image_to_3d' and input_url:
        query = query.filter(AITask.input_url == input_url)
    else:
        return None
    return query.order_by(AITask.created_at.desc()).first()


def _maybe_refresh_async_task(task):
    """轮询刷新真实异步任务（薄包装 → services.ai_task.refresh_task）

    行为与重构前完全一致（超时保护/腾讯查询/SUCCESS 产物转存+Artwork/FAILED）；
    传入当前 Provider（保持 API 层 get_ai_service 语义与测试可注入性）
    """
    return refresh_task(task, service=get_ai_service())


def _create_artwork_from_task(task):
    """任务 SUCCESS 后创建 Artwork（方案 B；薄包装 → services.ai_task）"""
    return create_artwork_from_task(task)


def _execute_generate_3d(task):
    """执行 3D 生成（提交 → 状态流转 → 成功后创建 Artwork）

    状态一致性：Provider 抛异常（如 AI_PROVIDER=glm 时
    GLMService.generate_3d 明确不支持 3D 抛 UnconfiguredProviderError）→
    与 analyze_style 一致落 FAILED 终态并 commit，避免任务永久停留 PENDING。
    """
    service = get_ai_service()

    transition_status(task, RUNNING)
    try:
        result = service.generate_3d(task)
    except Exception as e:
        # 记录错误 → 状态机转 FAILED（终态）→ commit 落库 → 继续上抛
        task.error_message = str(e)
        transition_status(task, FAILED)
        db.session.commit()
        raise

    if result.get('status') == FAILED:
        task.error_message = result.get('error_message', 'AI 生成失败')
        transition_status(task, FAILED)
        db.session.commit()
        return task

    # 异步任务已提交（真实混元3D）→ 回填外部 JobId，
    # 任务保持 RUNNING（等待后续轮询查询），不创建空壳 Artwork
    if result.get('status') == RUNNING:
        if result.get('external_task_id'):
            task.external_task_id = result['external_task_id']
        db.session.commit()
        return task

    # 成功: 记录外部任务 ID 与结果 URL
    if result.get('external_task_id'):
        task.external_task_id = result['external_task_id']
    task.result_url = result.get('result_url')
    transition_status(task, SUCCESS)

    # 方案 B: 成功后创建 Artwork 并回填
    _create_artwork_from_task(task)

    db.session.commit()
    return task


def _execute_analyze_style(task, artwork=None):
    """执行风格分析（提交 → 状态流转 → 成功后可选回填 Artwork 分析结果）

    持久化规则：
    - 仅当分析成功（SUCCESS）且调用方传入 artwork 时，写入 artwork.style_analysis
    - 分析失败 / 抛异常 / 未传 artwork → 不修改 Artwork（纯分析，保持原行为）
    - artwork 的归属校验（本人）由路由在任务创建前完成（fail-fast）

    状态一致性：
    - Provider 抛异常（AIServiceError 一族，如 HTTP 非 200 / 超时 / 网络异常 /
      JSON 解析失败 / 缺字段 / 空 content）→ 任务落 FAILED 终态并 commit，
      避免任务永久停留 PENDING/RUNNING（僵尸任务）
    - 异常记录到 task.error_message 后继续上抛，API 保持项目统一错误语义
      （不吞异常、不伪造 SUCCESS）
    - 成功路径与 Mock 业务失败（返回 FAILED dict）行为不变
    """
    service = get_ai_service()

    transition_status(task, RUNNING)
    try:
        result = service.analyze_style(task)
    except Exception as e:
        # AI 服务异常（Service 层已将网络/HTTP/解析等统一转为 AIServiceError）:
        # 记录错误 → 状态机转 FAILED（终态）→ commit 落库 → 继续上抛
        task.error_message = str(e)
        transition_status(task, FAILED)
        db.session.commit()
        raise

    if result.get('status') == FAILED:
        task.error_message = result.get('error_message', '风格分析失败')
        transition_status(task, FAILED)
        db.session.commit()
        return task, result

    transition_status(task, SUCCESS)

    # 分析成功且绑定作品 → 持久化结构化分析结果
    if artwork is not None:
        artwork.style_analysis = result

    db.session.commit()
    return task, result


@api_bp.route('/ai/generate-3d', methods=['POST'])
def generate_3d():
    """创建 3D 生成任务（文生3D / 图生3D）

    认证: get_authenticated_user()
    请求: {"prompt": "...", "task_type": "text_to_3d"|"image_to_3d",
           "input_url": "..."(图生3D必填), "model": "...", "params": {...}}
    校验: text_to_3d 必填 prompt; image_to_3d 必填 input_url; 非法 task_type → 400
    响应: {"code": 200, "message": "...", "data": {task}}
    """
    user = _get_authenticated_user_or_401()

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        raise ValidationError('请求数据不能为空')

    task_type = (data.get('task_type') or '').strip()
    if task_type not in TASK_TYPES or task_type == 'analyze_style':
        raise ValidationError('非法任务类型，仅支持 text_to_3d / image_to_3d')

    prompt = (data.get('prompt') or '').strip()
    input_url = (data.get('input_url') or '').strip()
    service = get_ai_service()
    # model 元数据 —— 客户端未指定时按 Provider 实际模型记录
    # （hunyuan → HUNYUAN_3D_MODEL 配置或 'hunyuan-3d'；mock 无 model 属性 → 'mock-3d'）
    model = (data.get('model') or '').strip() or getattr(service, 'model', None) or 'mock-3d'

    if task_type == 'text_to_3d' and not prompt:
        raise ValidationError('text_to_3d 任务必须提供 prompt')
    if task_type == 'image_to_3d':
        # 安全: input_url 必须为本项目上传路径（防 SSRF）
        input_url = _validate_input_url(input_url)

    # 重复生成保护 —— 同用户/同任务类型/同输入（prompt 或 input_url）
    # 且存在 RUNNING（进行中，未终态）任务 → 直接返回已有任务，不重复提交
    # （防手抖/网络重试导致重复消耗积分；终态任务不拦截——用户可重新生成）
    duplicate = _find_running_duplicate(user.id, task_type, prompt, input_url)
    if duplicate is not None:
        return APIResponse.success(
            data=duplicate.to_dict(),
            message='相同生成任务正在执行中，已返回现有任务',
            code=200,
        )

    # 积分 —— 动态成本（AIProviderConfig.cost_config 优先）;
    # 创建任务前余额检查（不足 402，不建任务）
    cost = CreditService.get_ai_cost(service.provider_name, 'generate_3d')
    if CreditService.get_balance(user.id) < cost:
        raise CreditInsufficientError(f'积分不足（AI 3D 生成需 {cost} 积分）')

    # 创建任务（PENDING; flush 拿 id 供扣费引用，扣费成功一并 commit）
    task = AITask(
        user_id=user.id,
        provider=service.provider_name,
        model=model,
        task_type=task_type,
        prompt=prompt or None,
        input_url=input_url or None,
        status=PENDING,
    )
    db.session.add(task)
    db.session.flush()  # 获取 task.id（事务未提交）

    # 扣费（幂等 reference=task.id；余额不足抛 402 → 事务回滚无任务残留）
    # description 审计格式 '<TYPE>:<provider>'，用于按模型统计积分消耗
    CreditService().consume(
        user.id, cost,
        transaction_type=CREDIT_TYPE_AI_GENERATE_3D,
        reference_id=task.id,
        description=f'{CREDIT_TYPE_AI_GENERATE_3D}:{service.provider_name}',
    )
    # consume 内部已 commit（task + 账户 + 流水原子落库）

    # 执行（同步/异步由 Provider 决定；失败自动退款见 helper）
    try:
        task = _execute_generate_3d(task)
    except Exception:
        # 提交或执行异常已落 FAILED：自动退款并保持错误语义上抛
        _refund_generate_3d(user.id, task.id, cost)
        raise
    if task.status == FAILED:
        # 业务失败（如腾讯拒绝）→ 自动退款
        _refund_generate_3d(user.id, task.id, cost)

    return APIResponse.success(
        data=task.to_dict(),
        message='AI 生成任务处理完成',
        code=200,
    )


@api_bp.route('/ai/tasks', methods=['GET'])
def list_tasks():
    """AI 任务列表（仅本人，倒序分页）

    认证: get_authenticated_user()
    查询参数: page（默认1）, per_page（默认10, 最大50）
    说明: 仅返回 DB 当前状态，不逐条触发外部查询（轮询刷新在任务详情
    GET /ai/tasks/<id> 进行，避免列表 N 次第三方调用）
    响应: APIResponse.paginated（items=[task.to_dict()]）
    """
    user = _get_authenticated_user_or_401()

    # 列表路径触发批量超时清理（纯本地 DB；RUNNING 超时任务 → FAILED）
    _fail_timed_out_tasks()

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 50))

    query = (AITask.query
             .filter_by(user_id=user.id)
             .order_by(AITask.created_at.desc()))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return APIResponse.paginated(
        items=[t.to_dict() for t in pagination.items],
        total=pagination.total,
        page=page,
        page_size=per_page,
        message='获取任务列表成功',
    )


@api_bp.route('/ai/tasks/statistics', methods=['GET'])
def task_statistics():
    """AI 任务统计（仅本人）

    认证: get_authenticated_user()
    说明: 统计当前用户全部 AI 任务状态分布；查询前先执行超时清理保证准确
    响应: data={total, pending, running, success, failed, success_rate,
               average_duration}
          success_rate = success / total（0~1；无任务时为 0）
          average_duration = SUCCESS 任务平均耗时（秒，updated_at - created_at
          兼容口径，无单独完成时间字段；无成功任务时为 0）
    """
    user = _get_authenticated_user_or_401()
    # 先清理超时 RUNNING（保证统计口径一致）
    _fail_timed_out_tasks()

    rows = (
        db.session.query(AITask.status, db.func.count(AITask.id))
        .filter_by(user_id=user.id)
        .group_by(AITask.status)
        .all()
    )
    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    success = counts.get(SUCCESS, 0)

    # 平均耗时（SUCCESS 任务 updated_at - created_at，秒）
    average_duration = 0.0
    if success:
        success_rows = (
            db.session.query(AITask.created_at, AITask.updated_at)
            .filter_by(user_id=user.id, status=SUCCESS)
            .all()
        )
        durations = [
            (updated - created).total_seconds()
            for created, updated in success_rows
            if created and updated and updated >= created
        ]
        if durations:
            average_duration = round(sum(durations) / len(durations), 2)

    data = {
        'total': total,
        'pending': counts.get(PENDING, 0),
        'running': counts.get(RUNNING, 0),
        'success': success,
        'failed': counts.get(FAILED, 0),
        'success_rate': round(success / total, 4) if total else 0.0,
        'average_duration': average_duration,
    }
    return APIResponse.success(
        data=data,
        message='获取任务统计成功',
        code=200,
    )


@api_bp.route('/ai/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """查询 AI 任务（仅本人）

    权限: task.user_id == current_user.id；他人任务/不存在 → 404
    响应: {id, provider, model, task_type, status, result_url, artwork_id, error_message, ...}
    """
    user = _get_authenticated_user_or_401()
    task = _get_task_or_404(task_id, user)
    # 真实异步任务（RUNNING + JobId）读取时触发一次轮询刷新
    _maybe_refresh_async_task(task)

    return APIResponse.success(
        data=task.to_dict(),
        message='获取任务成功',
        code=200,
    )


@api_bp.route('/ai/tasks/<task_id>/retry', methods=['POST'])
def retry_task(task_id):
    """失败任务重试（仅本人）

    规则: 仅本人任务（他人/不存在 → 404 不泄露）；仅 FAILED 允许重试
    （SUCCESS/RUNNING/PENDING → 400）
    行为: 创建新 AITask（复制 provider/model/task_type/prompt/input_url），
    重新进入执行流程（RUNNING 推进）；旧任务保持不变（历史留痕）
    响应: data = 新任务 to_dict
    """
    user = _get_authenticated_user_or_401()
    old = _get_task_or_404(task_id, user)

    if old.status != FAILED:
        raise ValidationError(f'仅失败任务可重试（当前状态: {old.status}）')

    # 复制原任务生成参数创建新任务（外部任务 ID/结果/错误不复制，全新执行）
    task = AITask(
        user_id=user.id,
        provider=old.provider,      # provider 保持一致
        model=old.model,
        task_type=old.task_type,
        prompt=old.prompt,
        input_url=old.input_url,
        status=PENDING,
    )
    db.session.add(task)
    db.session.commit()

    # 重新执行（状态机统一管理：RUNNING → SUCCESS/FAILED）
    task = _execute_generate_3d(task)

    return APIResponse.success(
        data=task.to_dict(),
        message='任务重试已提交',
        code=200,
    )


@api_bp.route('/ai/history', methods=['GET'])
def ai_history():
    """AI 生成历史（仅本人）

    认证: get_authenticated_user()
    查询参数: page / per_page（默认10, 最大50）
    说明: 当前用户全部 AI 任务（生成+分析），按创建时间倒序；
          每项含 AITask 全字段（id 即 task_id）与 artwork 关联摘要（批量查询，无 N+1）
    响应: APIResponse.paginated（items=[task.to_dict() + artwork 摘要]）
    """
    user = _get_authenticated_user_or_401()
    # 先清理超时 RUNNING（历史口径一致）
    _fail_timed_out_tasks()

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 50))

    query = (AITask.query
             .filter_by(user_id=user.id)
             .order_by(AITask.created_at.desc()))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [t.to_dict() for t in pagination.items]

    # artwork 关联摘要（批量一次查询）
    artwork_ids = {item.get('artwork_id') for item in items if item.get('artwork_id')}
    artwork_map = {}
    if artwork_ids:
        artworks = Artwork.query.filter(Artwork.id.in_(artwork_ids)).all()
        artwork_map = {
            a.id: {'id': a.id, 'title': a.title, 'thumbnail': a.thumbnail,
                   'model_url': a.model_url}
            for a in artworks
        }
    for item in items:
        aid = item.get('artwork_id')
        item['artwork'] = artwork_map.get(aid) if aid else None

    return APIResponse.paginated(
        items=items,
        total=pagination.total,
        page=page,
        page_size=per_page,
        message='获取AI历史成功',
    )


@api_bp.route('/ai/analyze-style', methods=['POST'])
def analyze_style():
    """风格分析（多模态图片理解）

    认证: get_authenticated_user()（JWT 优先 + Session 兜底）
    输入: {"input_url": "/api/static/uploads/images/xxx.png",
           "artwork_id": "可选，作品ID（复用 /workshop/save 返回的 data.id）"}
    权限：传 artwork_id 时 ——
      作品不存在 → 404（ResourceNotFoundError）
      作品属于他人 → 403（PermissionError_，禁止越权修改）
      作品属于本人 → 分析成功后写入 artwork.style_analysis
    不传 artwork_id → 保持原行为（纯分析，不触碰任何 Artwork）
    响应: {"code": 200, "message": "...",
           "data": {"task": {...}, "style": "...", "features": [...], "report": {...}}}
    """
    user = _get_authenticated_user_or_401()

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        raise ValidationError('请求数据不能为空')

    input_url = (data.get('input_url') or '').strip()
    # 安全: input_url 必须为本项目上传路径（防 SSRF）
    input_url = _validate_input_url(input_url)

    # 可选 artwork_id —— 先校验归属（fail-fast，越权请求不产生任务记录）
    artwork_id = (data.get('artwork_id') or '').strip() or None
    artwork = None
    if artwork_id:
        artwork = db.session.get(Artwork, artwork_id)
        if artwork is None:
            raise ResourceNotFoundError('作品不存在')
        if artwork.user_id != user.id:
            raise PermissionError_('没有权限修改该作品')

    # Provider 选择（enabled 运行时治理，fail-fast 不建任务）
    service = get_ai_service()
    # 积分 —— 动态成本 + 创建任务前余额检查（不足 402，不建任务）
    cost = CreditService.get_ai_cost(service.provider_name, 'analyze_style')
    if CreditService.get_balance(user.id) < cost:
        raise CreditInsufficientError(f'积分不足（AI 风格分析需 {cost} 积分）')

    # 创建分析任务（复用 AITask，状态管理与 generate_3d 一致）
    # model 必须反映服务层实际调用模型 —— GLMService.model 即 GLM_MODEL 配置值，
    # 不硬编码 'glm-vision'（配置改变时元数据自动跟随）；Mock 无 model 属性 → 保持 'mock-vision'
    task = AITask(
        user_id=user.id,
        provider=service.provider_name,
        model=getattr(service, 'model', None) or 'mock-vision',
        task_type='analyze_style',
        input_url=input_url,
        status=PENDING,
    )
    db.session.add(task)
    db.session.flush()  # 获取 task.id（事务未提交）

    # 扣费（幂等 reference=task.id；不足抛 402 → 事务回滚无任务残留）
    # description 审计格式 '<TYPE>:<provider>'
    CreditService().consume(
        user.id, cost,
        transaction_type=CREDIT_TYPE_AI_ANALYZE_STYLE,
        reference_id=task.id,
        description=f'{CREDIT_TYPE_AI_ANALYZE_STYLE}:{service.provider_name}',
    )

    # 执行（成功保留消费；失败/异常自动退款）
    try:
        task, result = _execute_analyze_style(task, artwork=artwork)
    except Exception:
        _refund_style_analyze(user.id, task.id, cost)
        raise
    if task.status == FAILED:
        _refund_style_analyze(user.id, task.id, cost)

    return APIResponse.success(
        data={
            'task': task.to_dict(),
            'style': result.get('style'),
            'features': result.get('features', []),
            'report': result.get('report', {}),
        },
        message='风格分析完成',
        code=200,
    )
