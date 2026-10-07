"""Refresh the local public catalog; --clear-users explicitly erases account data."""
import argparse
import json
import secrets
import sys
from pathlib import Path
from dotenv import set_key
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from app.extensions import db
from app.models.artwork import Artwork
from app.models.shop import Product
from sqlalchemy import delete, select
from flask_migrate import upgrade

def refresh(clear_users=False):
    app = create_app('development')
    with app.app_context():
        # This utility is deliberately restricted to the named workspace database.
        expected = (ROOT / 'backend/dev.db').resolve()
        if db.engine.dialect.name != 'sqlite' or Path(db.engine.url.database).resolve() != expected:
            raise RuntimeError('This utility only operates on backend/dev.db')
        db.engine.echo = False
        upgrade(directory=str(ROOT / 'backend/migrations'))
        users = db.metadata.tables['users']
        previous = db.session.execute(select(db.func.count()).select_from(users)).scalar()
        if clear_users:
            # Children first, in one transaction. No passwords or profiles are backed up.
            names = ['product_reviews', 'product_favorites', 'shipping_addresses',
                     'cart_items', 'orders', 'artwork_collections', 'artwork_comments',
                     'artwork_likes', 'ai_tasks', 'credit_transactions', 'credit_accounts',
                     'admin_logs', 'password_reset_codes', 'user_profiles']
            for name in names:
                db.session.execute(delete(db.metadata.tables[name]))
            db.session.execute(delete(Artwork).where(Artwork.user_id.is_not(None)))
            db.session.execute(delete(users))
        content = json.loads((ROOT / 'frontend/src/content/editorial.json').read_text(encoding='utf-8-sig'))
        for design in content['products']:
            row = Product.query.filter_by(name=design['name']).first()
            if row is None:
                row = Product(name=design['name'])
                db.session.add(row)
            row.description = design['story'] if design['story'].startswith(design['intro']) else design['intro'] + ' ' + design['story']
            row.category = 'stationery' if design['id'] in ('notebook', 'postcards') else 'clay'
            row.price_cents = 0
            row.stock = 0
            row.active = True
            row.image = '/content/' + design['image']
            row.specs = {'display_only': True, 'design_id': design['id'],
                         'model_url': '/' + design['model'], '材质方向': design['material'],
                         '尺寸规划': design['size'], '状态': '原创文创，尚未实物销售'}
        works = json.loads((ROOT / 'frontend/src/content/community-showcase.json').read_text(encoding='utf-8-sig'))
        for item in works:
            row = db.session.get(Artwork, item['id'])
            if row is None:
                row = Artwork(id=item['id'], user_id=None)
                db.session.add(row)
            row.title, row.description = item['title'], item['description']
            row.tags = item['tags']
            row.thumbnail, row.model_url = item['thumbnail'], item['model_url']
            row.is_public, row.allow_download = True, False
        db.session.commit()
        if clear_users:
            # Revoke pre-reset JWTs and cookie sessions before a new account can reuse an ID.
            for key in ('JWT_SECRET_KEY', 'SECRET_KEY'):
                set_key(str(ROOT / 'backend/.env'), key, secrets.token_urlsafe(48))
        print(json.dumps({'removed_accounts': previous if clear_users else 0,
                          'remaining_accounts': db.session.execute(select(db.func.count()).select_from(users)).scalar(),
                          'showcase_works': len(works), 'catalog_designs': len(content['products'])}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--clear-users', action='store_true')
    refresh(parser.parse_args().clear_users)
