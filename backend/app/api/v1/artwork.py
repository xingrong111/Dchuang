# ============================================================
# 智绘锡承 - 作品管理 API
# 位置: backend/app/api/v1/artwork.py
#
# 接口前缀约定: 前端 Vite 代理剥 /api 后转发，本蓝图路由无 /api 前缀:
#   POST   /workshop/save        （前端 POST /api/workshop/save）
#   GET    /workshop/works       （作品列表）
#   GET    /workshop/works/<id>  （作品详情）
#   PUT    /workshop/works/<id>  （更新，仅作者）
#   DELETE /workshop/works/<id>  （删除，仅作者）
#
# 认证设计:
# - 创建/更新/删除: 使用现有 get_authenticated_user()（JWT 优先 + Session 兜底）
# - 作者身份: 严格来自认证来源，绝不信任客户端提交的 user_id/username
# - 列表/详情: 公开浏览（is_public=True 可见）
#
# 安全规则:
# - 越权修改/删除（非作者）→ 403
# - 资源不存在 → 404
# - 未认证写操作 → 401
# - 客户端提交 user_id 一律忽略（归属仅由服务端认证身份决定）
# ============================================================
from flask import request

from app.api.v1 import api_bp
from app.extensions import db
from app.models.artwork import Artwork
from app.models.like import Like
from app.models.comment import Comment
from app.models.collection import Collection
from app.utils.auth import get_authenticated_user
from app.utils.exceptions import (
    ValidationError,
    AuthenticationError,
    PermissionError_,
    ResourceNotFoundError,
)
from app.utils.response import APIResponse

# 评论内容长度上限
COMMENT_MAX_LENGTH = 1000

# 创建/更新时允许客户端设置的业务字段（白名单，防字段污染）
# 注意: 不含 user_id / id / 统计字段 / blockchain 认证字段
CREATE_FIELDS = {
    'title', 'description', 'tags',
    'model_url', 'model_format', 'model_size', 'thumbnail',
    'is_ai_generated', 'ai_model', 'ai_prompt', 'ai_params',
    'is_public', 'allow_download', 'license_type',
}

# 更新时允许修改的字段（= 创建字段，同样不含归属/统计/存证字段）
UPDATE_FIELDS = CREATE_FIELDS

# 禁止客户端修改的字段（防御性声明，用于文档与断言）
PROTECTED_FIELDS = {
    'id', 'user_id',
    'view_count', 'like_count', 'download_count',
    'blockchain_hash', 'blockchain_tx_id', 'is_certified',
}


def _get_authenticated_user_or_401():
    """获取认证用户，未认证返回 None（调用方抛 401）"""
    user = get_authenticated_user()
    if user is None:
        raise AuthenticationError('登录凭证无效或已过期')
    return user


def _get_artwork_or_404(artwork_id):
    """按 ID 获取作品，不存在抛 404"""
    artwork = db.session.get(Artwork, artwork_id)
    if artwork is None:
        raise ResourceNotFoundError('作品不存在')
    return artwork


def _extract_fields(data, allowed):
    """从请求数据中提取白名单字段（忽略未知/受保护字段）"""
    if not data or not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in allowed}


def _validate_create_fields(fields):
    """校验创建必填字段"""
    title = (fields.get('title') or '').strip()
    if not title:
        raise ValidationError('作品标题不能为空')
    if len(title) > 200:
        raise ValidationError('作品标题长度不能超过200个字符')
    fields['title'] = title
    return fields


@api_bp.route('/workshop/save', methods=['POST'])
def save_artwork():
    """保存作品（创建 Artwork）

    认证: get_authenticated_user()（JWT 或 Session）
    身份: 作者来自服务端认证身份，客户端提交的 user_id 被忽略
    请求: {"title": "...", "description": "...", "model_url": "/api/static/uploads/...", ...}
    响应: {"code": 200, "message": "作品保存成功", "data": {artwork}}
    """
    user = _get_authenticated_user_or_401()

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        raise ValidationError('请求数据不能为空')

    fields = _extract_fields(data, CREATE_FIELDS)
    fields = _validate_create_fields(fields)

    artwork = Artwork(user_id=user.id)
    for key, value in fields.items():
        setattr(artwork, key, value)

    db.session.add(artwork)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise ValidationError('作品保存失败，请稍后重试')

    return APIResponse.success(
        data=artwork.to_dict(include_details=True),
        message='作品保存成功',
        code=200,
    )


