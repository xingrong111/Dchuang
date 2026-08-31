# ============================================================
# 智绘锡承 - 文件上传 API
# 位置: backend/app/api/v1/upload.py（阶段5 文件上传服务）
#
# 接口前缀约定: 前端 Vite 代理剥 /api 后转发，本蓝图路由无 /api 前缀:
#   POST /workshop/upload      （前端 POST /api/workshop/upload）
#   POST /user/upload-avatar   （前端 POST /api/user/upload-avatar）
#
# 响应契约（A_qianduan 真实代码）:
# - CommunityView.vue handleUploadSuccess: 读取 response.data.url
#   → 响应必须为 {"code":200,"message":...,"data":{"url":"..."}}
#
# 认证设计（重要）:
# 1. /workshop/upload:
#    - 暂不要求 JWT（兼容 CommunityView.vue 的 el-upload 直发，其不带 Bearer）
#    - 【安全技术债务】匿名可上传，后续需收紧为 @jwt_required()
#      （AdvancedMultiModalInput.vue 走 axios 已带 Bearer；CommunityView el-upload 需前端加 headers 或改用封装）
# 2. /user/upload-avatar:
#    - 强制 @jwt_required()（身份识别安全优先）
#    - 从 JWT identity 获取当前用户，更新其 avatar
#    - 【禁止】接受客户端提交的 user_id/username 等不可信字段
#    - 注意: 当前 ProfileView.vue 的 el-upload 未带 Bearer，调用将 401；
#      需 A 同学前端配合（el-upload 加 :headers 或改用 axios 封装）后头像上传才可用
# ============================================================
from flask import request, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api.v1 import api_bp
from app.extensions import db
from app.models.user import User
from app.utils.exceptions import ValidationError, AuthenticationError
from app.utils.files import (
    save_upload_file,
    build_file_url,
)
from app.utils.response import APIResponse


@api_bp.route('/static/uploads/<path:filename>', methods=['GET'])
def serve_uploaded_file(filename):
    """提供上传文件访问（无需认证，公开可读）

    前端 data.url = /api/static/uploads/<path> → Vite 剥 /api → 本路由
    安全: send_from_directory 只从 UPLOAD_FOLDER 目录内读取，防路径穿越
    """
    return send_from_directory(_upload_root(), filename)


def _upload_root():
    """读取 UPLOAD_FOLDER 配置"""
    from flask import current_app
    return current_app.config['UPLOAD_FOLDER']


@api_bp.route('/workshop/upload', methods=['POST'])
def workshop_upload():
    """上传文件（图片 / 3D 模型等）

    请求: multipart/form-data，字段名 file（前端 workshop.js: formData.append('file', file)）
    响应: {"code": 200, "message": "上传成功", "data": {"url": "/api/static/uploads/..."}}

    认证说明: 暂不要求 JWT（兼容 CommunityView el-upload）；安全技术债务见文件头注释。
    """
    if 'file' not in request.files:
        raise ValidationError('未接收到文件（字段名应为 file）')

    file_storage = request.files['file']
    # 默认子目录: 图片 → images，3D 模型 → models（按扩展名分流）
    from app.utils.files import get_extension
    ext = get_extension(file_storage.filename or '')
    subdir = 'models' if ext in ('glb', 'gltf', 'obj', 'stl') else 'images'

    rel_path = save_upload_file(file_storage, subdir=subdir)
    return APIResponse.success(
        data={'url': build_file_url(rel_path)},
        message='上传成功',
        code=200,
    )


@api_bp.route('/user/upload-avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    """上传当前用户头像

    请求: multipart/form-data，字段名 file（el-upload 默认字段名）
    认证: 必须携带 Authorization: Bearer <token>（@jwt_required）
    身份: 仅从 JWT identity 获取当前用户，【不信任任何客户端提交的用户标识字段】
    响应: {"code": 200, "message": "头像上传成功", "data": {"url": "/api/static/uploads/..."}}
    """
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        raise AuthenticationError('登录凭证无效或已过期')

    user = db.session.get(User, user_id)
    if not user:
        raise AuthenticationError('登录凭证无效或已过期')

    if 'file' not in request.files:
        raise ValidationError('未接收到文件（字段名应为 file）')

    file_storage = request.files['file']
    rel_path = save_upload_file(file_storage, subdir='avatars')
    url = build_file_url(rel_path)

    # 更新当前用户头像（身份来自 JWT，非客户端提交）
    user.avatar = url
    db.session.commit()

    return APIResponse.success(
        data={'url': url},
        message='头像上传成功',
        code=200,
    )
