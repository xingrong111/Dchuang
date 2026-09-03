# ============================================================
# 智绘锡承 - 平台积分 Service（阶段15-B）
# 位置: backend/app/services/credit.py
#
# 职责:
#   - 账户初始化（注册赠送 100）
#   - 余额查询 / 消费（负向）/ 充值退款（正向）
#   - 事务内更新余额 + 记录不可变流水
#   - 幂等保护: consume 以 reference_id 为键（同类型同引用不重复扣费）；
#              退款同 reference 不重复退
# ============================================================
from app.extensions import db
from sqlalchemy.exc import OperationalError

from app.models.ai_provider import AIProviderConfig
from app.models.credit import (
    CreditAccount,
    CreditTransaction,
    CREDIT_TYPE_RECHARGE,
    CREDIT_TYPE_REFUND,
    DEFAULT_REGISTER_CREDITS,
)
from app.utils.exceptions import CreditInsufficientError


class CreditService:
    """平台积分服务（阶段15-B/16-C）"""

    # ------------------------------------------------------------
    # 动态 AI 成本（阶段16-C）
    # ------------------------------------------------------------
    @staticmethod
    def get_ai_cost(provider, task_type):
        """查询 AI 调用成本（DB AIProviderConfig.cost_config 优先于 config 默认）

        Args:
            provider: provider 名（hunyuan/glm/mock）
            task_type: 'generate_3d' | 'analyze_style'（对应 cost_config 键）

        Returns:
            int: 成本（积分）

        优先级:
            1. AIProviderConfig.cost_config[task_type]（若为正整数）
            2. config.py AI_COST_3D_GENERATE / AI_COST_STYLE_ANALYZE（默认 20/5）
        """
        # 1) DB 运营配置（后台可调，新任务即时生效）
        #    兼容性: ai_providers 表不存在（旧库未跑 16-B migration）/查询异常
        #    → 回退默认成本，不阻断调用（与 factory enabled 治理口径一致）
        try:
            config = AIProviderConfig.query.filter_by(name=provider).first()
        except OperationalError:
            config = None
        if config is not None and isinstance(config.cost_config, dict):
            value = config.cost_config.get(task_type)
            if isinstance(value, int) and value > 0:
                return value

        # 2) 默认配置
        from flask import current_app

        if task_type == 'generate_3d':
            return current_app.config.get('AI_COST_3D_GENERATE', 20)
        return current_app.config.get('AI_COST_STYLE_ANALYZE', 5)

    # ------------------------------------------------------------
    # 账户初始化
    # ------------------------------------------------------------
    @staticmethod
    def init_account(user_id, initial=DEFAULT_REGISTER_CREDITS):
        """注册时初始化账户（幂等: 已有账户则跳过）并赠送初始积分

        产生一条 RECHARGE 流水（账本完整可审计）
        """
        account = CreditAccount.query.filter_by(user_id=user_id).first()
        if account is not None:
            return account

        account = CreditAccount(user_id=user_id, balance=0)
        db.session.add(account)
        db.session.flush()

        tx = CreditTransaction(
            user_id=user_id,
            amount=initial,
            type=CREDIT_TYPE_RECHARGE,
            description=f'注册赠送初始积分 {initial}',
        )
        db.session.add(tx)
        account.balance += initial
        db.session.commit()
        return account

    # ------------------------------------------------------------
    # 余额
    # ------------------------------------------------------------
    @staticmethod
    def get_balance(user_id):
        """查询用户当前余额（无账户返回 0）"""
        account = CreditAccount.query.filter_by(user_id=user_id).first()
        return account.balance if account else 0

    def _get_or_create_account(self, user_id):
        """获取或创建账户（返回余额 0 的新账户）"""
        account = CreditAccount.query.filter_by(user_id=user_id).first()
        if account is None:
            account = CreditAccount(user_id=user_id, balance=0)
            db.session.add(account)
            db.session.flush()
        return account

    # ------------------------------------------------------------
    # 消费（负向）
    # ------------------------------------------------------------
    def consume(self, user_id, amount, transaction_type, reference_id=None, description=None):
        """消费积分（余额不足抛 CreditInsufficientError）

        幂等: 当提供 reference_id 且该用户同 type+reference 已有消费流水 →
        直接返回当前余额（不重复扣费；配合 AI 任务去重防重复扣）

        Args:
            amount: 正整数（消费额）
            transaction_type: CREDIT_TYPE_*（AI_GENERATE_3D 等）

        Returns:
            int: 消费后余额

        Raises:
            CreditInsufficientError: 余额不足（402）
        """
        if amount <= 0:
            raise ValueError('消费金额必须为正数')

        # 幂等: 同类型同引用已消费 → 不重复扣
        if reference_id is not None:
            existed = (CreditTransaction.query
                       .filter_by(user_id=user_id, type=transaction_type,
                                  reference_id=reference_id)
                       .filter(CreditTransaction.amount < 0)
                       .first())
            if existed is not None:
                return self.get_balance(user_id)

        # 行级锁防并发超扣（MySQL 生效；SQLite 忽略）
        account = (CreditAccount.query
                   .filter_by(user_id=user_id)
                   .with_for_update()
                   .first())
        if account is None or account.balance < amount:
            raise CreditInsufficientError(
                f'积分不足（当前 {account.balance if account else 0}，需 {amount}）'
            )

        account.balance -= amount
        tx = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            type=transaction_type,
            description=description or transaction_type,
            reference_id=reference_id,
        )
        db.session.add(tx)
        db.session.commit()
        return account.balance

    # ------------------------------------------------------------
    # 充值 / 退款（正向）
    # ------------------------------------------------------------
    def recharge(self, user_id, amount, transaction_type=CREDIT_TYPE_RECHARGE,
                 reference_id=None, description=None):
        """充值或退款（正向入账）

        退款幂等: reference_id + REFUND 已有 → 跳过（防重复退款）
        """
        if amount <= 0:
            raise ValueError('充值金额必须为正数')

        if transaction_type == CREDIT_TYPE_REFUND and reference_id is not None:
            existed = (CreditTransaction.query
                       .filter_by(user_id=user_id, type=CREDIT_TYPE_REFUND,
                                  reference_id=reference_id)
                       .filter(CreditTransaction.amount > 0)
                       .first())
            if existed is not None:
                return self.get_balance(user_id)

        account = self._get_or_create_account(user_id)
        account.balance += amount
        tx = CreditTransaction(
            user_id=user_id,
            amount=amount,
            type=transaction_type,
            description=description or transaction_type,
            reference_id=reference_id,
        )
        db.session.add(tx)
        db.session.commit()
        return account.balance
