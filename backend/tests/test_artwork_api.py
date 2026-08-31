# ============================================================
# 智绘锡承 - Artwork 作品管理 API 测试（阶段7）
# 覆盖: 模型 / 创建 / 列表 / 详情 / 更新 / 删除 / 回归安全
# ============================================================
import io

import pytest


@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    return app


@pytest.fixture
def db(app):
    """初始化数据库表"""
    from app.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app, db):
    """测试客户端"""
    return app.test_client()


def _register(client, username, email):
    """辅助：注册"""
    resp = client.post('/auth/register', json={
        'username': username,
        'email': email,
        'password': 'password123',
    })
    assert resp.status_code == 200


def _login(client, email):
    """辅助：登录，返回 JWT"""
    resp = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _auth_headers(token):
    return {'Authorization': f'Bearer {token}'}


def _create_payload(**overrides):
    """辅助：构造创建作品请求体"""
    payload = {
        'title': '惠山泥人作品',
        'description': '测试作品描述',
        'model_url': '/api/static/uploads/models/ab12cd34_test.glb',
        'model_format': 'glb',
        'thumbnail': '/api/static/uploads/images/ef56gh78_test.png',
        'tags': ['惠山泥人', '传统'],
        'is_public': True,
    }
    payload.update(overrides)
    return payload


def _save(client, payload=None, token=None, headers=None):
    """辅助：保存作品"""
    return client.post(
        '/workshop/save',
        json=payload or _create_payload(),
        headers=headers or (_auth_headers(token) if token else {}),
    )


class TestArtworkModel:
    """Artwork 模型测试"""

    def test_create_artwork(self, app, db):
        """创建 Artwork + 与 User relationship"""
        from app.models.user import User
        from app.models.artwork import Artwork

        with app.app_context():
            user = User(username='artist', email='artist@e.com', password='pass123')
            db.session.add(user)
            db.session.commit()

            artwork = Artwork(user_id=user.id, title='作品A')
            db.session.add(artwork)
            db.session.commit()

            assert artwork.id is not None
            assert len(artwork.id) == 36  # UUID 格式
            assert artwork.author.username == 'artist'
            assert user.artworks.count() == 1
            assert user.artworks.first().title == '作品A'

    def test_artwork_to_dict_no_sensitive(self, app, db):
        """to_dict 不含 password_hash 等敏感字段，author 只含公开字段"""
        from app.models.user import User
        from app.models.artwork import Artwork

        with app.app_context():
            user = User(username='artist2', email='artist2@e.com', password='pass123')
            db.session.add(user)
            db.session.commit()
            artwork = Artwork(user_id=user.id, title='作品B', tags=['a', 'b'])
            db.session.add(artwork)
            db.session.commit()

            data = artwork.to_dict()
            body = str(data)
            assert 'password_hash' not in body
            assert 'password' not in body
            assert data['author'] == {'id': user.id, 'username': 'artist2', 'avatar': user.avatar}

    def test_artwork_json_fields_serializable(self, app, db):
        """JSON 字段（tags/ai_params/style_analysis）安全序列化"""
        from app.models.user import User
        from app.models.artwork import Artwork

        with app.app_context():
            user = User(username='artist3', email='artist3@e.com', password='pass123')
            db.session.add(user)
            db.session.commit()
            artwork = Artwork(
                user_id=user.id, title='作品C',
                tags=['x'], ai_params={'style': 'traditional'},
                style_analysis={'score': 0.9},
            )
            db.session.add(artwork)
            db.session.commit()

            data = artwork.to_dict(include_details=True)
            assert data['tags'] == ['x']
            assert data['ai_params'] == {'style': 'traditional'}
            assert data['style_analysis'] == {'score': 0.9}


