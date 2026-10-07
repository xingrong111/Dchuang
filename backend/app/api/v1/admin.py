# ============================================================
# 智绘锡承 - 后台运营管理 API
# 位置: backend/app/api/v1/admin.py
#
# 权限方案: 配置式 ADMIN_USER_IDS（逗号分隔用户 ID），
# 不新增 User 角色字段（避免 schema 变更）。流程: 登录 → 校验用户 ID
# 在 ADMIN_USER_IDS 内 → 允许；未登录 401；普通用户 403。
#
# 接口:
#   GET  /admin/statistics/users    用户统计
#   GET  /admin/statistics/ai       AI 任务统计（只查 DB，不查腾讯；时间范围）
#   GET  /admin/statistics/credits  积分统计
#   GET  /admin/statistics/models   AI 模型成本分析（description 审计）
#   GET  /admin/statistics/models/ranking  模型成本排行（total_cost DESC）
#   GET  /admin/tasks               任务分页列表（status/provider 过滤）
#   GET  /admin/tasks/<id>          任务详情（task+user+credit+artwork）
#   POST /admin/tasks/<id>/retry    管理员强制重试（任意用户 FAILED/RUNNING）
#   GET  /admin/providers/<id>/usage    Provider 用量统计
#   POST /admin/providers/<id>/toggle   Provider 启停开关
#   GET  /admin/providers/status        Provider 运行状态（模型健康面板）
#
# 审计: 管理操作写 AdminLog
# ============================================================
import json
from collections import defaultdict
from datetime import datetime, timedelta

from flask import request, current_app, Response

from app.api.v1 import api_bp
from app.extensions import db
from app.models.admin_log import AdminLog
from app.models.ai_provider import AIProviderConfig
from app.models.ai_task import AITask
from app.models.artwork import Artwork
from app.models.credit import CreditTransaction
from app.models.user import User
from app.utils.ai_status import PENDING, RUNNING, SUCCESS, FAILED, transition_status
from app.utils.auth import get_authenticated_user
from app.utils.exceptions import (
    ValidationError,
    AuthenticationError,
    PermissionError_,
    ResourceNotFoundError,
)
from app.utils.response import APIResponse

# 管理任务管理允许的状态过滤
ADMIN_TASK_STATUSES = {PENDING, RUNNING, SUCCESS, FAILED}


# ------------------------------------------------------------
# 权限
# ------------------------------------------------------------
def _admin_user_or_error():
    """管理员权限校验: 未登录 401；非管理员 403

    方案说明: 采用配置式 ADMIN_USER_IDS（环境变量逗号分隔），避免为角色
    新增 User 字段与 migration；后续如需细粒度角色可平滑迁移（保留本函数为唯一入口）。
    """
    user = get_authenticated_user()
    if user is None:
        raise AuthenticationError('登录凭证无效或已过期')

    raw = (current_app.config.get('ADMIN_USER_IDS') or '').strip()
    admin_ids = {int(x) for x in raw.split(',') if x.strip().isdigit()}
    if not admin_ids or user.id not in admin_ids:
        raise PermissionError_('需要管理员权限')
    return user


def _log_admin(admin, action, target_type, target_id, detail=None):
    """写入管理员操作日志（审计）"""
    log = AdminLog(
        admin_user_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        detail=json.dumps(detail, ensure_ascii=False) if detail is not None else None,
    )
    db.session.add(log)
    db.session.commit()


def _parse_date_range():
    """解析 start_date/end_date（YYYY-MM-DD，含首尾当天），返回 (start_dt, end_dt)"""
    start = request.args.get('start_date')
    end = request.args.get('end_date')
    start_dt = end_dt = None
    if start:
        try:
            start_dt = datetime.strptime(start.strip(), '%Y-%m-%d')
        except ValueError:
            raise ValidationError('start_date 格式应为 YYYY-MM-DD')
    if end:
        try:
            end_dt = datetime.strptime(end.strip(), '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            raise ValidationError('end_date 格式应为 YYYY-MM-DD')
    return start_dt, end_dt


def _paginate_args():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 100))
    return page, per_page


