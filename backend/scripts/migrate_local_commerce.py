"""Back up a local SQLite database before applying the additive commerce migration."""
from datetime import datetime
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db
from flask_migrate import upgrade
app=create_app('development')
with app.app_context():
    db.engine.echo=False
    if db.engine.url.get_backend_name()!='sqlite':
        raise SystemExit('This helper only migrates local SQLite. Use the deployment backup procedure for other databases.')
    source=Path(db.engine.url.database).resolve()
    if not source.is_file():
        raise SystemExit('Existing local database missing; migration cancelled.')
    with sqlite3.connect(source) as connection:
        revision=connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]
        if revision=='ad1020260003':
            print('Commerce migration already applied.');sys.exit(0)
        before={name:connection.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ['users','products','orders']}
        folder=Path(__file__).resolve().parents[1]/'backups';folder.mkdir(exist_ok=True)
        backup=folder/('before-commerce-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.sqlite3')
        with sqlite3.connect(backup) as destination:
            connection.backup(destination)
    upgrade(directory=str(Path(__file__).resolve().parents[1]/'migrations'))
    with sqlite3.connect(source) as connection:
        after={name:connection.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in before}
        assert before==after,'Existing record counts changed'
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='ad1020260003'
    print('Local database backed up and migrated; existing user, product and order counts preserved.')
