# ============================================================
# 智绘锡承 - 作品数据模型
# 位置: backend/app/models/artwork.py
#
# 字段定义依据: 《项目开发规范文档 v1.0》4.2.2 数据模型规范（Artwork）
# 设计定位: Artwork 是 Workshop 保存作品 / Community 社区作品 /
#           Profile 我的作品 / AI 文生3D / 风格分析 / 区块链存证 的公共数据基础。
#
# Artwork 与点赞、评论、收藏及 AI 任务共同构成作品领域模型。
# ============================================================
import uuid
from datetime import datetime

from app.extensions import db


def _generate_uuid():
    """生成 UUID 字符串主键（规范 4.2.2: id = String(64), UUID格式）"""
    return str(uuid.uuid4())


class Artwork(db.Model):
    """作品模型（规范 4.2.2）"""
    __tablename__ = 'artworks'

    # --- 主键（UUID 字符串格式，规范 4.2.2） ---
    id = db.Column(db.String(64), primary_key=True, default=_generate_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # --- 作品信息 ---
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.JSON, default=list)  # 标签列表

    # --- 3D 模型信息 ---
    model_url = db.Column(db.String(500))
    model_format = db.Column(db.Enum('glb', 'gltf', 'obj', 'stl'), default='glb')
    model_size = db.Column(db.Integer)  # 文件大小（字节）
    thumbnail = db.Column(db.String(500))  # 缩略图URL

    # --- AI 生成信息 ---
    is_ai_generated = db.Column(db.Boolean, default=False)
    ai_model = db.Column(db.String(50))
    ai_prompt = db.Column(db.Text)
    ai_params = db.Column(db.JSON)  # AI生成参数

    # --- 风格分析 ---
    style_analysis = db.Column(db.JSON)  # 风格分析结果

    # --- 区块链存证（预留，存证阶段使用） ---
    blockchain_hash = db.Column(db.String(256))
    blockchain_tx_id = db.Column(db.String(256))
    is_certified = db.Column(db.Boolean, default=False)

    # --- 权限设置 ---
    is_public = db.Column(db.Boolean, default=True)
    allow_download = db.Column(db.Boolean, default=False)
    license_type = db.Column(db.String(50), default='all-rights-reserved')

    # --- 统计信息 ---
    view_count = db.Column(db.Integer, default=0)
    like_count = db.Column(db.Integer, default=0)
    download_count = db.Column(db.Integer, default=0)

    # --- 时间戳 ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- 关系 ---
    author = db.relationship('User', backref=db.backref(
        'artworks', lazy='dynamic', cascade='all, delete-orphan'
    ))

    # ------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------
    def to_dict(self, include_details=False):
        """转换为字典（用于 API 响应）

        安全要求:
        - 硬编码允许返回字段，不直接暴露 SQLAlchemy 内部对象
        - 绝不包含 password_hash / session / token 等认证秘密
        - author 仅返回必要公开字段（id/username/avatar）
        """
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'tags': self.tags or [],
            'model_url': self.model_url,
            'model_format': self.model_format,
            'thumbnail': self.thumbnail,
            'is_ai_generated': self.is_ai_generated,
            'is_certified': self.is_certified,
            'is_public': self.is_public,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'author': {
                'id': self.author.id,
                'username': self.author.username,
                'avatar': self.author.avatar,
            } if self.author else None,
        }

        if include_details:
            data.update({
                'model_size': self.model_size,
                'allow_download': self.allow_download,
                'license_type': self.license_type,
                'download_count': self.download_count,
                'ai_model': self.ai_model,
                'ai_prompt': self.ai_prompt,
                'ai_params': self.ai_params,
                'style_analysis': self.style_analysis,
                'blockchain_hash': self.blockchain_hash,
                'blockchain_tx_id': self.blockchain_tx_id,
            })

        return data

    def increment_view_count(self):
        """增加浏览计数"""
        self.view_count += 1

    def __repr__(self):
        return f'<Artwork {self.title}>'