# ------------------------------------------------------------
# 用户统计
# ------------------------------------------------------------
@api_bp.route('/admin/statistics/users', methods=['GET'])
def admin_statistics_users():
    """用户统计（管理员）"""
    _admin_user_or_error()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    data = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'new_users_today': User.query.filter(User.created_at >= today_start).count(),
    }
    return APIResponse.success(data=data, message='获取用户统计成功', code=200)


# ------------------------------------------------------------
# AI 任务运营统计
# ------------------------------------------------------------
@api_bp.route('/admin/statistics/ai', methods=['GET'])
def admin_statistics_ai():
    """AI 任务运营统计（管理员；只查数据库）

    参数: start_date / end_date（YYYY-MM-DD，可选）
    返回: {total_tasks, success, failed, running, success_rate,
           avg_duration, by_provider: {provider: count}}
    """
    _admin_user_or_error()
    start_dt, end_dt = _parse_date_range()

    query = AITask.query
    if start_dt:
        query = query.filter(AITask.created_at >= start_dt)
    if end_dt:
        query = query.filter(AITask.created_at < end_dt)

    total = query.count()
    status_rows = (
        query.with_entities(AITask.status, db.func.count(AITask.id))
        .group_by(AITask.status)
        .all()
    )
    counts = {status: count for status, count in status_rows}
    success = counts.get(SUCCESS, 0)

    # by_provider（任务数）
    provider_rows = (
        query.with_entities(AITask.provider, db.func.count(AITask.id))
        .group_by(AITask.provider)
        .all()
    )
    by_provider = {provider: count for provider, count in provider_rows}

    # 平均耗时（SUCCESS：updated_at - created_at，秒；兼容口径）
    avg_duration = 0.0
    if success:
        durations = []
        for created, updated in query.filter_by(status=SUCCESS).with_entities(
                AITask.created_at, AITask.updated_at).all():
            if created and updated and updated >= created:
                durations.append((updated - created).total_seconds())
        if durations:
            avg_duration = round(sum(durations) / len(durations), 2)

    data = {
        'total_tasks': total,
        'success': success,
        'failed': counts.get(FAILED, 0),
        'running': counts.get(RUNNING, 0),
        'success_rate': round(success / total, 4) if total else 0.0,
        'avg_duration': avg_duration,
        'by_provider': by_provider,
    }
    return APIResponse.success(data=data, message='获取AI任务统计成功', code=200)


# ------------------------------------------------------------
# 积分运营统计
# ------------------------------------------------------------
@api_bp.route('/admin/statistics/credits', methods=['GET'])
def admin_statistics_credits():
    """积分运营统计（管理员）

    返回: {total_consumed, total_recharged, today_consumed,
           top_users: [{user_id, username, consumed}],
           daily: [{date, consumed}]（近 7 天，含 0 桶）,
           by_type: [{type, amount}]（带符号合计）}
    """
    _admin_user_or_error()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    def _sum_amount(amount_filter):
        row = (db.session.query(db.func.sum(CreditTransaction.amount))
               .filter(amount_filter).first())
        return int(row[0] or 0)

    total_consumed = -_sum_amount(CreditTransaction.amount < 0)
    total_recharged = _sum_amount(CreditTransaction.amount > 0)
    today_consumed = -_sum_amount(
        (CreditTransaction.amount < 0) & (CreditTransaction.created_at >= today_start)
    )

    # 消耗排行 Top10（join username）
    rows = (
        db.session.query(
            CreditTransaction.user_id,
            User.username,
            db.func.sum(-CreditTransaction.amount).label('consumed'),
        )
        .join(User, User.id == CreditTransaction.user_id)
        .filter(CreditTransaction.amount < 0)
        .group_by(CreditTransaction.user_id, User.username)
        .order_by(db.text('consumed DESC'))
        .limit(10)
        .all()
    )
    top_users = [{'user_id': uid, 'username': name, 'consumed': int(c)}
                 for uid, name, c in rows]

    # 近 7 天消费趋势（含 0 桶，Python 聚合保证 SQLite/MySQL 一致）
    seven_days_start = today_start - timedelta(days=6)
    daily_map = {i: 0 for i in range(7)}
    consume_rows = (
        db.session.query(CreditTransaction.created_at, CreditTransaction.amount)
        .filter(CreditTransaction.amount < 0,
                CreditTransaction.created_at >= seven_days_start)
        .all()
    )
    for created, amount in consume_rows:
        if created:
            idx = (created - seven_days_start).days
            if 0 <= idx < 7:
                daily_map[idx] += -amount
    daily = [
        {'date': (seven_days_start + timedelta(days=idx)).strftime('%Y-%m-%d'),
         'consumed': daily_map[idx]}
        for idx in range(7)
    ]

    # by_type（带符号合计：消费负、退款/充值正）
    type_rows = (
        db.session.query(CreditTransaction.type, db.func.sum(CreditTransaction.amount))
        .group_by(CreditTransaction.type)
        .all()
    )
    by_type = [{'type': tx_type, 'amount': int(amount or 0)} for tx_type, amount in type_rows]

    data = {
        'total_consumed': total_consumed,
        'total_recharged': total_recharged,
        'today_consumed': today_consumed,
        'top_users': top_users,
        'daily': daily,
        'by_type': by_type,
    }
    return APIResponse.success(data=data, message='获取积分统计成功', code=200)


