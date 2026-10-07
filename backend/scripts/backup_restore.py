"""Offline portable DB + upload backup. Restore only into an empty migrated database."""
import argparse
import base64
from datetime import datetime, date
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
import sqlalchemy as sa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db


def encode(value):
    if isinstance(value, (datetime, date)):
        return {'_date': value.isoformat()}
    if isinstance(value, bytes):
        return {'_bytes': base64.b64encode(value).decode()}
    raise TypeError(f'不支持的备份类型 {type(value).__name__}')


def backup(destination):
    from flask import current_app
    root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    tables = []
    for table in db.metadata.sorted_tables:
        # Password-reset challenges are temporary and must not be revived during recovery.
        records = [] if table.name == 'password_reset_codes' else [dict(row) for row in db.session.execute(sa.select(table)).mappings()]
        tables.append({'name': table.name, 'rows': records})
    version = db.session.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one()
    payload = json.dumps({'format': 1, 'revision': version, 'tables': tables}, ensure_ascii=False, default=encode).encode()
    with Path(destination).open('xb') as file, zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('database.json', payload)
        hashes = {'database.json': hashlib.sha256(payload).hexdigest()}
        if root.exists():
            for path in root.rglob('*'):
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError('上传目录存在符号链接或目录逃逸，备份停止')
                if path.is_file():
                    name = 'uploads/' + path.relative_to(root).as_posix()
                    data = path.read_bytes()
                    archive.writestr(name, data)
                    hashes[name] = hashlib.sha256(data).hexdigest()
        archive.writestr('checksums.json', json.dumps(hashes))
    return sum(len(table['rows']) for table in tables)


def restore(source):
    from flask import current_app
    root = Path(current_app.config['UPLOAD_FOLDER']).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError('仅可恢复到空上传目录')
    for table in db.metadata.sorted_tables:
        if db.session.execute(sa.select(sa.func.count()).select_from(table)).scalar():
            raise ValueError('仅可恢复到空数据库，请使用新的恢复数据库')
    with zipfile.ZipFile(source) as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError('备份包含重复条目')
        hashes = json.loads(archive.read('checksums.json'))
        if set(archive.namelist()) != set(hashes) | {'checksums.json'}:
            raise ValueError('备份清单不一致')
        contents = {}
        for name, digest in hashes.items():
            if name != 'database.json' and not name.startswith('uploads/'):
                raise ValueError('备份包含未知文件')
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('备份校验失败')
            if name.startswith('uploads/'):
                target = (root / name[len('uploads/'):]).resolve()
                if not target.is_relative_to(root) or target == root:
                    raise ValueError('备份路径非法')
            contents[name] = data
        document = json.loads(contents['database.json'])
        revision = db.session.execute(sa.text('SELECT version_num FROM alembic_version')).scalar_one()
        if document.get('format') != 1 or document.get('revision') != revision:
            raise ValueError('备份格式或数据库迁移版本不一致')
        if {item['name'] for item in document['tables']} != set(db.metadata.tables):
            raise ValueError('备份表结构不匹配')
        by_name = {item['name']: item['rows'] for item in document['tables']}
        created = []
        try:
            for table in db.metadata.sorted_tables:
                rows = by_name[table.name]
                for row in rows:
                    for key, value in row.items():
                        if isinstance(table.c[key].type, sa.DateTime) and isinstance(value, dict):
                            row[key] = datetime.fromisoformat(value['_date'])
                if rows:
                    db.session.execute(table.insert(), rows)
            # Write uploads before commit; a failure rolls back the database.
            for name, data in contents.items():
                if name.startswith('uploads/'):
                    target = (root / name[len('uploads/'):]).resolve()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    created.append(target)
            db.session.commit()
        except Exception:
            db.session.rollback()
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return sum(len(rows) for rows in by_name.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['backup', 'restore'])
    parser.add_argument('file')
    parser.add_argument('--offline', action='store_true', help='确认已停止 API/Worker/模型文件写入')
    args = parser.parse_args()
    if not args.offline:
        parser.error('必须先停止写入，再传入 --offline')
    app = create_app(os.getenv('FLASK_CONFIG', 'production'))
    with app.app_context():
        count = (backup if args.command == 'backup' else restore)(args.file)
    print(f'{args.command} 完成：{count} 条记录；备份包含账户与订单个人信息，请限制文件访问权限')


if __name__ == '__main__':
    main()
