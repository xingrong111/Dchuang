"""Print only local table counts and database kind; never credentials."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.extensions import db
from sqlalchemy import inspect, text
app = create_app('development')
with app.app_context():
    print('database:', db.engine.url.drivername, db.engine.url.database)
    for table in inspect(db.engine).get_table_names():
        print(table, db.session.execute(text('SELECT COUNT(*) FROM ' + db.engine.dialect.identifier_preparer.quote(table))).scalar())
