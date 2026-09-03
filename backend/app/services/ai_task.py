# ============================================================
# 智绘锡承 - AI 任务状态 Service（阶段15-C: 后台调度重构）
# 位置: backend/app/services/ai_task.py
#
# 职责（从 api/v1/ai.py 抽取的公共逻辑，供 API 与后台 Worker 共用）:
#   - refresh_task(task): 刷新单个 RUNNING 异步任务（超时保护 + 腾讯查询 +
#     SUCCESS 产物转存 + Artwork 创建 + 状态推进）
#   - fail_timeout_tasks(): 批量超时清理（RUNNING + JobId 超时 → FAILED）
#   - process_running_tasks(): 扫描全部 RUNNING 任务逐个刷新（Worker/手动入口）
#
# 设计:
#   - API 层（GET /ai/tasks/<id>）只调用 refresh_task，行为与重构前完全一致
#   - Worker 只调用 process_running_tasks，不复制任何业务逻辑
#   - refresh_task 支持注入 service（API 层传入当前 Provider；Worker 用默认工厂）
# ============================================================
import logging
import time
from datetime import datetime, timedelta

from app.extensions import db
from app.models.ai_task import AITask
from app.models.artwork import Artwork
from app.services.factory import get_ai_service
from app.utils.ai_status import RUNNING, SUCCESS, FAILED, transition_status
from app.utils.exceptions import AIServiceError, ValidationError
from app.utils.files import download_model_to_local

logger = logging.getLogger(__name__)


def _log_task_done(task):
    """阶段16-D: AI 任务完成结构化日志（AI_TASK_DONE）

    任务进入终态（SUCCESS/FAILED）时记录:
      AI_TASK_DONE task_id=<id> provider=<p> status=<s> duration=<秒>
    duration = updated_at - created_at（任务生命周期耗时）；
    Worker 轮询完成与 API 详情轮询完成路径共用（终态只发生一次 → 不重复）。
    """
    duration = 0.0
    if task.created_at:
        end = task.updated_at or datetime.utcnow()
        try:
            duration = max((end - task.created_at).total_seconds(), 0.0)
        except TypeError:
            duration = 0.0
    logger.info(
        'AI_TASK_DONE task_id=%s provider=%s status=%s duration=%.2fs',
        task.id, task.provider, task.status, duration,
    )