# ------------------------------------------------------------
# AI 模型成本分析
# ------------------------------------------------------------
def _model_cost_aggregate(start_dt, end_dt):
    """消费记录成本聚合（models 明细与 ranking 排行共用）

    数据源: CreditTransaction（消费记录 amount<0），description 审计格式
    '<TYPE>:<provider>'（如 AI_GENERATE_3D:hunyuan / AI_ANALYZE_STYLE:glm）
    description 缺失/无冒号 → provider='unknown'（兼容脏数据）。

    Returns:
        dict: {(provider, task_type): (total_cost, count)}（Python 聚合跨方言统一）
    """
    query = CreditTransaction.query.filter(CreditTransaction.amount < 0)
    if start_dt:
        query = query.filter(CreditTransaction.created_at >= start_dt)
    if end_dt:
        query = query.filter(CreditTransaction.created_at < end_dt)

    aggregate = {}
    for tx_type, description, amount in query.with_entities(
            CreditTransaction.type, CreditTransaction.description,
            CreditTransaction.amount).all():
        provider = 'unknown'
        if description and ':' in description:
            provider = description.rsplit(':', 1)[1].strip() or 'unknown'
        key = (provider, tx_type)
        cost, count = aggregate.get(key, (0, 0))
        aggregate[key] = (cost + abs(amount), count + 1)
    return aggregate


@api_bp.route('/admin/statistics/models', methods=['GET'])
def admin_statistics_models():
    """AI 模型成本分析（管理员）

    数据源: CreditTransaction（消费记录 amount<0），description 审计格式
    '<TYPE>:<provider>'（如 AI_GENERATE_3D:hunyuan / AI_ANALYZE_STYLE:glm）
    返回: {models: [{provider, task_type, total_cost, count}]}
    """
    _admin_user_or_error()
    start_dt, end_dt = _parse_date_range()
    aggregate = _model_cost_aggregate(start_dt, end_dt)

    models = [
        {'provider': provider, 'task_type': tx_type,
         'total_cost': cost, 'count': count}
        for (provider, tx_type), (cost, count) in
        sorted(aggregate.items(), key=lambda kv: -kv[1][0])
    ]
    return APIResponse.success(data={'models': models},
                               message='获取模型成本分析成功', code=200)


@api_bp.route('/admin/statistics/models/ranking', methods=['GET'])
def admin_statistics_models_ranking():
    """AI 模型成本排行（管理员）

    数据源同 /admin/statistics/models（积分消费审计 description），
    按 provider 汇总后按 total_cost 降序排名（附 rank 序号与分类型成本）。

    参数: start_date / end_date（YYYY-MM-DD，可选）
    返回: {ranking: [{rank, provider, total_cost, count,
                      task_types: {task_type: count}}]}
    """
    _admin_user_or_error()
    start_dt, end_dt = _parse_date_range()
    aggregate = _model_cost_aggregate(start_dt, end_dt)

    # 按 provider 汇总（跨 task_type 合并成本与次数）
    by_provider = {}
    for (provider, tx_type), (cost, count) in aggregate.items():
        entry = by_provider.setdefault(
            provider,
            {'provider': provider, 'total_cost': 0, 'count': 0,
             'task_types': {}},
        )
        entry['total_cost'] += cost
        entry['count'] += count
        entry['task_types'][tx_type] = entry['task_types'].get(tx_type, 0) + count

    ranking = sorted(by_provider.values(),
                     key=lambda e: (-e['total_cost'], e['provider']))
    for rank, entry in enumerate(ranking, start=1):
        entry['rank'] = rank

    return APIResponse.success(data={'ranking': ranking},
                               message='获取模型成本排行成功', code=200)


