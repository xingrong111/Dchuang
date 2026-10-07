"""仅用于本机自动验收：独立数据库/上传目录，不触碰已有开发数据。"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=18000)
parser.add_argument('--runtime', default=str(ROOT / '.acceptance'))
args = parser.parse_args()
runtime = Path(args.runtime).resolve()
runtime.mkdir(parents=True, exist_ok=True)
run = Path(tempfile.mkdtemp(prefix='run-', dir=runtime))
os.environ['TEST_DATABASE_URL'] = 'sqlite:///' + (run / 'acceptance.db').as_posix()
from app import create_app
from app.extensions import db
from app.models.user import User, UserProfile
from app.models.shop import Product
from app.models.artwork import Artwork
from app.services.credit import CreditService
from flask_migrate import upgrade

app = create_app('testing')
app.static_folder = str(run / 'static')
app.config.update(UPLOAD_FOLDER=str(run / 'static/uploads'),
                  AI_PROVIDER='mock', AI_GENERATION_PROVIDER='mock', AI_ANALYSIS_PROVIDER='mock',
                  SMTP_HOST='', SMTP_USER='', SMTP_PASSWORD='',
                  BLOCKCHAIN_RPC_URL='', AI_WORKER_ENABLED=False)
with app.app_context():
    upgrade(directory=str(ROOT / 'backend/migrations'))
    password = secrets.token_urlsafe(20)
    user = User('验收管理员', 'acceptance@example.invalid', password)
    user.profile = UserProfile()
    db.session.add(user)
    db.session.flush()
    CreditService.init_account(user.id)
    app.config['ADMIN_USER_IDS'] = str(user.id)
    image_dir = Path(app.config['UPLOAD_FOLDER']) / 'images'
    image_dir.mkdir(parents=True)
    source = ROOT / 'operations/images/museum/01_ounian.jpg'
    if not source.is_file():
        source = next((ROOT / 'operations/images/museum').glob('*.jpg'))
    shutil.copyfile(source, image_dir / 'fixture.jpg')
    image = '/api/static/uploads/images/fixture.jpg'
    for i in range(1, 4):
        db.session.add(Product(name=f'验收泥人{i}', category='clay', price_cents=3500*i,
                               stock=20, active=True, image=image, description='自动验收使用的临时商品'))
    for public in [True, False]:
        db.session.add(Artwork(user_id=user.id, title='验收公开作品' if public else '验收私有作品',
                               description='临时验收数据', tags=['惠山泥人'], thumbnail=image,
                               is_public=public))
    db.session.commit()
(runtime / 'fixture.json').write_text(json.dumps({'email': 'acceptance@example.invalid', 'password': password,
    'runtime': str(run), 'api': f'http://127.0.0.1:{args.port}'}, ensure_ascii=False), encoding='utf-8')
print('独立验收环境就绪；仅监听 127.0.0.1；不调用外部云服务。', flush=True)
app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)
