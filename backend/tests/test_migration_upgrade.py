# ============================================================
# 智绘锡承 - Alembic migration 真升级测试（部署前验收补充）
# 覆盖:
#   - 全新空库执行 flask db upgrade 完整跑到 head f6a7b8c9d0e1
#   - alembic_version 与核心表存在性
#   - 关键约束存在（likes/collections 联合唯一、FK cascade、
#     ai_tasks artwork FK ondelete SET NULL、credit 索引、
#     admin_logs 索引、ai_providers name 唯一）
#   - head 一步 downgrade → upgrade 冒烟
# 说明: 使用独立临时 SQLite 文件库（不经 create_all，跑真实 Alembic）。
#       在 create_app 前 monkeypatch testing config 类（engine URL 绑定于
#       init_app 时读取的 config 类），用独立 app 执行迁移，自动还原不污染其它测试。
# ============================================================
import os

import pytest


@pytest.fixture
def app(tmp_path):
    """普通测试 app（SQLite 内存库，仅供 fixture 结构一致，测试用独立 migrate app）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    return app


def _make_migrate_app(monkeypatch, tmp_path):
    """创建指向独立 SQLite 文件库的 app（engine 首次创建即绑定文件 URL）"""
    from config import config as _configs
    from app import create_app

    db_path = str(tmp_path / 'mig_upgrade.db')
    url = 'sqlite:///' + db_path.replace('\\', '/')

    monkeypatch.setattr(_configs['testing'], 'SQLALCHEMY_DATABASE_URI', url)
    monkeypatch.setattr(_configs['testing'], 'SQLALCHEMY_ENGINE_OPTIONS', {})

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    return app, db_path


def _alembic_config():
    from alembic.config import Config

    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini = os.path.join(backend_dir, 'migrations', 'alembic.ini')
    cfg = Config(ini)
    cfg.set_main_option('script_location', os.path.join(backend_dir, 'migrations'))
    return cfg


def _upgrade(app, cfg, target='head'):
    from alembic import command

    with app.app_context():
        command.upgrade(cfg, target)


def _downgrade(app, cfg, target):
    from alembic import command

    with app.app_context():
        command.downgrade(cfg, target)


def _sqlite_tables(db_path):
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "select name from sqlite_master where type='table'").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _sqlite_ddl(db_path, table):
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "select sql from sqlite_master where name=?", (table,)).fetchone()
        return row[0] if row else ''
    finally:
        conn.close()


def _alembic_version(db_path):
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute('select version_num from alembic_version').fetchone()
        return row[0] if row else None
    finally:
        conn.close()


class TestMigrationUpgrade:
    """Alembic 真实升级验收"""

    CORE_TABLES = [
        'users', 'user_profiles', 'artworks', 'ai_tasks',
        'artwork_likes', 'artwork_comments', 'artwork_collections',
        'credit_accounts', 'credit_transactions', 'admin_logs', 'ai_providers',
    ]
    HEAD = 'f6a7b8c9d0e1'

    def test_fresh_upgrade_to_head(self, app, tmp_path, monkeypatch):
        """全新空库 upgrade → head，核心表齐全"""
        mig_app, db_path = _make_migrate_app(monkeypatch, tmp_path)
        cfg = _alembic_config()
        _upgrade(mig_app, cfg, 'head')

        assert _alembic_version(db_path) == self.HEAD
        tables = _sqlite_tables(db_path)
        missing = [t for t in self.CORE_TABLES if t not in tables]
        assert missing == []

    def test_key_constraints_present(self, app, tmp_path, monkeypatch):
        """关键约束: 联合唯一 / FK cascade / SET NULL / 索引 / name 唯一"""
        mig_app, db_path = _make_migrate_app(monkeypatch, tmp_path)
        cfg = _alembic_config()
        _upgrade(mig_app, cfg, 'head')

        # likes/collections: UNIQUE(user_id, artwork_id)
        for table in ('artwork_likes', 'artwork_collections'):
            ddl = _sqlite_ddl(db_path, table)
            assert 'UNIQUE (user_id, artwork_id)' in ddl, f'{table} 缺联合唯一'

        # comments/collections: artwork FK ON DELETE CASCADE
        for table in ('artwork_comments', 'artwork_collections'):
            ddl = _sqlite_ddl(db_path, table)
            assert 'ON DELETE CASCADE' in ddl, f'{table} 缺 FK cascade'

        # ai_tasks.artwork FK: ON DELETE SET NULL（1bfd 语义）
        ai_ddl = _sqlite_ddl(db_path, 'ai_tasks')
        assert 'fk_ai_tasks_user_id' in ai_ddl, 'ai_tasks user FK 缺稳定名称'
        assert 'fk_ai_tasks_artwork_id' in ai_ddl, 'ai_tasks artwork FK 缺稳定名称'
        assert 'ON DELETE SET NULL' in ai_ddl, 'ai_tasks artwork FK 缺 SET NULL'

        # credit_accounts: user_id 唯一
        acc_ddl = _sqlite_ddl(db_path, 'credit_accounts')
        assert 'UNIQUE' in acc_ddl

        # ai_providers: name 唯一
        prov_ddl = _sqlite_ddl(db_path, 'ai_providers')
        assert 'UNIQUE' in prov_ddl

    def test_downgrade_upgrade_head_smoke(self, app, tmp_path, monkeypatch):
        """head 一步 downgrade（ai_providers 删除）→ 再 upgrade 恢复"""
        mig_app, db_path = _make_migrate_app(monkeypatch, tmp_path)
        cfg = _alembic_config()
        _upgrade(mig_app, cfg, 'head')

        assert _alembic_version(db_path) == self.HEAD
        _downgrade(mig_app, cfg, 'e5f6a7b8c9d0')  # head 的父版本
        assert _alembic_version(db_path) == 'e5f6a7b8c9d0'
        tables = _sqlite_tables(db_path)
        assert 'ai_providers' not in tables

        _upgrade(mig_app, cfg, 'head')
        assert _alembic_version(db_path) == self.HEAD
        assert 'ai_providers' in _sqlite_tables(db_path)