class TestCreate:
    """创建作品"""

    def test_jwt_create_success(self, client):
        """JWT 创建成功"""
        _register(client, 'userone', 'c1@e.com')
        token = _login(client, 'c1@e.com')
        resp = _save(client, token=token)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert data['data']['title'] == '惠山泥人作品'
        assert data['data']['author']['username'] == 'userone'
        assert 'password_hash' not in resp.get_data(as_text=True)

    def test_session_create_success(self, client):
        """Session 创建成功（无 Authorization）"""
        _register(client, 'usertwo', 'c2@e.com')
        _login(client, 'c2@e.com')  # Session Cookie 保存
        resp = _save(client)
        assert resp.status_code == 200
        assert resp.get_json()['data']['author']['username'] == 'usertwo'

    def test_create_no_auth_401(self, client):
        """无认证创建 → 401"""
        resp = _save(client)
        assert resp.status_code == 401
        data = resp.get_json()
        assert data['code'] == 401
        assert data['data'] is None

    def test_create_missing_title_400(self, client):
        """缺少 title → 400"""
        _register(client, 'userthree', 'c3@e.com')
        token = _login(client, 'c3@e.com')
        resp = _save(client, payload={'description': 'no title'}, token=token)
        assert resp.status_code == 400
        assert resp.get_json()['code'] == 400

    def test_create_ignores_client_user_id(self, client, app, db):
        """客户端伪造 user_id 被忽略，作者始终是认证用户"""
        from app.models.artwork import Artwork

        _register(client, 'realowner', 'realowner@e.com')
        token = _login(client, 'realowner@e.com')
        resp = _save(client, payload=_create_payload(user_id='999999'), token=token)
        assert resp.status_code == 200
        artwork_id = resp.get_json()['data']['id']

        with app.app_context():
            artwork = db.session.get(Artwork, artwork_id)
            # 作者是认证用户（realowner），不是伪造的 999999
            assert artwork.user_id != 999999
            assert artwork.author.username == 'realowner'


class TestList:
    """作品列表"""

    def test_list_public_works(self, client):
        """公开作品列表"""
        _register(client, 'userlist1', 'l1@e.com')
        token = _login(client, 'l1@e.com')
        _save(client, token=token)
        _save(client, payload=_create_payload(title='第二件'), token=token)

        resp = client.get('/workshop/works')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert len(data['data']) == 2
        # 按创建时间倒序
        assert data['data'][0]['title'] == '第二件'

    def test_list_pagination(self, client):
        """分页正确"""
        _register(client, 'userlist2', 'l2@e.com')
        token = _login(client, 'l2@e.com')
        for i in range(15):
            _save(client, payload=_create_payload(title=f'作品{i}'), token=token)

        resp = client.get('/workshop/works?page=1&per_page=10')
        data = resp.get_json()
        assert len(data['data']) == 10
        assert data['meta']['pagination']['total'] == 15
        assert data['meta']['pagination']['total_pages'] == 2
        assert data['meta']['pagination']['has_next'] is True

        resp2 = client.get('/workshop/works?page=2&per_page=10')
        assert len(resp2.get_json()['data']) == 5

    def test_list_hides_private(self, client):
        """私有作品不出现在公开列表"""
        _register(client, 'userlist3', 'l3@e.com')
        token = _login(client, 'l3@e.com')
        _save(client, token=token)  # 公开
        _save(client, payload=_create_payload(title='私有', is_public=False), token=token)  # 私有

        resp = client.get('/workshop/works')
        titles = [w['title'] for w in resp.get_json()['data']]
        assert '私有' not in titles
        assert len(titles) == 1


