#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智绘锡承 - 数据库启动检查工具（阶段16-D 交付收口）

用途: 部署/启动前只读检查数据库就绪状态，输出 OK / WARN：
  1. Migration 版本（alembic_version 与迁移链 head 一致性）
  2. 核心表是否存在（users / artworks / ai_tasks / credits / admin ...）

用法（在 backend/ 目录下执行）:
    python scripts/check_database.py [config_name]
  config_name 缺省取环境变量 FLASK_CONFIG，再缺省 'default'。
  数据库连接串读取配置（DATABASE_URL / DB_*，与 config.py 一致）。

行为约束:
  - 只读检查：SELECT / inspector，绝不执行 DDL / alembic upgrade / 写库。
  - 退出码: 0 = 全部 OK；1 = 存在 WARN；2 = 连接失败等致命错误。

输出示例:
    [OK]   数据库连接成功 (sqlite:///...)
    [OK]   migration 版本一致: head=f6a7b8c9d0e1
    [WARN] 核心表缺失: ['likes']
"""
import os
import re
import sys

# 输出 UTF-8（Windows 控制台/重定向场景避免 GBK 乱码；失败则忽略）
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:  # noqa: BLE001
    pass

# 允许 `python scripts/check_database.py` 从 backend/ 任意子目录执行
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from sqlalchemy import create_engine, inspect, text  # noqa: E402

# 项目核心表（与 models 对齐；alembic_version 由 migration 自动管理，单独检查）
CORE_TABLES = [
    'users',
    'user_profiles',
    'artworks',
    'artwork_likes',
    'artwork_comments',
    'artwork_collections',
    'ai_tasks',
    'credit_accounts',
    'credit_transactions',
    'admin_logs',
    'ai_providers',
]

_MIGRATIONS_DIR = os.path.join(_BACKEND_DIR, 'migrations', 'versions')

# 每类结果的打印序号（保证稳定输出顺序）
_OK = 'OK'
_WARN = 'WARN'


def _print(kind, message):
    print(f'[{kind:>4}] {message}')


def _load_revision_chain():
    """扫描 migrations/versions 解析 revision / down_revision，返回 (revisions, heads)

    不依赖 alembic 运行时，纯静态解析（可离线检查预期 head）。
    """
    revisions = set()
    children = {}  # down_revision -> [revision]（一个 down 可被多分支引用）
    pattern_rev = re.compile(r"^revision\s*=\s*['\"]([0-9a-f]+)['\"]")
    pattern_down = re.compile(r"^down_revision\s*=\s*['\"]([0-9a-f]+)['\"]")

    if not os.path.isdir(_MIGRATIONS_DIR):
        return revisions, set()

    for filename in sorted(os.listdir(_MIGRATIONS_DIR)):
        if not filename.endswith('.py'):
            continue
        rev = None
        down = None
        with open(os.path.join(_MIGRATIONS_DIR, filename), encoding='utf-8') as fh:
            for line in fh:
                m = pattern_rev.match(line.strip())
                if m:
                    rev = m.group(1)
                d = pattern_down.match(line.strip())
                if d:
                    down = d.group(1)
        if rev:
            revisions.add(rev)
            if down:
                children.setdefault(down, []).append(rev)

    # head = 未被任何其他 revision 引用为 down_revision 的 revision
    referenced = set(children.keys())
    heads = {r for r in revisions if r not in referenced}
    return revisions, heads


def _check_migration(conn, heads):
    """检查 alembic_version 与迁移链 head 一致性"""
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())

    if 'alembic_version' not in tables:
        _print(_WARN, 'migration 未应用: alembic_version 表不存在'
                      '（请先执行 flask db upgrade）')
        return 1

    row = conn.execute(text('SELECT version_num FROM alembic_version')).first()
    current = row[0] if row else None
    if current is None:
        _print(_WARN, 'alembic_version 为空: 数据库尚无任何 migration 记录')
        return 1

    if not heads:
        _print(_WARN, f'无法解析迁移文件预期 head（{_MIGRATIONS_DIR} 为空或格式异常）')
        return 1

    if current in heads:
        _print(_OK, f'migration 版本一致: head={current}')
        return 0

    expected = ','.join(sorted(heads))
    _print(_WARN, f'migration 版本不一致: 当前={current}，预期 head={expected}'
                  '（落后于迁移链，请执行 flask db upgrade）')
    return 1


def _check_core_tables(conn):
    """检查核心表是否存在"""
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    missing = [name for name in CORE_TABLES if name not in tables]

    if missing:
        _print(_WARN, f'核心表缺失: {missing}（请先执行 flask db upgrade 建表）')
        return len(missing)
    _print(_OK, f'核心表齐全（{len(CORE_TABLES)} 张）')
    return 0


def main():
    config_name = (sys.argv[1] if len(sys.argv) > 1
                   else os.getenv('FLASK_CONFIG', 'default'))

    try:
        from config import config as _configs
        cfg = _configs.get(config_name)
        if cfg is None:
            _print(_WARN, f'未知配置环境: {config_name}（可用: {",".join(_configs)}）')
            return 1
        uri = cfg.SQLALCHEMY_DATABASE_URI
    except Exception as exc:  # noqa: BLE001
        _print(_WARN, f'读取配置失败: {exc}')
        return 1

    # 脱敏打印（连接串可能含密码）
    safe_uri = uri
    if '://' in uri and '@' in uri.split('://', 1)[1]:
        scheme, rest = uri.split('://', 1)
        safe_uri = f'{scheme}://***@{rest.split("@", 1)[1]}'

    # 只读连接检查（engine.connect + inspector，不执行任何写操作）
    try:
        engine = create_engine(uri, pool_pre_ping=False)
        with engine.connect() as conn:
            _print(_OK, f'数据库连接成功 ({safe_uri})')
            warn_count = _check_migration(conn, _load_revision_chain()[1])
            warn_count += _check_core_tables(conn)
    except Exception as exc:  # noqa: BLE001
        _print(_WARN, f'数据库连接失败: {exc}')
        return 2

    if warn_count:
        _print(_WARN, f'检查完成: {warn_count} 项异常（请处理后再启动）')
        return 1
    _print(_OK, '检查完成: 全部通过，可启动服务')
    return 0


if __name__ == '__main__':
    sys.exit(main())
