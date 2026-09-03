# ============================================================
# 智绘锡承 - 作品评论模型（阶段14-C）
# 位置: backend/app/models/comment.py
#
# 设计:
#   - artwork 删除 → comments 级联删除（关系层 cascade + DB ondelete CASCADE）
#   - comment_count 权威来源: count(Comment)；Artwork 无冗余列（直接统计）
#   - 评论内容上限: 服务层校验（1000 字符）
# ============================================================
from datetime import datetime

from app.extensions import db


class Comment(db.Model):
    """作品评论（阶段14-C）"""
    __tablename__ = 'artwork_comments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    artwork_id = db.Column(
        db.String(64),
        db.ForeignKey('artworks.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- 关系（artwork.comments / user.comments 可用） ---
    user = db.relationship('User', backref=db.backref(
        'comments', lazy='dynamic', cascade='all, delete-orphan'
    ))
    artwork = db.relationship('Artwork', backref=db.backref(
        'comments', lazy='dynamic', cascade='all, delete-orphan'
    ))

    def to_dict(self):
        """序列化（安全: 不含敏感字段，author 仅公开信息）"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'artwork_id': self.artwork_id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'author': {
                'id': self.user.id,
                'username': self.user.username,
                'avatar': self.user.avatar,
            } if self.user else None,
        }

    def __repr__(self):
        return f'<Comment {self.id} user={self.user_id} artwork={self.artwork_id}>'