# ------------------------------------------------------------
# 任务管理
# ------------------------------------------------------------
def _admin_task_base_query():
    """管理任务查询（可选状态/Provider 过滤）"""
    query = AITask.query
    status = (request.args.get('status') or '').strip().upper()
    if status:
        if status not in ADMIN_TASK_STATUSES:
            raise ValidationError('非法任务状态')
        query = query.filter(AITask.status == status)
    provider = (request.args.get('provider') or '').strip().lower()
    if provider:
        query = query.filter(AITask.provider == provider)
    return query.order_by(AITask.created_at.desc())


@api_bp.route('/admin/tasks', methods=['GET'])
def admin_list_tasks():
    """后台任务列表（管理员）

    参数: status / provider / page / per_page
    """
    _admin_user_or_error()
    page, per_page = _paginate_args()
    query = _admin_task_base_query()
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [t.to_dict() for t in pagination.items]
    # 附 user 摘要（批量）
    user_ids = {t.user_id for t in pagination.items}
    users = {u.id: {'id': u.id, 'username': u.username} for u in
             User.query.filter(User.id.in_(user_ids)).all()} if user_ids else {}
    for item, task in zip(items, pagination.items):
        item['user'] = users.get(task.user_id)

    return APIResponse.paginated(
        items=items, total=pagination.total, page=page, page_size=per_page,
        message='获取任务列表成功',
    )


@api_bp.route('/admin/tasks/<task_id>', methods=['GET'])
def admin_get_task(task_id):
    """后台任务详情（管理员）

    返回聚合: task + user + credit 流水（该任务 reference）+ artwork
    """
    _admin_user_or_error()
    task = db.session.get(AITask, task_id)
    if task is None:
        raise ResourceNotFoundError('任务不存在')

    data = task.to_dict()
    user = db.session.get(User, task.user_id)
    data['user'] = {'id': user.id, 'username': user.username} if user else None

    # 该任务关联积分流水（reference_id = task.id）
    txs = (CreditTransaction.query
           .filter_by(reference_id=task.id)
           .order_by(CreditTransaction.created_at.desc())
           .all())
    data['credit_transactions'] = [t.to_dict() for t in txs]

    artwork = db.session.get(Artwork, task.artwork_id) if task.artwork_id else None
    data['artwork'] = ({
        'id': artwork.id, 'title': artwork.title, 'thumbnail': artwork.thumbnail,
        'model_url': artwork.model_url,
    } if artwork else None)

    return APIResponse.success(data=data, message='获取任务详情成功', code=200)


@api_bp.route('/admin/tasks/<task_id>/retry', methods=['POST'])
def admin_retry_task(task_id):
    """管理员强制重试任务

    区别普通 retry（仅本人 + 仅 FAILED）: 管理员可对任意用户 FAILED/RUNNING
    任务强制重试；保留旧任务（不删除）并记录 AdminLog 审计；新建任务重新执行。
    """
    from app.api.v1.ai import _execute_generate_3d

    admin = _admin_user_or_error()
    old = db.session.get(AITask, task_id)
    if old is None:
        raise ResourceNotFoundError('任务不存在')
    if old.status not in (FAILED, RUNNING):
        raise ValidationError(f'仅 FAILED/RUNNING 任务可强制重试（当前: {old.status}）')

    # 复制生成参数创建新任务（保持 provider/model；全新执行）
    task = AITask(
        user_id=old.user_id,
        provider=old.provider,
        model=old.model,
        task_type=old.task_type,
        prompt=old.prompt,
        input_url=old.input_url,
        status=PENDING,
    )
    db.session.add(task)
    db.session.commit()

    # 审计（旧任务保留）
    _log_admin(
        admin, action='task_retry', target_type='aitask', target_id=old.id,
        detail={'old_status': old.status, 'new_task_id': task.id,
                'provider': old.provider, 'task_type': old.task_type},
    )

    task = _execute_generate_3d(task)
    return APIResponse.success(
        data={'old_task': old.to_dict(), 'new_task': task.to_dict()},
        message='管理员强制重试已提交',
        code=200,
    )


