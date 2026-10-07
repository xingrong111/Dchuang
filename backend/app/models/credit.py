# ============================================================
# 智绘锡承 - 平台积分账本模型（Credit Ledger）
# 位置: backend/app/models/credit.py
#
# 设计:
#   - CreditAccount: 每用户一行余额（user_id unique）
#   - CreditTransaction: 不可变流水（amount 正=充值/退款，负=消费）
#   - 权威余额 = account.balance（消费/充值时同事务维护，流水只增不改）
#   - reference_id 可关联 AITask.id（幂等扣费依据）
# ============================================================
from datetime import datetime

from app.extensions import db

# 交易类型
CREDIT_TYPE_RECHARGE = 'RECHARGE'            # 充值/赠送
CREDIT_TYPE_AI_GENERATE_3D = 'AI_GENERATE_3D'  # AI 3D 生成消费
CREDIT_TYPE_AI_ANALYZE_STYLE = 'AI_ANALYZE_STYLE'  # AI 风格分析消费
CREDIT_TYPE_REFUND = 'REFUND'                # 退款

# 注册初始赠送积分
DEFAULT_REGISTER_CREDITS = 100


class CreditAccount(db.Model):
    """用户积分账户"""
    __tablename__ = 'credit_accounts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True,
                        nullable=False, index=True)
    balance = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('credit_account', uselist=False))

    def __repr__(self):
        return f'<CreditAccount user={self.user_id} balance={self.balance}>'


class CreditTransaction(db.Model):
    """积分流水（只增不改）"""
    __tablename__ = 'credit_transactions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # 正数=充值/退款；负数=消费
    amount = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(30), nullable=False, index=True)  # CREDIT_TYPE_*
    description = db.Column(db.Text)
    # 可关联 AITask.id（幂等扣费/退款依据）
    reference_id = db.Column(db.String(64), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('ix_credit_tx_user_created', 'user_id', 'created_at'),
    )

    user = db.relationship('User', backref=db.backref('credit_transactions', lazy='dynamic'))

    def to_dict(self):
        """序列化（不含敏感字段）"""
        return {
            'id': self.id,
            'amount': self.amount,
            'type': self.type,
            'description': self.description,
            'reference_id': self.reference_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<CreditTransaction user={self.user_id} amount={self.amount} type={self.type}>'
