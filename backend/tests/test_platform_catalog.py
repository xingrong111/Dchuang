"""Public content remains searchable without any registered accounts."""
import pytest
from app import create_app
from app.extensions import db
from app.models.artwork import Artwork
from app.models.shop import Product

@pytest.fixture
def client():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        db.session.add(Artwork(id='platform-child', user_id=None, title='春日小福',
                               description='人物搭配', tags=['惠山泥人'], is_public=True))
        db.session.add(Product(name='泥韵手账', category='stationery', price_cents=0,
                               stock=50, active=True, specs={'display_only': True}))
        db.session.commit()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_platform_work_search_and_detail_without_accounts(client):
    for route in ['/workshop/works?q=春日', '/workshop/works?category=惠山泥人']:
        response = client.get(route)
        assert response.status_code == 200
        rows = response.json['data']
        assert len(rows) == 1
        assert rows[0]['author']['username'] == '平台创作精选'
        assert rows[0]['author']['id'] is None
        assert not rows[0]['current_user_status']['is_author']
    assert client.get('/workshop/works/platform-child').status_code == 200

def test_design_cannot_be_ordered_even_with_positive_stock(client):
    client.post('/auth/register', json={'username':'catalogreader', 'email':'catalog@example.com', 'password':'safe-password-123'})
    token = client.post('/auth/login', json={'email':'catalog@example.com', 'password':'safe-password-123'}).json['data']['token']
    headers = {'Authorization': 'Bearer ' + token}
    pid = client.get('/shop/products?q=手账').json['data'][0]['id']
    assert client.post('/shop/cart', headers=headers, json={'product_id':pid, 'quantity':1}).status_code == 400
    response = client.post('/shop/orders', headers=headers, json={'request_key':'catalog-request', 'receiver':'收件人',
                           'phone':'13800138000','address':'本地地址', 'items':[{'product_id':pid,'quantity':1}]})
    assert response.status_code == 400
    assert '设计展示' in response.json['message']


