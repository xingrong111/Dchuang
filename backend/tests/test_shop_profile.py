import pytest
from app import create_app
from app.extensions import db
from app.models.shop import Product, Order


@pytest.fixture
def setup():
    app = create_app('testing')
    app.config.update(AI_PROVIDER='mock', AI_GENERATION_PROVIDER='', AI_ANALYSIS_PROVIDER='')
    with app.app_context():
        db.create_all()
        db.session.add(Product(id=1, name='泥人', category='clay', price_cents=9900, stock=5))
        db.session.add(Product(id=2, name='售罄', category='clay', price_cents=100, stock=0))
        db.session.commit()
    client = app.test_client()
    def account(email, name):
        client.post('/auth/register', json={'email': email, 'username': name, 'password': 'password123'})
        token = client.post('/auth/login', json={'email': email, 'password': 'password123'}).json['data']['token']
        return {'Authorization': 'Bearer ' + token}
    headers = account('buyer@example.com', 'buyer')
    other = account('other@example.com', 'other')
    yield app, client, headers, other
    with app.app_context():
        db.session.remove()
        db.drop_all()


def payload(key='request-key-123', items=None):
    return {'request_key': key, 'receiver': '测试用户', 'phone': '13800000000', 'address': '测试地址',
            'items': items or [{'product_id': 1, 'quantity': 2, 'price': 0.01}]}


def test_price_idempotency_owner_and_cancel(setup):
    app, client, headers, other = setup
    response = client.post('/shop/orders', headers=headers, json=payload())
    assert response.status_code == 200
    order = response.json['data']
    assert order['total'] == 198
    retry = client.post('/shop/orders', headers=headers, json=payload())
    assert retry.json['data']['id'] == order['id']
    assert client.get('/shop/orders', headers=other).json['data'] == []
    assert client.post(f'/shop/orders/{order["id"]}/cancel', headers=other).status_code == 404
    with app.app_context():
        assert db.session.get(Product, 1).stock == 3
        assert Order.query.count() == 1
    assert client.post(f'/shop/orders/{order["id"]}/cancel', headers=headers).status_code == 200
    assert client.post(f'/shop/orders/{order["id"]}/cancel', headers=headers).status_code == 400
    with app.app_context():
        assert db.session.get(Product, 1).stock == 5


def test_order_stock_transaction_rollback(setup):
    app, client, headers, _ = setup
    result = client.post('/shop/orders', headers=headers, json=payload(items=[
        {'product_id': 1, 'quantity': 2}, {'product_id': 2, 'quantity': 1}]))
    assert result.status_code == 400
    with app.app_context():
        assert db.session.get(Product, 1).stock == 5
        assert Order.query.count() == 0


def test_profile_password_and_unique_name(setup):
    _, client, headers, _ = setup
    assert client.put('/user/profile', headers=headers, json={'username': 'other'}).status_code == 400
    response = client.put('/user/profile', headers=headers, json={'username': '新名字', 'bio': '泥人爱好者', 'is_active': False})
    assert response.json['data']['bio'] == '泥人爱好者'
    assert response.json['data']['is_active'] is True
    assert client.put('/user/password', headers=headers, json={'current_password': 'wrong', 'new_password': 'newpassword123'}).status_code == 400
    assert client.put('/user/password', headers=headers, json={'current_password': 'password123', 'new_password': 'newpassword123'}).status_code == 200
    assert client.post('/auth/login', json={'email': 'buyer@example.com', 'password': 'password123'}).status_code == 401
    assert client.post('/auth/login', json={'email': 'buyer@example.com', 'password': 'newpassword123'}).status_code == 200


def test_invalid_quantities_and_cart(setup):
    _, client, headers, _ = setup
    for quantity in [True, -1, 0, 100, '2']:
        assert client.post('/shop/orders', headers=headers, json=payload(items=[{'product_id': 1, 'quantity': quantity}])).status_code == 400
    assert client.post('/shop/cart', headers=headers, json={'product_id': 1, 'quantity': 2}).status_code == 200
    assert client.get('/shop/cart', headers=headers).json['data'][0]['quantity'] == 2
    assert client.delete('/shop/cart/1', headers=headers).status_code == 200
    assert client.get('/shop/cart', headers=headers).json['data'] == []