# ------------------------------------------------------------
# AI 趋势分析
# ------------------------------------------------------------
def _bucket_key(dt, group_by):
    """日期分桶键: day=%Y-%m-%d / week=ISO %G-W%V / month=%Y-%m"""
    if group_by == 'week':
        return dt.strftime('%G-W%V')
    if group_by == 'month':
        return dt.strftime('%Y-%m')
    return dt.strftime('%Y-%m-%d')


@api_bp.route('/admin/statistics/trend', methods=['GET'])
def admin_statistics_trend():
    """AI 趋势分析（管理员；只查数据库，不查第三方）

    参数: start_date / end_date（YYYY-MM-DD，可选）/ group_by（day|week|month，默认 day）
    返回: {trend: [{date, total, success, failed, credits}]}（按日期升序；
          无数据区间返回空数组）
    说明: 任务与消费按 created_at 分桶；采用 Python 聚合以保证 SQLite/MySQL
    跨方言一致（大数据量场景可迁移物化表，P2）
    """
    _admin_user_or_error()
    start_dt, end_dt = _parse_date_range()
    group_by = (request.args.get('group_by') or 'day').strip().lower()
    if group_by not in ('day', 'week', 'month'):
        raise ValidationError('group_by 仅支持 day/week/month')

    task_q = AITask.query
    credit_q = CreditTransaction.query.filter(CreditTransaction.amount < 0)
    if start_dt:
        task_q = task_q.filter(AITask.created_at >= start_dt)
        credit_q = credit_q.filter(CreditTransaction.created_at >= start_dt)
    if end_dt:
        task_q = task_q.filter(AITask.created_at < end_dt)
        credit_q = credit_q.filter(CreditTransaction.created_at < end_dt)

    # 任务分桶（total/success/failed）
    task_stats = {}
    for created, status in task_q.with_entities(
            AITask.created_at, AITask.status).all():
        if created:
            key = _bucket_key(created, group_by)
            bucket = task_stats.setdefault(
                key, {'date': key, 'total': 0, 'success': 0, 'failed': 0, 'credits': 0})
            bucket['total'] += 1
            if status == SUCCESS:
                bucket['success'] += 1
            elif status == FAILED:
                bucket['failed'] += 1

    # 积分消费分桶
    for created, amount in credit_q.with_entities(
            CreditTransaction.created_at, CreditTransaction.amount).all():
        if created:
            key = _bucket_key(created, group_by)
            bucket = task_stats.setdefault(
                key, {'date': key, 'total': 0, 'success': 0, 'failed': 0, 'credits': 0})
            bucket['credits'] += -amount

    trend = [task_stats[k] for k in sorted(task_stats.keys())]
    return APIResponse.success(data={'trend': trend},
                               message='获取趋势统计成功', code=200)


# ------------------------------------------------------------
# AI Provider 运营管理
# ------------------------------------------------------------
@api_bp.route('/admin/providers', methods=['GET'])
def admin_list_providers():
    """Provider 配置列表（管理员）"""
    _admin_user_or_error()
    items = [p.to_dict() for p in AIProviderConfig.query.order_by(AIProviderConfig.id).all()]
    return APIResponse.success(data={'providers': items},
                               message='获取 Provider 列表成功', code=200)


