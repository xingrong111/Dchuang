# ============================================================
# 智绘锡承 - Artwork 收藏系统测试（阶段14-D）
# 覆盖: 收藏/重复幂等/取消幂等/401/私有权限/用户隔离/
#       collect_count 统计/current_user_status.collected/删除级联
# ============================================================
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
    resp = client.post('/auth/register', json={
        'username': username, 'email': email, 'password': 'password123',
    })
    assert resp.status_code == 200


def _login(client, email):
    resp = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


def _save_artwork(client, token, is_public=True, title='作品'):
    resp = client.post('/workshop/save', json={'title': title, 'is_public': is_public},
                       headers=_auth(token))
    assert resp.status_code == 200
    return resp.get_json()['data']['id']


class TestCollectionModel:
    """Collection 模型约束"""

    def test_unique_user_artwork(self, app, db):
        """同一 (user, artwork) 不能重复插入（唯一约束）"""
        from sqlalchemy.exc import IntegrityError

        from app.extensions import db as flask_db
        from app.models.artwork import Artwork
        from app.models.collection import Collection
        from app.models.user import User

        with app.app_context():
            user = User(username='colu1', email='colu1@e.com', password='pass123')
            flask_db.session.add(user)
            flask_db.session.commit()
            artwork = Artwork(user_id=user.id, title='C')
            flask_db.session.add(artwork)
            flask_db.session.commit()

            flask_db.session.add(Collection(user_id=user.id, artwork_id=artwork.id))
            flask_db.session.commit()
            flask_db.session.add(Collection(user_id=user.id, artwork_id=artwork.id))
            with pytest.raises(IntegrityError):
                flask_db.session.commit()
            flask_db.session.rollback()

    def test_artwork_delete_cascades_collections(self, app, db):
        """删除 Artwork → 其收藏级联删除"""
        from app.extensions import db as flask_db
        from app.models.artwork import Artwork
        from app.models.collection import Collection
        from app.models.user import User

        with app.app_context():
            u1 = User(username='colu2', email='colu2@e.com', password='pass123')
            u2 = User(username='colu3', email='colu3@e.com', password='pass123')
            flask_db.session.add_all([u1, u2])
            flask_db.session.commit()
            artwork = Artwork(user_id=u1.id, title='删除级联收藏')
            flask_db.session.add(artwork)
            flask_db.session.commit()
            flask_db.session.add_all([
                Collection(user_id=u1.id, artwork_id=artwork.id),
                Collection(user_id=u2.id, artwork_id=artwork.id),
            ])
            flask_db.session.commit()
            assert Collection.query.count() == 2

            flask_db.session.delete(artwork)
            flask_db.session.commit()
            assert Collection.query.count() == 0  # 级联删除


class TestCollectionAPI:
    """POST/DELETE /workshop/works/<id>/collect"""

    def _setup(self, client):
        _register(client, 'cola1', 'cola1@e.com')
        return _login(client, 'cola1@e.com')

    def test_collect_success(self, client):
        """收藏成功 → collected=true + collect_count=1"""
        token = self._setup(client)
        art_id = _save_artwork(client, token)

        resp = client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token))
        assert resp.status_code == 200
        d = resp.get_json()['data']
        assert d['collected'] is True
        assert d['collect_count'] == 1

    def test_collect_idempotent(self, client):
        """重复收藏幂等 → collect_count 仍 1"""
        token = self._setup(client)
        art_id = _save_artwork(client, token)

        client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token))
        resp2 = client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token))
        assert resp2.status_code == 200
        assert resp2.get_json()['data']['collect_count'] == 1

    def test_uncollect_success_and_idempotent(self, client):
        """取消收藏成功；未收藏时取消幂等"""
        token = self._setup(client)
        art_id = _save_artwork(client, token)
        client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token))

        resp = client.delete(f'/workshop/works/{art_id}/collect', headers=_auth(token))
        assert resp.status_code == 200
        d = resp.get_json()['data']
        assert d['collected'] is False
        assert d['collect_count'] == 0

        resp2 = client.delete(f'/workshop/works/{art_id}/collect', headers=_auth(token))
        assert resp2.status_code == 200
        assert resp2.get_json()['data']['collect_count'] == 0

    def test_no_auth_401(self, client, app):
        """未登录收藏 → 401"""
        token = self._setup(client)
        art_id = _save_artwork(client, token)
        anon = app.test_client()
        resp = anon.post(f'/workshop/works/{art_id}/collect')
        assert resp.status_code == 401

    def test_not_found_404(self, client):
        """不存在作品 → 404"""
        token = self._setup(client)
        resp = client.post('/workshop/works/nonexistent/collect', headers=_auth(token))
        assert resp.status_code == 404

    def test_private_work_blocked(self, client, app):
        """私有作品不可收藏: 作者 400；他人 404"""
        token = self._setup(client)
        private_id = _save_artwork(client, token, is_public=False)

        resp = client.post(f'/workshop/works/{private_id}/collect', headers=_auth(token))
        assert resp.status_code == 400

        _register(client, 'cola2', 'cola2@e.com')
        token2 = _login(client, 'cola2@e.com')
        resp2 = client.post(f'/workshop/works/{private_id}/collect', headers=_auth(token2))
        assert resp2.status_code == 404

    def test_multi_user_collect_count(self, client):
        """多人收藏计数正确"""
        token_a = self._setup(client)
        art_id = _save_artwork(client, token_a)

        _register(client, 'cola3', 'cola3@e.com')
        token_b = _login(client, 'cola3@e.com')
        _register(client, 'cola4', 'cola4@e.com')
        token_c = _login(client, 'cola4@e.com')

        client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token_b))
        client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token_c))
        resp = client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token_a))
        assert resp.get_json()['data']['collect_count'] == 3


