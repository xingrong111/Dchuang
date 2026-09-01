# ============================================================
# 智绘锡承 - AI 任务数据模型
# 位置: backend/app/models/ai_task.py（阶段9 AI 基础设施）
#
# 设计依据: 《AI 多模态模块架构设计报告》AITask 模型设计
# 定位: AITask 记录一次 AI 生成/分析任务的完整生命周期，
#       成功后关联 Artwork（方案 B: 成功后创建作品并回填 artwork_id）。
#
# 本阶段仅实现基础设施（Mock Provider），不调用真实收费 API。
# ============================================================
import uuid
from datetime import datetime

from app.extensions import db


def _generate_uuid():
    """生成 UUID 字符串主键（与 Artwork 保持一致）"""
    return str(uuid.uuid4())


class AITask(db.Model):
    """AI 任务模型"""
    __tablename__ = 'ai_tasks'

    # --- 主键（UUID 字符串格式，与 Artwork 一致） ---
    id = db.Column(db.String(64), primary_key=True, default=_generate_uuid)
    # 归属用户（必填）
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # 关联作品（可空：任务成功前无作品，成功后回填）
    # 阶段10 A2: ON DELETE SET NULL —— Artwork 删除后任务保留，artwork_id 置 NULL（保留 AI 任务历史）
    artwork_id = db.Column(
        db.String(64),
        db.ForeignKey('artworks.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )

    # --- Provider 信息 ---
    provider = db.Column(db.String(30), nullable=False, default='mock')   # 'mock' | 'hunyuan' | 'glm'
    model = db.Column(db.String(50), nullable=False, default='mock-3d')   # 具体模型名
    task_type = db.Column(db.String(30), nullable=False)                  # 'text_to_3d' | 'image_to_3d' | 'analyze_style'

    # --- 输入 ---
    prompt = db.Column(db.Text)                    # 文生3D 提示词
    input_url = db.Column(db.String(500))          # 图生3D / 风格分析输入图片 URL

    # --- 执行状态 ---
    external_task_id = db.Column(db.String(128), index=True)  # 第三方任务 ID（可空）
    status = db.Column(db.String(20), nullable=False, default='PENDING', index=True)
    result_url = db.Column(db.String(500))         # 生成结果 URL（3D 模型/图片）
    error_message = db.Column(db.Text)             # 失败原因

    # --- 时间戳 ---
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- 关系（遵循项目 backref 风格） ---
    user = db.relationship('User', backref=db.backref(
        'ai_tasks', lazy='dynamic', cascade='all, delete-orphan'
    ))
    artwork = db.relationship('Artwork', backref=db.backref(
        'ai_tasks', lazy='dynamic'
    ))

    # ------------------------------------------------------------
    # 序列化（安全: 只返回任务自身字段，不含认证秘密）
    # ------------------------------------------------------------
    def to_dict(self):
        """转换为字典（用于 API 响应）"""
        return {
            'id': self.id,
            'provider': self.provider,
            'model': self.model,
            'task_type': self.task_type,
            'prompt': self.prompt,
            'input_url': self.input_url,
            'external_task_id': self.external_task_id,
            'status': self.status,
            'result_url': self.result_url,
            'artwork_id': self.artwork_id,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f'<AITask {self.id} {self.task_type} {self.status}>'