@api_bp.route('/admin/providers', methods=['POST'])
def admin_create_provider():
    """创建 Provider 配置（管理员）

    body: {"name": "hunyuan", "type": "3d"}（type: 3d | analysis；cost_config 可选）
    """
    admin = _admin_user_or_error()
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        raise ValidationError('请求数据不能为空')

    name = (data.get('name') or '').strip().lower()
    provider_type = (data.get('type') or '').strip().lower()
    if not name:
        raise ValidationError('Provider 名称不能为空')
    if provider_type not in ('3d', 'analysis'):
        raise ValidationError('type 仅支持 3d / analysis')
    if AIProviderConfig.query.filter_by(name=name).first():
        raise ValidationError('Provider 已存在')

    cost_config = data.get('cost_config')
    if cost_config is not None and not isinstance(cost_config, dict):
        raise ValidationError('cost_config 必须为对象')

    provider = AIProviderConfig(
        name=name, provider_type=provider_type,
        enabled=bool(data.get('enabled', True)),
        cost_config=cost_config or {},
    )
    db.session.add(provider)
    db.session.commit()

    _log_admin(admin, action='provider_create', target_type='ai_provider',
               target_id=provider.id, detail={'name': name, 'type': provider_type})
    return APIResponse.success(data=provider.to_detail(), message='创建成功', code=200)


@api_bp.route('/admin/providers/<int:provider_id>', methods=['PUT'])
def admin_update_provider(provider_id):
    """更新 Provider 配置（管理员；支持 enabled/cost_config/type）

    作用: enabled=false 时，factory 在运行时阻止该 Provider 的新调用
    """
    admin = _admin_user_or_error()
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise ResourceNotFoundError('Provider 不存在')

    data = request.get_json(silent=True) or {}
    changed = {}
    if 'enabled' in data:
        provider.enabled = bool(data['enabled'])
        changed['enabled'] = provider.enabled
    if 'cost_config' in data:
        if not isinstance(data['cost_config'], dict):
            raise ValidationError('cost_config 必须为对象')
        provider.cost_config = data['cost_config']
        changed['cost_config'] = provider.cost_config
    if 'type' in data:
        if data['type'] not in ('3d', 'analysis'):
            raise ValidationError('type 仅支持 3d / analysis')
        provider.provider_type = data['type']
        changed['type'] = provider.provider_type
    if not changed:
        raise ValidationError('无可更新字段')

    db.session.commit()
    _log_admin(admin, action='provider_update', target_type='ai_provider',
               target_id=provider.id, detail=changed)
    return APIResponse.success(data=provider.to_detail(), message='更新成功', code=200)


@api_bp.route('/admin/providers/<int:provider_id>', methods=['DELETE'])
def admin_delete_provider(provider_id):
    """删除 Provider 配置（管理员）

    限制: 存在任务记录（AITask.provider == name）时禁止删除 → 400
    """
    admin = _admin_user_or_error()
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise ResourceNotFoundError('Provider 不存在')

    if AITask.query.filter_by(provider=provider.name).first():
        raise ValidationError('该 Provider 存在任务记录，禁止删除')

    _log_admin(admin, action='provider_delete', target_type='ai_provider',
               target_id=provider.id, detail={'name': provider.name})
    db.session.delete(provider)
    db.session.commit()
    return APIResponse.success(data={'id': provider_id}, message='删除成功', code=200)