@api_bp.route('/workshop/works', methods=['GET'])
def list_artworks():
    """作品列表（公开浏览，支持分页/排序/过滤）

    查询参数:
      page / per_page（默认10, 最大100）
      sort: latest（默认，按创建时间倒序）
      is_ai_generated: true|false（AI 生成作品过滤）
      author_id: 指定作者公开作品（用户隔离：仅该作者 is_public=True 作品）
    规则: 仅返回 is_public=True 的公开作品（他人私有作品永不进入列表）；
          排序 latest = created_at desc
    响应: APIResponse.paginated（统一分页格式）
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 100))

    # 用户隔离: 公开列表只含 is_public=True（私有对非作者不可见）
    query = Artwork.query.filter_by(is_public=True)

    # AI 作品过滤
    ai_flag = request.args.get('is_ai_generated')
    if ai_flag is not None:
        if str(ai_flag).strip().lower() == 'true':
            query = query.filter(Artwork.is_ai_generated.is_(True))
        elif str(ai_flag).strip().lower() == 'false':
            query = query.filter(Artwork.is_ai_generated.is_(False))

    # 作者过滤（仅该作者公开作品；author_id 不存在/他人私有均不可见）
    author_id = request.args.get('author_id', type=int)
    if author_id:
        query = query.filter(Artwork.user_id == author_id)

    # 排序: latest（默认，创建时间倒序）
    sort = (request.args.get('sort') or 'latest').strip().lower()
    order = Artwork.created_at.desc()  # latest 与默认一致；其他值回退 latest
    query = query.order_by(order)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # like_count / comment_count 真实批量统计（一次 GROUP BY，无 N+1）
    artwork_ids = [artwork.id for artwork in pagination.items]
    like_counts = {}
    comment_counts = {}
    collect_counts = {}
    if artwork_ids:
        like_rows = (
            db.session.query(Like.artwork_id, db.func.count(Like.id))
            .filter(Like.artwork_id.in_(artwork_ids))
            .group_by(Like.artwork_id)
            .all()
        )
        like_counts = {artwork_id: count for artwork_id, count in like_rows}
        comment_rows = (
            db.session.query(Comment.artwork_id, db.func.count(Comment.id))
            .filter(Comment.artwork_id.in_(artwork_ids))
            .group_by(Comment.artwork_id)
            .all()
        )
        comment_counts = {artwork_id: count for artwork_id, count in comment_rows}
        collect_rows = (
            db.session.query(Collection.artwork_id, db.func.count(Collection.id))
            .filter(Collection.artwork_id.in_(artwork_ids))
            .group_by(Collection.artwork_id)
            .all()
        )
        collect_counts = {artwork_id: count for artwork_id, count in collect_rows}

    items = []
    for artwork in pagination.items:
        data = artwork.to_dict()
        data['like_count'] = like_counts.get(artwork.id, 0)       # 覆盖列为真实统计
        data['comment_count'] = comment_counts.get(artwork.id, 0)  # 真实评论数
        data['collect_count'] = collect_counts.get(artwork.id, 0)  # 真实收藏数
        items.append(data)
    return APIResponse.paginated(
        items=items,
        total=pagination.total,
        page=page,
        page_size=per_page,
        message='获取作品列表成功',
    )


@api_bp.route('/workshop/works/<artwork_id>', methods=['GET'])
def get_artwork(artwork_id):
    """作品详情

    规则: 公开作品允许访问；私有作品仅作者可见；不存在 → 404
    响应 data 扩展：
      - 基础信息 + author + like_count/view_count（to_dict）
      - comment_count: 真实评论数
      - current_user_status: 当前用户交互状态预留（liked/collected/is_author）
    """
    artwork = _get_artwork_or_404(artwork_id)

    user = get_authenticated_user()
    is_author = user is not None and user.id == artwork.user_id

    if not artwork.is_public and not is_author:
        raise ResourceNotFoundError('作品不存在')

    # 浏览量 +1（公开浏览计数；作者本人查看也计数，保持简单一致）
    artwork.increment_view_count()
    db.session.commit()

    data = artwork.to_dict(include_details=True)
    # like_count 真实统计 + current_user_status.liked 真实查询
    data['like_count'] = artwork.likes.count()
    liked = (
        user is not None
        and Like.query.filter_by(user_id=user.id, artwork_id=artwork.id).first() is not None
    )
    # comment_count 真实统计； collect_count + collected 真实
    data['comment_count'] = artwork.comments.count()
    data['collect_count'] = artwork.collections.count()
    collected = (
        user is not None
        and Collection.query.filter_by(user_id=user.id, artwork_id=artwork.id).first() is not None
    )
    data['current_user_status'] = {
        'liked': liked,            # 真实点赞状态
        'collected': collected,    # 真实收藏状态
        'is_author': is_author,
    }

    return APIResponse.success(
        data=data,
        message='获取作品详情成功',
        code=200,
    )


def _check_like_target(artwork):
    """点赞/取消点赞目标校验: 私有作品不可互动（非作者 404 不泄露；作者 400 明确）"""
    return _check_public_interaction_target(artwork, action='点赞')


def _check_public_interaction_target(artwork, action='操作'):
    """公开互动（点赞/评论）目标校验

    规则: 登录必需（None → 401）；私有作品不可互动——
      非作者 → 404（不泄露存在性）；作者 → 400（明确不可互动）

    Returns:
        User: 认证用户
    """
    user = get_authenticated_user()
    if user is None:
        raise AuthenticationError('登录凭证无效或已过期')
    if not artwork.is_public:
        if user.id == artwork.user_id:
            raise ValidationError(f'私有作品不可{action}')
        raise ResourceNotFoundError('作品不存在')
    return user


def _like_count(artwork):
    """真实点赞数"""
    return artwork.likes.count()


@api_bp.route('/workshop/works/<artwork_id>/like', methods=['POST'])
def like_artwork(artwork_id):
    """点赞作品

    认证: 登录用户（JWT/Session）
    幂等: 已点赞再次点赞 → 直接成功（不重复计数）
    规则: 私有作品不可操作（非作者 404 不泄露存在性；作者 400 明确不可点赞）
    响应: {"liked": true, "like_count": <真实统计>}
    """
    artwork = _get_artwork_or_404(artwork_id)
    user = _check_like_target(artwork)

    exists = Like.query.filter_by(user_id=user.id, artwork_id=artwork.id).first()
    if exists is None:
        db.session.add(Like(user_id=user.id, artwork_id=artwork.id))
        db.session.commit()

    return APIResponse.success(
        data={'liked': True, 'like_count': _like_count(artwork)},
        message='点赞成功',
        code=200,
    )


@api_bp.route('/workshop/works/<artwork_id>/like', methods=['DELETE'])
def unlike_artwork(artwork_id):
    """取消点赞

    认证: 登录用户
    幂等: 未点赞时取消 → 直接成功（不报错）
    规则: 私有作品不可操作（同点赞）
    响应: {"liked": false, "like_count": <真实统计>}
    """
    artwork = _get_artwork_or_404(artwork_id)
    user = _check_like_target(artwork)

    exists = Like.query.filter_by(user_id=user.id, artwork_id=artwork.id).first()
    if exists is not None:
        db.session.delete(exists)
        db.session.commit()

    return APIResponse.success(
        data={'liked': False, 'like_count': _like_count(artwork)},
        message='取消点赞成功',
        code=200,
    )


def _collect_count(artwork):
    """真实收藏数"""
    return artwork.collections.count()


@api_bp.route('/workshop/works/<artwork_id>/collect', methods=['POST'])
def collect_artwork(artwork_id):
    """收藏作品

    认证: 登录用户
    幂等: 已收藏再次收藏 → 直接成功（不重复计数）
    规则: 私有作品不可操作（非作者 404 不泄露；作者 400 明确不可收藏，同 Like）
    响应: {"collected": true, "collect_count": <真实统计>}
    """
    artwork = _get_artwork_or_404(artwork_id)
    user = _check_public_interaction_target(artwork, action='收藏')

    exists = Collection.query.filter_by(user_id=user.id, artwork_id=artwork.id).first()
    if exists is None:
        db.session.add(Collection(user_id=user.id, artwork_id=artwork.id))
        db.session.commit()

    return APIResponse.success(
        data={'collected': True, 'collect_count': _collect_count(artwork)},
        message='收藏成功',
        code=200,
    )


@api_bp.route('/workshop/works/<artwork_id>/collect', methods=['DELETE'])
def uncollect_artwork(artwork_id):
    """取消收藏

    认证: 登录用户
    幂等: 未收藏时取消 → 直接成功（不报错）
    响应: {"collected": false, "collect_count": <真实统计>}
    """
    artwork = _get_artwork_or_404(artwork_id)
    user = _check_public_interaction_target(artwork, action='收藏')

    exists = Collection.query.filter_by(user_id=user.id, artwork_id=artwork.id).first()
    if exists is not None:
        db.session.delete(exists)
        db.session.commit()

    return APIResponse.success(
        data={'collected': False, 'collect_count': _collect_count(artwork)},
        message='取消收藏成功',
        code=200,
    )


@api_bp.route('/workshop/works/<artwork_id>', methods=['PUT'])
def update_artwork(artwork_id):
    """更新作品（仅作者本人）

    认证: get_authenticated_user()
    权限: 非作者 → 403
    安全: 不允许修改 user_id/id/统计/存证字段（白名单过滤）
    """
    user = _get_authenticated_user_or_401()
    artwork = _get_artwork_or_404(artwork_id)

    if artwork.user_id != user.id:
        raise PermissionError_('没有权限修改该作品')

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        raise ValidationError('请求数据不能为空')

    fields = _extract_fields(data, UPDATE_FIELDS)
    if 'title' in fields:
        fields = _validate_create_fields(fields)

    for key, value in fields.items():
        setattr(artwork, key, value)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise ValidationError('作品更新失败，请稍后重试')

    return APIResponse.success(
        data=artwork.to_dict(include_details=True),
        message='作品更新成功',
        code=200,
    )


@api_bp.route('/workshop/works/<artwork_id>', methods=['DELETE'])
def delete_artwork(artwork_id):
    """删除作品（仅作者本人）

    认证: get_authenticated_user()
    权限: 非作者 → 403；不存在 → 404
    说明: 仅删除数据库记录，不删除服务器上传文件
          （文件可能被其他记录引用，生命周期管理留待后续专门设计）
    """
    user = _get_authenticated_user_or_401()
    artwork = _get_artwork_or_404(artwork_id)

    if artwork.user_id != user.id:
        raise PermissionError_('没有权限删除该作品')

    db.session.delete(artwork)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise ValidationError('作品删除失败，请稍后重试')

    return APIResponse.success(
        data={'id': artwork_id},
        message='作品删除成功',
        code=200,
    )


# ------------------------------------------------------------
# 评论
# ------------------------------------------------------------
def _get_comment_or_404(comment_id):
    """按 ID 获取评论，不存在抛 404"""
    comment = db.session.get(Comment, comment_id)
    if comment is None:
        raise ResourceNotFoundError('评论不存在')
    return comment


@api_bp.route('/workshop/works/<artwork_id>/comments', methods=['POST'])
def create_comment(artwork_id):
    """发表评论

    认证: 登录用户
    规则: 私有作品不可评论（非作者 404/作者 400）；作品不存在 404
    校验: content 非空且 ≤1000 字符
    响应: {"comment": {...}}（创建后的评论）
    """
    artwork = _get_artwork_or_404(artwork_id)
    user = _check_public_interaction_target(artwork, action='评论')

    data = request.get_json(silent=True)
    content = (data or {}).get('content')
    if not content or not str(content).strip():
        raise ValidationError('评论内容不能为空')
    content = str(content).strip()
    if len(content) > COMMENT_MAX_LENGTH:
        raise ValidationError(f'评论内容长度不能超过{COMMENT_MAX_LENGTH}个字符')

    comment = Comment(user_id=user.id, artwork_id=artwork.id, content=content)
    db.session.add(comment)
    db.session.commit()

    return APIResponse.success(
        data={'comment': comment.to_dict()},
        message='评论发表成功',
        code=200,
    )


@api_bp.route('/workshop/works/<artwork_id>/comments', methods=['GET'])
def list_comments(artwork_id):
    """评论列表

    规则: 公开作品可查看；私有作品仅作者可查看（非作者 404 不泄露）
    分页: page / per_page（默认 10，最大 50），按创建时间倒序
    响应: APIResponse.paginated（items=[comment.to_dict()]）
    """
    artwork = _get_artwork_or_404(artwork_id)

    user = get_authenticated_user()
    is_author = user is not None and user.id == artwork.user_id
    if not artwork.is_public and not is_author:
        raise ResourceNotFoundError('作品不存在')

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 50))

    query = (Comment.query
             .filter_by(artwork_id=artwork.id)
             .order_by(Comment.created_at.desc()))
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return APIResponse.paginated(
        items=[c.to_dict() for c in pagination.items],
        total=pagination.total,
        page=page,
        page_size=per_page,
        message='获取评论列表成功',
    )


@api_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    """删除评论（仅评论作者）

    认证: 登录用户
    权限: 非作者 → 403；评论不存在 → 404
    """
    user = _get_authenticated_user_or_401()
    comment = _get_comment_or_404(comment_id)

    if comment.user_id != user.id:
        raise PermissionError_('没有权限删除该评论')

    db.session.delete(comment)
    db.session.commit()

    return APIResponse.success(
        data={'id': comment_id},
        message='评论删除成功',
        code=200,
    )
