# ============================================================
# 智绘锡承 - 管理员操作日志（阶段16-A）
# 位置: backend/app/models/admin_log.py
#
# 用途: 审计后台管理操作（任务强制重试/后续运营动作），可追踪
#   admin_user_id（操作管理员）/ target_type/target_id（对象）/ detail
# ============================================================
from datetime import datetime

from app.extensions import db


class AdminLog(db.Model):
    """管理员操作日志（阶段16-A）"""
    __tablename__ = 'admin_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)  # 如 task_retry
    target_type = db.Column(db.String(30), nullable=False)         # 如 aitask / artwork / user
    target_id = db.Column(db.String(64), nullable=False)           # 对象 ID（task id 等）
    detail = db.Column(db.Text)                                    # JSON/文本详情
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    admin = db.relationship('User', backref=db.backref('admin_logs', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'admin_user_id': self.admin_user_id,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'detail': self.detail,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<AdminLog {self.action} {self.target_type}:{self.target_id}>'