# ------------------------------------------------------------
# Provider 用量统计 / 启停开关
# ------------------------------------------------------------
@api_bp.route('/admin/providers/<int:provider_id>/usage', methods=['GET'])
def admin_provider_usage(provider_id):
    """Provider 用量统计（管理员）

    聚合该 Provider 的任务（AITask.provider）与积分消费（description 审计
    '<TYPE>:<provider>'）:
    返回: {provider, total_tasks, status_counts, success_rate, avg_duration,
           by_task_type, total_cost, consume_count}
    说明: cost 以积分流水为准（任务创建时扣费，失败自动退款 → 净成本）
    """
    _admin_user_or_error()
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise ResourceNotFoundError('Provider 不存在')

    # 任务侧: 总数 / 状态分布 / 任务类型分布 / 平均耗时
    task_q = AITask.query.filter_by(provider=provider.name)
    total_tasks = task_q.count()
    status_counts = {status: 0 for status in (PENDING, RUNNING, SUCCESS, FAILED)}
    for status, count in (task_q.with_entities(AITask.status, db.func.count(AITask.id))
                          .group_by(AITask.status).all()):
        status_counts[status] = count

    by_task_type = {}
    for task_type, count in (task_q.with_entities(AITask.task_type, db.func.count(AITask.id))
                             .group_by(AITask.task_type).all()):
        by_task_type[task_type] = count

    avg_duration = 0.0
    success = status_counts.get(SUCCESS, 0)
    if success:
        durations = []
        for created, updated in (task_q.filter_by(status=SUCCESS)
                                 .with_entities(AITask.created_at, AITask.updated_at)
                                 .all()):
            if created and updated and updated >= created:
                durations.append((updated - created).total_seconds())
        if durations:
            avg_duration = round(sum(durations) / len(durations), 2)

    # 成本侧: 积分消费（description 审计格式 '<TYPE>:<provider>'）
    cost_row = (
        db.session.query(
            db.func.sum(-CreditTransaction.amount),
            db.func.count(CreditTransaction.id),
        )
        .filter(CreditTransaction.amount < 0,
                CreditTransaction.description.like(f'%:{provider.name}'))
        .first()
    )
    total_cost = int(cost_row[0] or 0) if cost_row else 0
    consume_count = int(cost_row[1] or 0) if cost_row else 0

    data = {
        'provider': provider.to_detail(),
        'total_tasks': total_tasks,
        'status_counts': status_counts,
        'success_rate': round(success / total_tasks, 4) if total_tasks else 0.0,
        'avg_duration': avg_duration,
        'by_task_type': by_task_type,
        'total_cost': total_cost,
        'consume_count': consume_count,
    }
    return APIResponse.success(data=data, message='获取 Provider 用量统计成功', code=200)


@api_bp.route('/admin/providers/<int:provider_id>/toggle', methods=['POST'])
def admin_toggle_provider(provider_id):
    """Provider 启停开关（管理员）

    body 可选: {"enabled": true|false}；缺省则翻转当前值。
    说明: 与 PUT /admin/providers/<id> 区别 —— toggle 专为快速启停设计，
    写 AdminLog action=provider_toggle（记录前后状态），返回最新详情。
    """
    admin = _admin_user_or_error()
    provider = db.session.get(AIProviderConfig, provider_id)
    if provider is None:
        raise ResourceNotFoundError('Provider 不存在')

    data = request.get_json(silent=True) or {}
    old_enabled = provider.enabled
    if 'enabled' in data:
        provider.enabled = bool(data['enabled'])
    else:
        provider.enabled = not provider.enabled
    db.session.commit()

    _log_admin(admin, action='provider_toggle', target_type='ai_provider',
               target_id=provider.id,
               detail={'name': provider.name, 'old_enabled': old_enabled,
                       'new_enabled': provider.enabled})
    return APIResponse.success(
        data={'provider': provider.to_detail(),
              'old_enabled': old_enabled, 'new_enabled': provider.enabled},
        message='切换成功', code=200)


# ------------------------------------------------------------
# Provider 运行状态（后台模型健康面板）
# ------------------------------------------------------------
@api_bp.route('/admin/providers/status', methods=['GET'])
def admin_provider_status():
    """AI Provider 运行状态（管理员；后台模型健康面板）

    返回: {providers: [{provider, enabled, running_tasks, last_used_at}]}
      provider:      名称（AIProviderConfig ∪ AITask.provider，按名升序）
      enabled:       AIProviderConfig.enabled（无配置记录 → True，兼容未治理的历史 provider）
      running_tasks: 该 provider 当前 RUNNING 任务数
      last_used_at:  该 provider 最近一次任务更新时间（无任务 → null）
    数据源: 仅 DB（ai_providers + ai_tasks），不触发任何第三方调用。
    """
    _admin_user_or_error()

    # 1) 已知 Provider 集合（配置记录 ∪ 任务历史）
    configs = AIProviderConfig.query.all()
    names = {c.name for c in configs}
    task_providers = db.session.query(AITask.provider).distinct().all()
    names.update(row[0] for row in task_providers if row[0])

    # 2) RUNNING 任务数（按 provider）
    running_counts = {
        provider: count
        for provider, count in (
            db.session.query(AITask.provider, db.func.count(AITask.id))
            .filter(AITask.status == RUNNING)
            .group_by(AITask.provider)
            .all()
        )
    }

    # 3) 最近使用时间（max(updated_at)，按 provider）
    last_used_at = {
        provider: (updated.isoformat() if updated else None)
        for provider, updated in (
            db.session.query(AITask.provider, db.func.max(AITask.updated_at))
            .group_by(AITask.provider)
            .all()
        )
    }

    config_map = {c.name: c for c in configs}
    providers = []
    for name in sorted(names):
        cfg = config_map.get(name)
        providers.append({
            'provider': name,
            'enabled': cfg.enabled if cfg is not None else True,
            'running_tasks': running_counts.get(name, 0),
            'last_used_at': last_used_at.get(name),
        })

    return APIResponse.success(
        data={'providers': providers},
        message='获取 Provider 运行状态成功', code=200)


