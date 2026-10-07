# ============================================================
# 智绘锡承 - 用户认证 API
# 位置: backend/app/api/v1/auth.py
#
# 接口前缀约定（重要）:
# 前端 Vite 代理将 /api 剥除后转发到 Flask，因此本蓝图路由为:
#   POST /auth/register   （前端 POST /api/auth/register）
#   POST /auth/login      （前端 POST /api/auth/login）
#   GET  /auth/user       （前端 GET  /api/auth/user）
#
# 契约依据（A_qianduan 真实代码）:
# - RegisterView.vue: 请求 {username, email, password}，成功判断 code === 200
# - LoginView.vue:     请求 {email, password}，成功判断 code === 200
# - userStore.js:      user = response.data，即 data 必须含 token 且为扁平结构
# - axios 拦截器:      Authorization: Bearer <token>（data.token）
# ============================================================
import re

from flask import request, session
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app.api.v1 import api_bp
from app.extensions import db
from app.models.user import User, UserProfile
from app.services.credit import CreditService
from app.utils.exceptions import ValidationError, AuthenticationError
from app.utils.response import APIResponse

# 与前端 RegisterView.vue 校验规则保持一致
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
USERNAME_RE = re.compile(r'^[a-zA-Z0-9\u4e00-\u9fa5]+$')
PASSWORD_MIN_LENGTH = 6
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20


def _get_json_body():
    """获取并校验 JSON 请求体"""
    if not request.is_json:
        raise ValidationError('请求必须为 application/json 格式')
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        raise ValidationError('请求数据不能为空')
    return data


def _validate_register_data(data):
    """校验注册字段（返回清洗后的字段）"""
    for field in ('username', 'email', 'password'):
        if not isinstance(data.get(field), str):
            raise ValidationError(f'{field} 必须为字符串')
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not username:
        raise ValidationError('用户名不能为空')
    if not (USERNAME_MIN_LENGTH <= len(username) <= USERNAME_MAX_LENGTH):
        raise ValidationError('用户名长度需在3-20个字符之间')
    if not USERNAME_RE.match(username):
        raise ValidationError('用户名只能包含字母、数字和中文')

    if not email:
        raise ValidationError('邮箱不能为空')
    if not EMAIL_RE.match(email):
        raise ValidationError('邮箱格式不正确')

    if not password:
        raise ValidationError('密码不能为空')
    if len(password) > 128 or len(email) > 120:
        raise ValidationError('邮箱或密码超出长度限制')
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationError(f'密码长度不能少于{PASSWORD_MIN_LENGTH}位')

    return username, email, password


