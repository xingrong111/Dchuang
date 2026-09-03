# ============================================================
# 智绘锡承 - Artwork 点赞系统测试（阶段14-B）
# 覆盖: Like 模型约束 / 点赞取消（幂等）/ 私有作品禁止 /
#       列表 like_count 真实统计 / 详情 current_user_status.liked
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
    resp = client.post('/workshop/save', json={
        'title': title, 'is_public': is_public,
    }, headers=_auth(token))
    assert resp.status_code == 200
    return resp.get_json()['data']['id']


class TestLikeModel:
    """Like 模型约束"""

    def test_unique_user_artwork(self, app, db):
        """同一 (user, artwork) 不能重复插入（唯一约束）"""
        from sqlalchemy.exc import IntegrityError

        from app.extensions import db as flask_db
        from app.models.artwork import Artwork
        from app.models.like import Like
        from app.models.user import User

        with app.app_context():
            user = User(username='likeu1', email='likeu1@e.com', password='pass123')
            flask_db.session.add(user)
            flask_db.session.commit()
            artwork = Artwork(user_id=user.id, title='L')
            flask_db.session.add(artwork)
            flask_db.session.commit()

            flask_db.session.add(Like(user_id=user.id, artwork_id=artwork.id))
            flask_db.session.commit()
            # 重复插入 → 唯一约束违反
            flask_db.session.add(Like(user_id=user.id, artwork_id=artwork.id))
            with pytest.raises(IntegrityError):
                flask_db.session.commit()
            flask_db.session.rollback()

    def test_artwork_delete_cascades_likes(self, app, db):
        """删除 Artwork → 其 Like 级联删除"""
        from app.extensions import db as flask_db
        from app.models.artwork import Artwork
        from app.models.like import Like
        from app.models.user import User

        with app.app_context():
            u1 = User(username='likeu2', email='likeu2@e.com', password='pass123')
            u2 = User(username='likeu3', email='likeu3@e.com', password='pass123')
            flask_db.session.add_all([u1, u2])
            flask_db.session.commit()
            artwork = Artwork(user_id=u1.id, title='删除级联')
            flask_db.session.add(artwork)
            flask_db.session.commit()
            flask_db.session.add_all([
                Like(user_id=u1.id, artwork_id=artwork.id),
                Like(user_id=u2.id, artwork_id=artwork.id),
            ])
            flask_db.session.commit()
            assert Like.query.count() == 2

            flask_db.session.delete(artwork)
            flask_db.session.commit()
            assert Like.query.count() == 0  # 级联删除


class TestLikeAPI:
    """POST/DELETE /workshop/works/<id>/like"""

    def _setup(self, client):
        _register(client, 'liker1', 'lk1@e.com')
        token = _login(client, 'lk1@e.com')
        return token

    def test_like_success(self, client):
        """点赞成功 → liked=true + like_count=1"""
        token = self._setup(client)
        art_id = _save_artwork(client, token)

        resp = client.post(f'/workshop/works/{art_id}/like', headers=_auth(token))
        assert resp.status_code == 200
        d = resp.get_json()['data']
        assert d['liked'] is True
        assert d['like_count'] == 1

    def test_like_idempotent(self, client):
        """重复点赞幂等 → like_count 仍 1（不重复计数）"""
        token = self._setup(client)
        art_id = _save_artwork(client, token)

        client.post(f'/workshop/works/{art_id}/like', headers=_auth(token))
        resp2 = client.post(f'/workshop/works/{art_id}/like', headers=_auth(token))
        assert resp2.status_code == 200
        assert resp2.get_json()['data']['like_count'] == 1

    def test_unlike_success_and_idempotent(self, client):
        """取消点赞成功；未赞时取消幂等"""
        token = self._setup(client)
        art_id = _save_artwork(client, token)
        client.post(f'/workshop/works/{art_id}/like', headers=_auth(token))

        resp = client.delete(f'/workshop/works/{art_id}/like', headers=_auth(token))
        assert resp.status_code == 200
        d = resp.get_json()['data']
        assert d['liked'] is False
        assert d['like_count'] == 0

        # 幂等: 再取消
        resp2 = client.delete(f'/workshop/works/{art_id}/like', headers=_auth(token))
        assert resp2.status_code == 200
        assert resp2.get_json()['data']['like_count'] == 0

    def test_like_no_auth_401(self, client, app):
        """未登录点赞 → 401（干净 client 无 Session/Bearer）"""
        _register(client, 'liker2', 'liker2@e.com')
        token = _login(client, 'liker2@e.com')
        art_id = _save_artwork(client, token)

        anon = app.test_client()  # 无 Session Cookie
        resp = anon.post(f'/workshop/works/{art_id}/like')
        assert resp.status_code == 401

    def test_like_not_found_404(self, client):
        """不存在作品 → 404"""
        token = self._setup(client)
        resp = client.post('/workshop/works/nonexistent/like', headers=_auth(token))
        assert resp.status_code == 404

    def test_like_private_work_blocked(self, client, app):
        """私有作品不可点赞: 作者 400；他人 404（不泄露）"""
        token = self._setup(client)
        private_id = _save_artwork(client, token, is_public=False)

        resp = client.post(f'/workshop/works/{private_id}/like', headers=_auth(token))
        assert resp.status_code == 400  # 作者明确不可点赞

        anon = app.test_client()
        _register(client, 'liker3', 'lk3@e.com')
        token3 = _login(client, 'lk3@e.com')
        resp3 = anon.post(f'/workshop/works/{private_id}/like', headers=_auth(token3))
        assert resp3.status_code == 404  # 他人不可见/不可操作

    def test_multi_user_like_count(self, client):
        """多人点赞计数正确"""
        token_a = self._setup(client)
        art_id = _save_artwork(client, token_a)

        _register(client, 'liker4', 'lk4@e.com')
        token_b = _login(client, 'lk4@e.com')
        _register(client, 'liker5', 'lk5@e.com')
        token_c = _login(client, 'lk5@e.com')

        client.post(f'/workshop/works/{art_id}/like', headers=_auth(token_b))
        client.post(f'/workshop/works/{art_id}/like', headers=_auth(token_c))
        resp = client.post(f'/workshop/works/{art_id}/like', headers=_auth(token_a))
        assert resp.get_json()['data']['like_count'] == 3