# ------------------------------------------------------------
# 审计日志查询
# ------------------------------------------------------------
@api_bp.route('/admin/logs', methods=['GET'])
def admin_list_logs():
    """管理员操作日志查询（管理员）

    参数: action / target_type / admin_user_id / page / per_page
    """
    _admin_user_or_error()
    page, per_page = _paginate_args()

    query = AdminLog.query
    action = (request.args.get('action') or '').strip()
    if action:
        query = query.filter(AdminLog.action == action)
    target_type = (request.args.get('target_type') or '').strip()
    if target_type:
        query = query.filter(AdminLog.target_type == target_type)
    admin_id = request.args.get('admin_user_id', type=int)
    if admin_id:
        query = query.filter(AdminLog.admin_user_id == admin_id)

    pagination = (query.order_by(AdminLog.created_at.desc(), AdminLog.id.desc())
                  .paginate(page=page, per_page=per_page, error_out=False))

    items = [log.to_dict() for log in pagination.items]
    return APIResponse.paginated(
        items=items, total=pagination.total, page=page, page_size=per_page,
        message='获取操作日志成功',
    )


# ------------------------------------------------------------
# 任务 CSV 导出（流式）
# ------------------------------------------------------------
def _iter_task_rows(filters, header=True):
    """分页流式产出 CSV 行（不一次加载全部；cost 按页批量查询）"""
    import csv
    import io

    status = filters.get('status')
    provider = filters.get('provider')
    query = AITask.query
    if status:
        query = query.filter(AITask.status == status)
    if provider:
        query = query.filter(AITask.provider == provider)
    query = query.order_by(AITask.created_at.desc())

    page, per_page = 1, 500
    total_pages = None
    first = True
    while True:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        if total_pages is None:
            total_pages = pagination.pages or 1
        tasks = pagination.items
        if not tasks:
            break

        # 用户 + 成本批量
        user_ids = {t.user_id for t in tasks}
        users = {u.id: u.username for u in User.query.filter(User.id.in_(user_ids)).all()}
        cost_rows = (
            db.session.query(CreditTransaction.reference_id,
                             db.func.sum(-CreditTransaction.amount))
            .filter(CreditTransaction.reference_id.in_([t.id for t in tasks]),
                    CreditTransaction.amount < 0)
            .group_by(CreditTransaction.reference_id)
            .all()
        )
        costs = {ref: int(c) for ref, c in cost_rows}

        buf = io.StringIO()
        writer = csv.writer(buf)
        if first and header:
            writer.writerow(['task_id', 'user', 'provider', 'model', 'status',
                             'cost', 'created_at', 'artwork_id'])
        for t in tasks:
            writer.writerow([
                t.id, users.get(t.user_id, ''), t.provider, t.model, t.status,
                costs.get(t.id, 0),
                t.created_at.isoformat() if t.created_at else '',
                t.artwork_id or '',
            ])
        first = False
        yield buf.getvalue()

        if page >= total_pages:
            break
        page += 1


@api_bp.route('/admin/tasks/export', methods=['GET'])
def admin_export_tasks():
    """任务 CSV 导出（管理员；流式输出，不一次加载全部）

    参数: status / provider
    字段: task_id,user,provider,model,status,cost,created_at,artwork_id
    """
    _admin_user_or_error()
    status = (request.args.get('status') or '').strip().upper()
    if status and status not in ADMIN_TASK_STATUSES:
        raise ValidationError('非法任务状态')
    provider = (request.args.get('provider') or '').strip().lower()

    generator = _iter_task_rows({'status': status, 'provider': provider})
    return Response(
        generator,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=ai_tasks.csv'},
    )