@api_bp.route('/auth/register', methods=['POST'])
def register():
    """用户注册

    请求: {"username": "...", "email": "...", "password": "..."}
    响应: {"code": 200, "message": "注册成功", "data": {用户信息}}
    约定: 不自动登录、不返回 JWT Token（前端注册成功后跳转登录页）
    """
    data = _get_json_body()
    username, email, password = _validate_register_data(data)

    # 唯一性检查（username / email）
    if User.query.filter_by(username=username).first():
        raise ValidationError('用户名或邮箱已存在')
    if User.query.filter_by(email=email).first():
        raise ValidationError('用户名或邮箱已存在')

    # 创建用户（set_password 内部完成 werkzeug 哈希，不存明文）
    user = User(username=username, email=email, password=password)
    # 创建关联的 UserProfile（利用现有模型关系）
    user.profile = UserProfile()

    db.session.add(user)
    try:
        db.session.flush()
        CreditService.init_account(user.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise ValidationError('注册失败，请稍后重试')

    return APIResponse.success(
        data=user.to_dict(include_sensitive=True),
        message='注册成功',
        code=200,
    )


@api_bp.route('/auth/login', methods=['POST'])
def login():
    """用户登录（严格使用 email + password）

    请求: {"email": "...", "password": "..."}
    响应: {"code": 200, "message": "登录成功",
           "data": {"token": "<JWT>", "id": 1, "username": "...",
                    "email": "...", "avatar": "...", "bio": "..."}}
    约定: data.token 必须存在（前端 userStore.user = response.data）
    """
    data = _get_json_body()
    if not isinstance(data.get('email'), str) or not isinstance(data.get('password'), str):
        raise ValidationError('邮箱和密码必须为字符串')
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    if not email:
        raise ValidationError('邮箱不能为空')
    if not password:
        raise ValidationError('密码不能为空')

    user = User.query.filter_by(email=email).first()
    # 统一错误提示，避免泄露用户是否存在
    if not user or not user.check_password(password):
        raise AuthenticationError('邮箱或密码错误')

    # 禁用用户拒绝登录
    if not user.is_active:
        raise AuthenticationError('账号已被禁用，请联系管理员')

    # 生成 JWT Access Token（identity 使用用户 id）
    access_token = create_access_token(identity=str(user.id))

    # 建立安全 Flask Session，兼容 el-upload 自动携带 Cookie 的场景
    # 身份来源为服务端验证后的 user.id（可信），与 JWT identity 一致
    session.clear()
    session['user_id'] = user.id
    session.permanent = True  # 使用 PERMANENT_SESSION_LIFETIME（24h）

    return APIResponse.success(
        data={
            'token': access_token,
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'avatar': user.avatar,
            'bio': user.bio,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        },
        message='登录成功',
        code=200,
    )


@api_bp.route('/auth/user', methods=['GET'])
@jwt_required()
def get_current_user():
    """获取当前登录用户信息

    请求头: Authorization: Bearer <token>
    响应: {"code": 200, "message": "获取用户信息成功",
           "data": {id, username, email, avatar, bio, ...}}
    """
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        raise AuthenticationError('登录凭证无效或已过期')

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        raise AuthenticationError('登录凭证无效或已过期')

    return APIResponse.success(
        data=user.to_dict(include_sensitive=True),
        message='获取用户信息成功',
        code=200,
    )


@api_bp.post('/auth/logout')
def logout():
    # 不要求有效 JWT，使过期登录也能清除上传接口使用的 Session。
    session.clear()
    return APIResponse.success(message='已退出登录')


# ============================================================
# 密码重置（忘记密码）
# ============================================================

@api_bp.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    """发送密码重置验证码

    请求: {"email": "..."}
    响应: {"code": 200, "message": "验证码已发送"}
    安全: 无论邮箱是否存在都返回相同信息（防枚举）
    """
    data = _get_json_body()
    if not isinstance(data.get('email'), str):
        raise ValidationError('邮箱必须为字符串')
    email = (data.get('email') or '').strip()
    if not email or not EMAIL_RE.match(email):
        raise ValidationError('邮箱格式不正确')

    # 查找用户（存在才发邮件；不存在也返回成功，防邮箱枚举）
    user = User.query.filter_by(email=email).first()
    if user:
        from app.utils.verification_code import generate_code
        from app.utils.email import send_verification_email

        try:
            code = generate_code(email)
        except ValueError as e:
            raise ValidationError(str(e))

        if not send_verification_email(email, code):
            from app.utils.verification_code import clear_code
            clear_code(email)

    return APIResponse.success(
        message='验证码已发送，请查收邮件',
        code=200,
    )


@api_bp.route('/auth/reset-password', methods=['POST'])
def reset_password():
    """验证码重置密码

    请求: {"email": "...", "code": "123456", "new_password": "..."}
    响应: {"code": 200, "message": "密码重置成功"}
    """
    data = _get_json_body()
    for field in ('email', 'code', 'new_password'):
        if not isinstance(data.get(field), str):
            raise ValidationError(f'{field} 必须为字符串')
    email = (data.get('email') or '').strip()
    code = (data.get('code') or '').strip()
    new_password = data.get('new_password') or ''

    if not email or not EMAIL_RE.match(email):
        raise ValidationError('邮箱格式不正确')
    if not code:
        raise ValidationError('验证码不能为空')
    if not PASSWORD_MIN_LENGTH <= len(new_password) <= 128:
        raise ValidationError(f'密码至少 {PASSWORD_MIN_LENGTH} 位')

    # 校验验证码
    from app.utils.verification_code import verify_code, clear_code
    try:
        verify_code(email, code)
    except ValueError as e:
        raise ValidationError(str(e))

    # 查找用户并重置密码
    user = User.query.filter_by(email=email).first()
    if not user:
        raise ValidationError('账号不存在')

    user.set_password(new_password)
    db.session.commit()
    clear_code(email)

    return APIResponse.success(
        message='密码重置成功，请使用新密码登录',
        code=200,
    )