def create_artwork_from_task(task):
    """任务 SUCCESS 后创建 Artwork（方案 B；由 api/v1/ai.py 迁移的公共逻辑）

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


def refresh_task(task, service=None):
    """刷新单个真实异步任务（RUNNING + JobId）—— 原 api/v1/ai.py
    _maybe_refresh_async_task 逻辑迁移（行为一致），另增加"非 AIServiceError
    意外异常 → FAILED"兜底（防 Worker/API 场景僵尸任务与 500）。

    Args:
        task: AITask 实例
        service: 可选 Provider（API 层传入当前实例；缺省走 get_ai_service 工厂）

    Returns:
        AITask: 刷新后的任务
    """
    if task.status != RUNNING or not task.external_task_id:
        return task

    # 超时保护: RUNNING 超过阈值未终态 → FAILED（防第三方失联永久 RUNNING）
    timeout_seconds = _timeout_seconds()
    if task.updated_at:
        try:
            age = (datetime.utcnow() - task.updated_at).total_seconds()
        except TypeError:
            age = 0  # updated_at 异常 → 不触发超时
        if age > timeout_seconds:
            task.error_message = f'AI 任务执行超时（超过 {timeout_seconds} 秒未完成）'
            transition_status(task, FAILED)
            db.session.commit()
            _log_task_done(task)  # 16-D: 超时落终态也记录
            return task

    provider = service or get_ai_service()
    query = getattr(provider, 'query_task', None)
    if not callable(query):
        return task  # Mock/GLM 无异步查询能力

    try:
        result = query(task)
    except AIServiceError as e:
        # 查询失败（网络/凭据/任务不存在等）：保持 RUNNING，轮询重试（不误判）
        logger.warning('AI任务状态查询失败 task=%s: %s', task.id, e)
        return task
    except Exception as e:
        # 意外异常（非 AIServiceError）→ 落 FAILED（防僵尸/500）
        task.error_message = f'AI任务状态查询异常: {e}'
        transition_status(task, FAILED)
        db.session.commit()
        _log_task_done(task)  # 16-D: 异常落终态记录
        return task

    if result.get('status') == SUCCESS:
        # 产物持久化: 下载腾讯 COS GLB 转存本地稳定地址（防签名 URL 过期）；
        # 下载失败保留腾讯 result_url 作为 fallback
        remote_url = result.get('result_url')
        final_url = remote_url
        if remote_url:
            try:
                final_url = download_model_to_local(remote_url)
            except (ValidationError, AIServiceError, OSError) as e:
                logger.warning('AI产物本地转存失败 task=%s: %s（保留腾讯 URL fallback）',
                               task.id, e)
        task.result_url = final_url
        transition_status(task, SUCCESS)
        # Artwork 只在 SUCCESS 后创建（RUNNING→SUCCESS 仅一次 → 幂等）
        create_artwork_from_task(task)
        db.session.commit()
        _log_task_done(task)  # 16-D: 完成日志
    elif result.get('status') == FAILED:
        task.error_message = result.get('error_message') or 'AI任务失败'
        transition_status(task, FAILED)
        db.session.commit()
        _log_task_done(task)  # 16-D: 失败终态日志
    # RUNNING → 保持现状（等待下次轮询）
    return task


def fail_timeout_tasks():
    """批量超时清理（纯本地 DB，无外部调用）

    对全部 RUNNING + external_task_id（JobId）且 updated_at 超过
    AI_TASK_TIMEOUT_SECONDS 的任务置 FAILED —— 覆盖"用户/Worker 不访问
    详情"场景，保证超时任务最终进入终态。

    Returns:
        int: 被置为超时 FAILED 的任务数
    """
    timeout_seconds = _timeout_seconds()
    cutoff = datetime.utcnow() - timedelta(seconds=timeout_seconds)
    timed_out = (
        AITask.query
        .filter(
            AITask.status == RUNNING,
            AITask.external_task_id.isnot(None),
            AITask.updated_at < cutoff,
        )
        .all()
    )
    for task in timed_out:
        task.error_message = f'AI 任务执行超时（超过 {timeout_seconds} 秒未完成）'
        transition_status(task, FAILED)
    if timed_out:
        db.session.commit()
        for task in timed_out:
            _log_task_done(task)  # 16-D: 超时清理落终态记录
    return len(timed_out)


def process_running_tasks():
    """扫描全部 RUNNING + JobId 任务并逐个刷新（Worker/手动公共入口）

    单任务刷新失败不中断批次（记录日志继续处理其余任务）。

    Returns:
        dict: {'processed': 处理数, 'success': 刷新后成功数,
               'failed': 刷新后失败数, 'running': 刷新后仍运行数,
               'providers': {provider: 处理数},   # 16-C: 按 Provider 拆解
               'cost': 本轮耗时秒}               # 16-C: 运行耗时（成本治理）
    """
    started = _monotonic()
    # 先批量超时清理（保证统计/扫描口径一致）
    fail_timeout_tasks()

    running = (AITask.query
               .filter(
                   AITask.status == RUNNING,
                   AITask.external_task_id.isnot(None),
               )
               .all())
    task_ids = [task.id for task in running]

    # 16-C: Provider 分布（扫描到的 RUNNING 任务按 provider 计数）
    provider_counts = {}
    for task in running:
        provider_counts[task.provider] = provider_counts.get(task.provider, 0) + 1

    for task in running:
        try:
            refresh_task(task)
        except Exception as e:
            logger.exception('刷新任务异常 task=%s: %s', task.id, e)

    # 刷新后状态统计（供 Worker 状态日志）
    result = {'processed': len(task_ids), 'success': 0, 'failed': 0, 'running': 0}
    if task_ids:
        status_rows = (
            db.session.query(AITask.status, db.func.count(AITask.id))
            .filter(AITask.id.in_(task_ids))
            .group_by(AITask.status)
            .all()
        )
        for status, count in status_rows:
            result[status.lower()] = count

    # 16-C: 成本治理扩展（providers + 本轮耗时秒）
    result['providers'] = provider_counts
    result['cost'] = round(_monotonic() - started, 2)
    return result


def _timeout_seconds():
    """读取 AI_TASK_TIMEOUT_SECONDS 配置（缺省 1800）"""
    from flask import current_app

    return current_app.config.get('AI_TASK_TIMEOUT_SECONDS', 1800)


def _monotonic():
    """单调时钟（跨平台）"""
    return time.monotonic()
