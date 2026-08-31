# ============================================================
# 智绘锡承 - AI 多模态 API（阶段9 AI 基础设施）
# 位置: backend/app/api/v1/ai.py
#
# 接口前缀约定: 前端 Vite 代理剥 /api 后转发，本蓝图路由无 /api 前缀:
#   POST /ai/generate-3d        （文生3D / 图生3D 任务创建）
#   GET  /ai/tasks/<task_id>    （任务查询，仅本人）
#   POST /ai/analyze-style      （风格分析）
#
# 认证: 全部使用 get_authenticated_user()（JWT 优先 + Session 兜底）
# Provider: 通过 get_ai_service() 工厂选择（本阶段 mock / 真实 Provider 未实现）
#
# Artwork 集成（方案 B）: 任务 SUCCESS 后才创建 Artwork 并回填 task.artwork_id；
#                         失败不创建（不产生空壳作品）。
# ============================================================
from flask import request

from app.api.v1 import api_bp
from app.extensions import db
from app.models.ai_task import AITask
from app.models.artwork import Artwork
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
    ResourceNotFoundError,
)
from app.utils.response import APIResponse

# 合法任务类型
TASK_TYPES = {'text_to_3d', 'image_to_3d', 'analyze_style'}


def _get_authenticated_user_or_401():
    """获取认证用户，未认证抛 401"""
    user = get_authenticated_user()
    if user is None:
        raise AuthenticationError('登录凭证无效或已过期')
    return user


def _get_task_or_404(task_id, user):
    """按 ID 获取任务，仅本人可见；不存在或他人任务 → 404（不泄露存在性）"""
    task = db.session.get(AITask, task_id)
    if task is None or task.user_id != user.id:
        raise ResourceNotFoundError('任务不存在')
    return task


def _create_artwork_from_task(task):
    """任务 SUCCESS 后创建 Artwork（方案 B）

    仅设置真实存在的 Artwork 字段，不创建空壳。
    """
    artwork = Artwork(
        user_id=task.user_id,
        title=(task.prompt or '')[:80] or f'AI生成作品-{task.id[:8]}',
        description=task.prompt,
        model_url=task.result_url,
        model_format='glb' if task.task_type in ('text_to_3d', 'image_to_3d') else None,
        is_ai_generated=True,
        ai_model=task.model,
        ai_prompt=task.prompt,
    )
    db.session.add(artwork)
    db.session.flush()  # 获取 artwork.id
    task.artwork_id = artwork.id
    return artwork


def _execute_generate_3d(task):
    """执行 3D 生成（提交 → 状态流转 → 成功后创建 Artwork）"""
    service = get_ai_service()

    transition_status(task, RUNNING)
    result = service.generate_3d(task)

    if result.get('status') == FAILED:
        task.error_message = result.get('error_message', 'AI 生成失败')
        transition_status(task, FAILED)
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


def _execute_analyze_style(task):
    """执行风格分析（提交 → 状态流转 → 返回结构化结果）"""
    service = get_ai_service()

    transition_status(task, RUNNING)
    result = service.analyze_style(task)

    if result.get('status') == FAILED:
        task.error_message = result.get('error_message', '风格分析失败')
        transition_status(task, FAILED)
        db.session.commit()
        return task, result

    transition_status(task, SUCCESS)
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
    model = (data.get('model') or '').strip() or 'mock-3d'

    if task_type == 'text_to_3d' and not prompt:
        raise ValidationError('text_to_3d 任务必须提供 prompt')
    if task_type == 'image_to_3d' and not input_url:
        raise ValidationError('image_to_3d 任务必须提供 input_url')

    # 创建任务（PENDING）
    task = AITask(
        user_id=user.id,
        provider=get_ai_service().provider_name,
        model=model,
        task_type=task_type,
        prompt=prompt or None,
        input_url=input_url or None,
        status=PENDING,
    )
    db.session.add(task)
    db.session.commit()

    # 执行（本阶段同步执行，状态机统一管理）
    task = _execute_generate_3d(task)

    return APIResponse.success(
        data=task.to_dict(),
        message='AI 生成任务处理完成',
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

    return APIResponse.success(
        data=task.to_dict(),
        message='获取任务成功',
        code=200,
    )


@api_bp.route('/ai/analyze-style', methods=['POST'])
def analyze_style():
    """风格分析（多模态图片理解）

    认证: get_authenticated_user()
    输入: {"input_url": "/api/static/uploads/images/xxx.png"}（复用 /workshop/upload 返回的 data.url）
    响应: {"code": 200, "message": "...",
           "data": {"task": {...}, "style": "...", "features": [...], "report": {...}}}
    """
    user = _get_authenticated_user_or_401()

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        raise ValidationError('请求数据不能为空')

    input_url = (data.get('input_url') or '').strip()
    if not input_url:
        raise ValidationError('风格分析必须提供 input_url（来自 /workshop/upload 返回的 data.url）')

    # 创建分析任务（复用 AITask，状态管理与 generate_3d 一致）
    task = AITask(
        user_id=user.id,
        provider=get_ai_service().provider_name,
        model='glm-vision' if get_ai_service().provider_name == 'glm' else 'mock-vision',
        task_type='analyze_style',
        input_url=input_url,
        status=PENDING,
    )
    db.session.add(task)
    db.session.commit()

    task, result = _execute_analyze_style(task)

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
