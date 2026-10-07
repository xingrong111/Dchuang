from tests.test_shop_profile import setup, payload
from app.extensions import db
from app.models.shop import Order, Product


def test_address_privacy_default_and_delete(setup):
    _, client, owner, other = setup
    body = dict(receiver="收件人", phone="13800000000", address="测试地址")
    first = client.post('/shop/addresses', headers=owner, json=body).json['data']
    assert first['is_default']
    second = client.post('/shop/addresses', headers=owner, json={**body, 'is_default': True}).json['data']
    assert sum(a['is_default'] for a in client.get('/shop/addresses', headers=owner).json['data']) == 1
    assert client.get('/shop/addresses', headers=other).json['data'] == []
    assert client.put('/shop/addresses/'+str(first['id']), headers=other, json=body).status_code == 404
    assert client.delete('/shop/addresses/'+str(second['id']), headers=owner).status_code == 200
    assert client.get('/shop/addresses', headers=owner).json['data'][0]['is_default']


def test_favorite_idempotency_and_isolation(setup):
    _, client, owner, other = setup
    for _ in range(2):
        assert client.put('/shop/favorites/1', headers=owner).status_code == 200
    assert len(client.get('/shop/favorites', headers=owner).json['data']) == 1
    assert client.get('/shop/favorites', headers=other).json['data'] == []
    client.delete('/shop/favorites/1', headers=other)
    assert len(client.get('/shop/favorites', headers=owner).json['data']) == 1
    client.delete('/shop/favorites/1', headers=owner)
    assert client.get('/shop/favorites', headers=owner).json['data'] == []


def test_receive_and_verified_review(setup):
    app, client, owner, other = setup
    order = client.post('/shop/orders', headers=owner, json=payload()).json['data']['id']
    route = '/shop/orders/'+order
    review = dict(product_id=1, rating=4, content='做工符合预期')
    assert client.get(route, headers=other).status_code == 404
    assert client.post(route+'/receive', headers=owner).status_code == 400
    assert client.post(route+'/reviews', headers=owner, json=review).status_code == 400
    with app.app_context():
        db.session.get(Order, order).status = '已发货'
        db.session.commit()
    assert client.post(route+'/receive', headers=other).status_code == 400
    assert client.post(route+'/receive', headers=owner).status_code == 200
    assert client.post(route+'/receive', headers=owner).status_code == 400
    assert client.post(route+'/reviews', headers=other, json=review).status_code == 400
    assert client.post(route+'/reviews', headers=owner, json={**review,'rating':True}).status_code == 400
    assert client.post(route+'/reviews', headers=owner, json=review).status_code == 200
    assert client.post(route+'/reviews', headers=owner, json=review).status_code == 400
    product = client.get('/shop/products/1').json['data']
    assert product['rating'] == 4 and product['reviewCount'] == 1
    assert len(client.get('/shop/products/1/reviews').json['data']) == 1


def test_search_sort_over_full_catalog(setup):
    app, client, _, _ = setup
    with app.app_context():
        db.session.add_all([Product(name='检索'+str(i), category='clay', price_cents=i*100, stock=1) for i in range(3,130)])
        db.session.commit()
    rows = client.get('/shop/products?q=检索129').json['data']
    assert len(rows) == 1 and rows[0]['name'] == '检索129'
    rows = client.get('/shop/products?q=检索&sort=price_desc&per_page=2').json['data']
    assert [p['price'] for p in rows] == [129,128]
    assert client.get('/shop/products?sort=invalid').status_code == 400


def test_shipping_requires_reference_and_rolls_back(setup):
    app, client, owner, other = setup
    from app.models.user import User
    with app.app_context():
        app.config['ADMIN_USER_IDS'] = str(User.query.filter_by(email='buyer@example.com').first().id)
    oid = client.post('/shop/orders', headers=owner, json=payload()).json['data']['id']
    route = '/admin/orders/'+oid
    assert client.put(route, headers=other, json={'status':'待发货'}).status_code == 403
    assert client.put(route, headers=owner, json={'status':'待发货'}).status_code == 200
    assert client.put(route, headers=owner, json={'status':'已发货'}).status_code == 400
    assert client.get('/shop/orders/'+oid, headers=owner).json['data']['status'] == '待发货'
    row = client.put(route, headers=owner, json={'status':'已发货','carrier':'测试物流','tracking_number':'TEST-123'}).json['data']
    assert row['status'] == '已发货' and row['tracking_number'] == 'TEST-123'
