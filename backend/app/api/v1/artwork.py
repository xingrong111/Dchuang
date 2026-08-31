# ============================================================
# 智绘锡承 - 作品管理 API（阶段7 Artwork CRUD）
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
from app.utils.auth import get_authenticated_user
from app.utils.exceptions import (
    ValidationError,
    AuthenticationError,
    PermissionError_,
    ResourceNotFoundError,
)
from app.utils.response import APIResponse

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
    """作品列表（公开浏览，支持分页）

    查询参数: page（默认1）, per_page（默认10, 最大100）
    规则: 仅返回 is_public=True 的公开作品，按创建时间倒序
    响应: APIResponse.paginated（统一分页格式）
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    page = max(page, 1)
    per_page = max(1, min(per_page, 100))

    query = Artwork.query.filter_by(is_public=True).order_by(Artwork.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [artwork.to_dict() for artwork in pagination.items]
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
    """
    artwork = _get_artwork_or_404(artwork_id)

    user = get_authenticated_user()
    is_author = user is not None and user.id == artwork.user_id

    if not artwork.is_public and not is_author:
        raise ResourceNotFoundError('作品不存在')

    # 浏览量 +1（公开浏览计数；作者本人查看也计数，保持简单一致）
    artwork.increment_view_count()
    db.session.commit()

    return APIResponse.success(
        data=artwork.to_dict(include_details=True),
        message='获取作品详情成功',
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