class TestCollectionIntegration:
    """列表/详情 collect_count 与 collected 真实统计 + 用户隔离"""

    def test_detail_collected_real(self, client):
        """详情 current_user_status.collected 真实: 已收藏 true/未收藏 false/匿名 false"""
        _register(client, 'coli1', 'coli1@e.com')
        token_a = _login(client, 'coli1@e.com')
        art_id = _save_artwork(client, token_a)

        _register(client, 'coli2', 'coli2@e.com')
        token_b = _login(client, 'coli2@e.com')

        client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token_b))
        # B 已收藏
        resp_b = client.get(f'/workshop/works/{art_id}', headers=_auth(token_b))
        d_b = resp_b.get_json()['data']
        assert d_b['current_user_status']['collected'] is True
        assert d_b['collect_count'] == 1
        # A 未收藏
        resp_a = client.get(f'/workshop/works/{art_id}', headers=_auth(token_a))
        assert resp_a.get_json()['data']['current_user_status']['collected'] is False
        # 匿名
        anon = client.application.test_client()
        resp_anon = anon.get(f'/workshop/works/{art_id}')
        assert resp_anon.get_json()['data']['current_user_status']['collected'] is False
        # 结构保持
        assert set(d_b['current_user_status'].keys()) == {'liked', 'collected', 'is_author'}

    def test_detail_collected_after_uncollect(self, client):
        """取消收藏后详情 collected=false"""
        token = client_register_login(client, 'colj1')
        art_id = _save_artwork(client, token)
        client.post(f'/workshop/works/{art_id}/collect', headers=_auth(token))
        client.delete(f'/workshop/works/{art_id}/collect', headers=_auth(token))

        resp = client.get(f'/workshop/works/{art_id}', headers=_auth(token))
        assert resp.get_json()['data']['current_user_status']['collected'] is False

    def test_list_collect_count_real(self, client):
        """列表 collect_count 批量真实统计"""
        _register(client, 'colk1', 'colk1@e.com')
        token_a = _login(client, 'colk1@e.com')
        art_a = _save_artwork(client, token_a, title='A')
        art_b = _save_artwork(client, token_a, title='B')

        _register(client, 'colk2', 'colk2@e.com')
        token_b = _login(client, 'colk2@e.com')
        _register(client, 'colk3', 'colk3@e.com')
        token_c = _login(client, 'colk3@e.com')

        client.post(f'/workshop/works/{art_a}/collect', headers=_auth(token_b))
        client.post(f'/workshop/works/{art_a}/collect', headers=_auth(token_c))
        client.post(f'/workshop/works/{art_b}/collect', headers=_auth(token_b))

        resp = client.get('/workshop/works')
        items = {w['id']: w for w in resp.get_json()['data']}
        assert items[art_a]['collect_count'] == 2
        assert items[art_b]['collect_count'] == 1


def client_register_login(client, username):
    """便捷: 注册并登录唯一用户"""
    _register(client, username, f'{username}@e.com')
    return _login(client, f'{username}@e.com')