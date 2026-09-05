# ============================================================
# 智绘锡承 - AI 任务状态机
# 位置: backend/app/utils/ai_status.py
#
# 状态定义:
#   PENDING  - 任务已创建，等待 Provider 受理
#   RUNNING  - Provider 已受理，执行中
#   SUCCESS  - 执行成功（终态）
#   FAILED   - 执行失败（终态）
#
# 转换规则（白名单）:
#   PENDING → RUNNING | SUCCESS | FAILED
#   RUNNING → RUNNING | SUCCESS | FAILED
#   SUCCESS → （禁止任何转换）
#   FAILED  → （禁止任何转换）
#
# 非法转换必须抛出项目统一风格的异常（ValidationError），不静默修改状态。
# ============================================================
from app.utils.exceptions import ValidationError

# 状态常量
PENDING = 'PENDING'
RUNNING = 'RUNNING'
SUCCESS = 'SUCCESS'
FAILED = 'FAILED'

ALL_STATUSES = {PENDING, RUNNING, SUCCESS, FAILED}

# 允许的状态转换表: {当前状态: {允许的目标状态集合}}
_ALLOWED_TRANSITIONS = {
    PENDING: {RUNNING, SUCCESS, FAILED},
    RUNNING: {RUNNING, SUCCESS, FAILED},
    SUCCESS: set(),   # 终态，禁止任何转换
    FAILED: set(),    # 终态，禁止任何转换
}


def is_valid_status(status):
    """判断是否为合法状态值"""
    return status in ALL_STATUSES


def can_transition(current, new):
    """判断 current → new 是否允许"""
    if current not in _ALLOWED_TRANSITIONS:
        return False
    return new in _ALLOWED_TRANSITIONS[current]


def transition_status(task, new_status):
    """执行状态转换（含校验）

    Args:
        task: AITask 实例（含当前 status）
        new_status: 目标状态（PENDING/RUNNING/SUCCESS/FAILED）

    Raises:
        ValidationError: 目标状态非法或转换不被允许（如 SUCCESS → RUNNING）
    """
    if not is_valid_status(new_status):
        raise ValidationError(f'非法任务状态: {new_status}')

    current = task.status
    if not can_transition(current, new_status):
        raise ValidationError(
            f'非法任务状态转换: {current} → {new_status}'
        )

    task.status = new_status
    return task
