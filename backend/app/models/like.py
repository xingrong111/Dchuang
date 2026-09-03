# ============================================================
# 智绘锡承 - 作品点赞模型（阶段14-B）
# 位置: backend/app/models/like.py
#
# 设计:
#   - 唯一约束 (user_id, artwork_id) —— 一人一赞，重复点赞幂等
#   - artwork 删除 → likes 级联删除（关系层 cascade + DB ondelete CASCADE）
#   - like_count 权威统计来源: 查询 count(Like)；Artwork.like_count 列保留
#     但不再手动维护（避免双写不一致，接口统一以 count 为准）
# ============================================================
from datetime import datetime

from app.extensions import db


class Like(db.Model):
    """作品点赞（阶段14-B）"""
    __tablename__ = 'artwork_likes'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    artwork_id = db.Column(
        db.String(64),
        db.ForeignKey('artworks.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 一人一赞（幂等依据）
    __table_args__ = (
        db.UniqueConstraint('user_id', 'artwork_id', name='uq_artwork_likes_user_artwork'),
    )

    # --- 关系（artwork.likes / user.likes 可用） ---
    user = db.relationship('User', backref=db.backref(
        'likes', lazy='dynamic', cascade='all, delete-orphan'
    ))
    artwork = db.relationship('Artwork', backref=db.backref(
        'likes', lazy='dynamic', cascade='all, delete-orphan'
    ))

    def __repr__(self):
        return f'<Like user={self.user_id} artwork={self.artwork_id}>'
