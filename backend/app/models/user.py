# ============================================================
# 智绘锡承 - 用户数据模型
# 位置: backend/app/models/user.py（依据规范 4.2.1）
#
# 设计依据:
# - 《项目开发规范文档 v1.0》4.2.1 User / UserProfile 模型
# - A_qianduan 前端: RegisterView.vue (username/email/password)、
#   LoginView.vue (email/password)、userStore.js、ProfileView.vue (avatar/bio)
#
# 安全要求:
# - 密码只存 password_hash（werkzeug），绝不存明文
# - to_dict() 绝不返回 password_hash
# ============================================================
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'

    # --- 主键 ---
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # --- 登录凭证 ---
    # 前端登录使用 email + password；username 用于展示（均唯一）
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    # --- 用户资料 ---
    avatar = db.Column(db.String(255), default='default_avatar.png')
    bio = db.Column(db.String(500))
    location = db.Column(db.String(100))
    website = db.Column(db.String(255))

    # --- 用户状态（规范 4.2.1） ---
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    level = db.Column(db.Enum('normal', 'vip', 'svip'), default='normal')

    # --- 时间戳 ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- 模型关系 ---

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    # ------------------------------------------------------------
    # 密码方法
    # ------------------------------------------------------------
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------
    def to_dict(self, include_sensitive=False):
        """转换为字典（用于 API 响应）

        Args:
            include_sensitive: 是否包含邮箱（默认 False，与规范 4.2.1 一致；
                                登录/个人接口按需开启）
        注意: 任何情况下都不返回 password_hash
        """
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_sensitive else None,
            'avatar': self.avatar,
            'bio': self.bio,
            'location': self.location,
            'website': self.website,
            'level': self.level,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        return data

    def __repr__(self):
        return f'<User {self.username}>'


class UserProfile(db.Model):
    """用户资料扩展模型（规范 4.2.1 明确要求）"""
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)

    # --- 社交链接 ---
    github_url = db.Column(db.String(255))
    weibo_url = db.Column(db.String(255))
    bilibili_url = db.Column(db.String(255))
    zhihu_url = db.Column(db.String(255))

    # --- 隐私设置 ---
    show_email = db.Column(db.Boolean, default=False)
    show_location = db.Column(db.Boolean, default=True)

    # --- 偏好设置 ---
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(10), default='zh-CN')

    # --- 时间戳 ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- 关系 ---
    user = db.relationship('User', backref=db.backref('profile', uselist=False))

    def to_dict(self):
        """转换为字典"""
        return {
            'github_url': self.github_url,
            'weibo_url': self.weibo_url,
            'bilibili_url': self.bilibili_url,
            'zhihu_url': self.zhihu_url,
            'theme': self.theme,
            'language': self.language,
        }

    def __repr__(self):
        return f'<UserProfile user_id={self.user_id}>'