class TestLikeIntegration:
    """列表/详情 like_count 与 liked 真实统计"""

    def test_list_like_count_real(self, client):
        """列表 like_count 使用真实统计（即使 Artwork.like_count 列未维护）"""
        from app.extensions import db as flask_db
        from app.models.artwork import Artwork

        _register(client, 'liki1', 'liki1@e.com')
        token_a = _login(client, 'liki1@e.com')
        art_id = _save_artwork(client, token_a, title='被赞作品')

        _register(client, 'liki2', 'liki2@e.com')
        token_b = _login(client, 'liki2@e.com')
        client.post(f'/workshop/works/{art_id}/like', headers=_auth(token_b))

        resp = client.get('/workshop/works')
        item = next(w for w in resp.get_json()['data'] if w['id'] == art_id)
        assert item['like_count'] == 1

        # 列仍为 0（未手动维护）但接口返回真实 count —— 证明 count 为准
        with client.application.app_context():
            art = flask_db.session.get(Artwork, art_id)
            assert art.like_count == 0

    def test_detail_liked_real_for_user(self, client):
        """详情 current_user_status.liked: 已赞用户 true；未赞用户 false"""
        _register(client, 'likd1', 'likd1@e.com')
        token_a = _login(client, 'likd1@e.com')
        art_id = _save_artwork(client, token_a)

        _register(client, 'likd2', 'likd2@e.com')
        token_b = _login(client, 'likd2@e.com')

        # B 点赞
        client.post(f'/workshop/works/{art_id}/like', headers=_auth(token_b))
        # B 看详情 → liked true
        resp_b = client.get(f'/workshop/works/{art_id}', headers=_auth(token_b))
        assert resp_b.get_json()['data']['current_user_status']['liked'] is True
        assert resp_b.get_json()['data']['like_count'] == 1
        # A（作者未赞）→ liked false
        resp_a = client.get(f'/workshop/works/{art_id}', headers=_auth(token_a))
        assert resp_a.get_json()['data']['current_user_status']['liked'] is False
        # 匿名 → liked false
        anon = client.application.test_client()
        resp_anon = anon.get(f'/workshop/works/{art_id}')
        assert resp_anon.get_json()['data']['current_user_status']['liked'] is False

    def test_detail_liked_after_unlike(self, client):
        """取消点赞后详情 liked=false"""
        _register(client, 'liku1', 'liku1@e.com')
        token = _login(client, 'liku1@e.com')
        art_id = _save_artwork(client, token)
        client.post(f'/workshop/works/{art_id}/like', headers=_auth(token))
        client.delete(f'/workshop/works/{art_id}/like', headers=_auth(token))

        resp = client.get(f'/workshop/works/{art_id}', headers=_auth(token))
        assert resp.get_json()['data']['current_user_status']['liked'] is False