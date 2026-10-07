import json, os, re, sqlite3, sys
from datetime import datetime
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'backend'));os.environ['AI_WORKER_ENABLED']='false'
from app import create_app
from app.extensions import db
from app.models.artwork import Artwork
from app.models.user import User
app=create_app('development')
with app.app_context():
    db.engine.echo=False
    matches=[]
    for artwork in Artwork.query.filter_by(is_public=True).all():
        user=db.session.get(User,artwork.user_id)
        if user and re.fullmatch(r'e2e[0-9a-f]{8}',user.username) and artwork.title=='联调测试作品' and artwork.description=='端到端联调创建':
            matches.append(artwork)
        elif user and user.username=='full435461ae' and (artwork.id,artwork.title) in {
            ('673c2d83-dbeb-4d27-91c5-50145e1d78d0','惠山泥人测试'),
            ('c29fa9dd-96c4-4776-9032-bc5c713bf06e','全链路探测'),
        }:
            matches.append(artwork)
    folder=root/'operations/deliverables/content-backups';folder.mkdir(parents=True,exist_ok=True)
    database=Path(db.engine.url.database).resolve()
    if not database.is_relative_to(root):raise RuntimeError('Database outside workspace')
    if matches:
        backup=folder/('before-public-cleanup-'+datetime.now().strftime('%Y%m%d%H%M%S')+'.db')
        with sqlite3.connect(str(database)) as source, sqlite3.connect(str(backup)) as destination:source.backup(destination)
        record=[{'id':a.id,'is_public':a.is_public} for a in matches]
        for artwork in matches:artwork.is_public=False
        db.session.commit()
        (folder/('hidden-fixtures-'+datetime.now().strftime('%Y%m%d%H%M%S')+'.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({'hidden_automated_records':len(matches),'remaining_public_artworks':Artwork.query.filter_by(is_public=True).count()}))
