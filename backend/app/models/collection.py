# ============================================================
# 智绘锡承 - 作品收藏模型
# 位置: backend/app/models/collection.py
#
# 设计（与 Like 平行）:
#   - 唯一约束 (user_id, artwork_id) —— 一人一收藏，重复收藏幂等
#   - artwork 删除 → collections 级联删除（关系层 cascade + DB ondelete CASCADE）
#   - collect_count 权威统计: count(Collection)；无冗余列
# ============================================================
from datetime import datetime

from app.extensions import db


class Collection(db.Model):
    """作品收藏"""
    __tablename__ = 'artwork_collections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    artwork_id = db.Column(
        db.String(64),
        db.ForeignKey('artworks.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # 一人一收藏（幂等依据）
    __table_args__ = (
        db.UniqueConstraint('user_id', 'artwork_id', name='uq_artwork_collections_user_artwork'),
    )

    # --- 关系（artwork.collections / user.collections 可用） ---
    user = db.relationship('User', backref=db.backref(
        'collections', lazy='dynamic', cascade='all, delete-orphan'
    ))
    artwork = db.relationship('Artwork', backref=db.backref(
        'collections', lazy='dynamic', cascade='all, delete-orphan'
    ))

    def __repr__(self):
        return f'<Collection user={self.user_id} artwork={self.artwork_id}>'