class TestDetail:
    """作品详情"""

    def test_get_existing_artwork(self, client):
        """获取存在作品 → 200"""
        _register(client, 'userdet1', 'd1@e.com')
        token = _login(client, 'd1@e.com')
        art_id = _save(client, token=token).get_json()['data']['id']

        resp = client.get(f'/workshop/works/{art_id}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['data']['id'] == art_id
        assert data['data']['title'] == '惠山泥人作品'

    def test_get_not_found_404(self, client):
        """不存在作品 → 404"""
        resp = client.get('/workshop/works/nonexistent-id')
        assert resp.status_code == 404
        data = resp.get_json()
        assert data['code'] == 404
        assert data['data'] is None

    def test_get_private_artwork_denied(self, client, app):
        """私有作品非作者访问 → 404（不泄露存在性）"""
        _register(client, 'userdet2', 'd2@e.com')
        token = _login(client, 'd2@e.com')
        art_id = _save(client, payload=_create_payload(is_public=False), token=token).get_json()['data']['id']

        # 独立 client（无作者 Session）以非作者身份访问
        anon = app.test_client()
        resp = anon.get(f'/workshop/works/{art_id}')
        assert resp.status_code == 404

    def test_get_private_artwork_by_author(self, client):
        """私有作品作者本人可访问"""
        _register(client, 'userdet3', 'd3@e.com')
        token = _login(client, 'd3@e.com')
        art_id = _save(client, payload=_create_payload(is_public=False), token=token).get_json()['data']['id']

        resp = client.get(f'/workshop/works/{art_id}')
        assert resp.status_code == 200


class TestUpdate:
    """更新作品"""

    def test_author_update_success(self, client):
        """作者更新成功"""
        _register(client, 'userupd1', 'u1@e.com')
        token = _login(client, 'u1@e.com')
        art_id = _save(client, token=token).get_json()['data']['id']

        resp = client.put(f'/workshop/works/{art_id}', json={'title': '更新后的标题'}, headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['data']['title'] == '更新后的标题'

    def test_non_author_update_403(self, client):
        """非作者更新 → 403"""
        _register(client, 'userupda', 'ua@e.com')
        token_a = _login(client, 'ua@e.com')
        art_id = _save(client, token=token_a).get_json()['data']['id']

        _register(client, 'userupdb', 'ub@e.com')
        token_b = _login(client, 'ub@e.com')
        resp = client.put(f'/workshop/works/{art_id}', json={'title': 'hack'}, headers=_auth_headers(token_b))
        assert resp.status_code == 403
        assert resp.get_json()['code'] == 403

    def test_update_no_auth_401(self, client, app):
        """无认证更新 → 401"""
        _register(client, 'userupdc', 'uc@e.com')
        token = _login(client, 'uc@e.com')
        art_id = _save(client, token=token).get_json()['data']['id']

        # 独立 client（无作者 Session）→ 401
        anon = app.test_client()
        resp = anon.put(f'/workshop/works/{art_id}', json={'title': 'x'})
        assert resp.status_code == 401

    def test_update_cannot_change_user_id(self, client, app, db):
        """更新不能修改 user_id（客户端提交被忽略）"""
        from app.models.artwork import Artwork

        _register(client, 'uowner', 'uowner@e.com')
        token = _login(client, 'uowner@e.com')
        art_id = _save(client, token=token).get_json()['data']['id']

        resp = client.put(f'/workshop/works/{art_id}', json={'user_id': 999999, 'title': '正常更新'}, headers=_auth_headers(token))
        assert resp.status_code == 200

        with app.app_context():
            artwork = db.session.get(Artwork, art_id)
            assert artwork.user_id != 999999
            assert artwork.title == '正常更新'

    def test_update_not_found_404(self, client):
        """更新不存在作品 → 404"""
        _register(client, 'userupdd', 'ud@e.com')
        token = _login(client, 'ud@e.com')
        resp = client.put('/workshop/works/nonexistent', json={'title': 'x'}, headers=_auth_headers(token))
        assert resp.status_code == 404


class TestDelete:
    """删除作品"""

    def test_author_delete_success(self, client):
        """作者删除成功"""
        _register(client, 'userdel1', 'x1@e.com')
        token = _login(client, 'x1@e.com')
        art_id = _save(client, token=token).get_json()['data']['id']

        resp = client.delete(f'/workshop/works/{art_id}', headers=_auth_headers(token))
        assert resp.status_code == 200
        assert resp.get_json()['message'] == '作品删除成功'

        # 再查 → 404
        resp2 = client.get(f'/workshop/works/{art_id}')
        assert resp2.status_code == 404

    def test_non_author_delete_403(self, client):
        """非作者删除 → 403"""
        _register(client, 'userdela', 'xa@e.com')
        token_a = _login(client, 'xa@e.com')
        art_id = _save(client, token=token_a).get_json()['data']['id']

        _register(client, 'userdelb', 'xb@e.com')
        token_b = _login(client, 'xb@e.com')
        resp = client.delete(f'/workshop/works/{art_id}', headers=_auth_headers(token_b))
        assert resp.status_code == 403

    def test_delete_no_auth_401(self, client, app):
        """无认证删除 → 401"""
        _register(client, 'userdelc', 'xc@e.com')
        token = _login(client, 'xc@e.com')
        art_id = _save(client, token=token).get_json()['data']['id']

        # 独立 client（无作者 Session）→ 401
        anon = app.test_client()
        resp = anon.delete(f'/workshop/works/{art_id}')
        assert resp.status_code == 401

    def test_delete_not_found_404(self, client):
        """删除不存在作品 → 404"""
        _register(client, 'userdeld', 'xd@e.com')
        token = _login(client, 'xd@e.com')
        resp = client.delete('/workshop/works/nonexistent', headers=_auth_headers(token))
        assert resp.status_code == 404


class TestRegression:
    """回归安全：不影响既有认证/上传"""

    def test_jwt_login_still_works(self, client):
        """JWT 登录不受影响"""
        _register(client, 'userreg1', 'r1@e.com')
        resp = _login(client, 'r1@e.com')
        assert resp
        data = client.post('/auth/login', json={'email': 'r1@e.com', 'password': 'password123'}).get_json()
        assert 'token' in data['data']

    def test_session_avatar_upload_still_works(self, client, app, db):
        """Session 头像上传不受影响"""
        _register(client, 'userreg2', 'r2@e.com')
        _login(client, 'r2@e.com')
        png = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00'
            b'\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\x0d\x0a\x2d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        resp = client.post('/user/upload-avatar', data={'file': (io.BytesIO(png), 'a.png')},
                           content_type='multipart/form-data')
        assert resp.status_code == 200
