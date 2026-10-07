"""Community pagination, real interactions, validation and certificate regression."""
import pytest
from tests.test_artwork_api import app, db, client, _register, _login, _auth_headers


def setup_works(client):
    _register(client, 'creator', 'creator@example.com')
    headers = _auth_headers(_login(client, 'creator@example.com'))
    ids = []
    for i in range(15):
        response = client.post('/workshop/save', headers=headers, json={
            'title': f'作品{i}', 'tags': ['传统', '惠山泥人'], 'is_public': i != 14})
        assert response.status_code == 200
        ids.append(response.json['data']['id'])
    return headers, ids


def test_global_filters_sort_and_interactions(client):
    headers, ids = setup_works(client)
    client.post(f'/workshop/works/{ids[0]}/like', headers=headers)
    client.post(f'/workshop/works/{ids[0]}/collect', headers=headers)
    client.post(f'/workshop/works/{ids[1]}/comments', headers=headers, json={'content': '喜欢'})
    response = client.get('/workshop/works?sort=popular&per_page=1', headers=headers)
    assert response.json['data'][0]['id'] == ids[0]
    assert response.json['data'][0]['current_user_status']['liked'] is True
    assert response.json['data'][0]['current_user_status']['collected'] is True
    assert response.json['meta']['pagination']['total'] == 14
    assert client.get('/workshop/works?sort=comments&per_page=1').json['data'][0]['id'] == ids[1]
    assert client.get('/workshop/works?q=作品0&category=惠山泥人').json['data'][0]['id'] == ids[0]
    assert client.get('/workshop/works?category=泥人').json['data'] == []
    assert client.get('/workshop/works?q=%25').json['data'] == []
    assert client.get('/workshop/works?q=creator').json['meta']['pagination']['total'] == 14
    assert client.get('/user/statistics', headers=headers).json['data'] == {'works': 15, 'collections': 1, 'likes': 1}
    assert client.get('/user/works?sort=likes&per_page=1', headers=headers).json['data'][0]['like_count'] == 1
    private = client.get('/user/works?visibility=private', headers=headers).json['data']
    assert len(private) == 1 and private[0]['id'] == ids[14]


@pytest.mark.parametrize('field,value', [('title', 12), ('tags', '泥人'), ('tags', [None]),
    ('is_public', 'false'), ('allow_download', 1), ('model_size', -1),
    ('model_format', 'exe'), ('ai_params', []), ('thumbnail', 42)])
def test_invalid_create_and_partial_update(client, field, value):
    headers, ids = setup_works(client)
    assert client.post('/workshop/save', headers=headers, json={'title': '新作品', field: value}).status_code == 400
    assert client.put(f'/workshop/works/{ids[0]}', headers=headers, json={field: value}).status_code == 400


def test_changed_content_invalidates_certificate(app, db, client):
    from app.models.artwork import Artwork
    headers, ids = setup_works(client)
    with app.app_context():
        work = db.session.get(Artwork, ids[0])
        work.is_certified = True
        work.blockchain_hash = 'digest'
        work.blockchain_tx_id = 'transaction'
        db.session.commit()
    url = f'/workshop/works/{ids[0]}'
    assert client.put(url, headers=headers, json={'is_public': False}).json['data']['is_certified'] is True
    response = client.put(url, headers=headers, json={'description': '新的内容'})
    assert response.status_code == 200
    assert response.json['data']['is_certified'] is False
    assert response.json['data']['blockchain_tx_id'] is None
