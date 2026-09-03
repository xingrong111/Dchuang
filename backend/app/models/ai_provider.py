# ============================================================
# 智绘锡承 - AI Provider 配置模型（阶段16-B）
# 位置: backend/app/models/ai_provider.py
#
# 用途: 运营侧管理 AI Provider（启用/停用开关 + 成本配置），
#   为后续"关闭某模型调用"/成本策略提供数据基础。
#   运行时 factory 校验 enabled 为后续阶段接入（当前仅管理数据）。
# ============================================================
from datetime import datetime

from app.extensions import db


class AIProviderConfig(db.Model):
    """AI Provider 运营配置（阶段16-B）"""
    __tablename__ = 'ai_providers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 逻辑名（hunyuan/glm/mock），唯一；与 AITask.provider 对齐
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    # 能力类型: '3d'（3D 生成）| 'analysis'（风格分析）
    provider_type = db.Column(db.String(10), nullable=False)
    # 启用开关（未来 factory 校验；当前为管理记录）
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    # 成本配置 JSON（如 {"generate3d": 20, "analyze_style": 5}）
    cost_config = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """序列化（管理列表用，不含敏感）"""
        return {
            'id': self.id,
            'name': self.name,
            'enabled': self.enabled,
            'type': self.provider_type,
        }

    def to_detail(self):
        data = self.to_dict()
        data.update({
            'cost_config': self.cost_config or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        })
        return data

    def __repr__(self):
        return f'<AIProviderConfig {self.name} enabled={self.enabled}>'
