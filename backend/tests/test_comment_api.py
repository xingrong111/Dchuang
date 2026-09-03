# ============================================================
# 智绘锡承 - Artwork 评论系统测试（阶段14-C）
# 覆盖: 创建/权限/校验/列表分页/删除权限/comment_count 真实统计/用户隔离
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


def _comment(client, art_id, token, content='好看的作品'):
    return client.post(f'/workshop/works/{art_id}/comments',
                       json={'content': content}, headers=_auth(token))


class TestCreateComment:
    """POST 评论"""

    def test_create_success(self, client):
        """登录用户评论成功 → 返回创建的评论（含作者信息）"""
        _register(client, 'cm1', 'cm1@e.com')
        token = _login(client, 'cm1@e.com')
        art_id = _save_artwork(client, token)

        resp = _comment(client, art_id, token, '非常有传统韵味！')
        assert resp.status_code == 200
        c = resp.get_json()['data']['comment']
        assert c['content'] == '非常有传统韵味！'
        assert c['artwork_id'] == art_id
        assert c['author']['username'] == 'cm1'
        assert c['created_at'] is not None

    def test_no_auth_401(self, client, app):
        """未登录评论 → 401"""
        _register(client, 'cm2', 'cm2@e.com')
        token = _login(client, 'cm2@e.com')
        art_id = _save_artwork(client, token)
        anon = app.test_client()
        resp = anon.post(f'/workshop/works/{art_id}/comments', json={'content': 'x'})
        assert resp.status_code == 401

    def test_empty_content_400(self, client):
        """空/纯空白内容 → 400"""
        _register(client, 'cm3', 'cm3@e.com')
        token = _login(client, 'cm3@e.com')
        art_id = _save_artwork(client, token)
        for bad in ('', '   '):
            resp = _comment(client, art_id, token, bad)
            assert resp.status_code == 400
            assert '内容' in resp.get_json()['message']

    def test_too_long_content_400(self, client):
        """超长内容（>1000）→ 400"""
        _register(client, 'cm4', 'cm4@e.com')
        token = _login(client, 'cm4@e.com')
        art_id = _save_artwork(client, token)
        resp = _comment(client, art_id, token, '长' * 1001)
        assert resp.status_code == 400

    def test_artwork_not_found_404(self, client):
        """作品不存在 → 404"""
        _register(client, 'cm5', 'cm5@e.com')
        token = _login(client, 'cm5@e.com')
        resp = _comment(client, 'nonexistent', token)
        assert resp.status_code == 404

    def test_private_work_permission(self, client, app):
        """私有作品不可评论: 作者 400；他人 404（不泄露）"""
        _register(client, 'cm6', 'cm6@e.com')
        token_a = _login(client, 'cm6@e.com')
        private_id = _save_artwork(client, token_a, is_public=False)

        resp = _comment(client, private_id, token_a)
        assert resp.status_code == 400

        _register(client, 'cm7', 'cm7@e.com')
        token_b = _login(client, 'cm7@e.com')
        resp_b = _comment(client, private_id, token_b)
        assert resp_b.status_code == 404


class TestListComments:
    """GET 评论列表"""

    def test_list_paginated_desc(self, client):
        """评论列表分页 + 时间倒序"""
        _register(client, 'cl1', 'cl1@e.com')
        token_a = _login(client, 'cl1@e.com')
        art_id = _save_artwork(client, token_a)

        # 3 个用户各评论 1 条
        for i in range(3):
            _register(client, f'cl{i+2}', f'cl{i+2}@e.com')
            t = _login(client, f'cl{i+2}@e.com')
            _comment(client, art_id, t, f'评论{i}')

        resp = client.get(f'/workshop/works/{art_id}/comments')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['meta']['pagination']['total'] == 3
        items = body['data']
        assert len(items) == 3
        # 倒序: 最后评论的在前
        assert items[0]['content'] == '评论2'
        # 分页
        resp2 = client.get(f'/workshop/works/{art_id}/comments?page=2&per_page=2')
        assert resp2.get_json()['meta']['pagination']['total'] == 3
        assert len(resp2.get_json()['data']) == 1

    def test_list_public_anonymous_ok(self, client, app):
        """匿名可看公开作品评论"""
        _register(client, 'cl9', 'cl9@e.com')
        token = _login(client, 'cl9@e.com')
        art_id = _save_artwork(client, token)
        _comment(client, art_id, token, '公开评论')

        anon = app.test_client()
        resp = anon.get(f'/workshop/works/{art_id}/comments')
        assert resp.status_code == 200
        assert len(resp.get_json()['data']) == 1

    def test_list_private_restricted(self, client, app):
        """私有作品评论列表: 作者可见（空/内容）；非作者 404"""
        _register(client, 'c10', 'c10@e.com')
        token_a = _login(client, 'c10@e.com')
        private_id = _save_artwork(client, token_a, is_public=False)

        # 私有作品不可评论（POST 400，见 TestCreateComment），作者可看空列表
        resp_author = client.get(f'/workshop/works/{private_id}/comments', headers=_auth(token_a))
        assert resp_author.status_code == 200
        assert resp_author.get_json()['meta']['pagination']['total'] == 0

        _register(client, 'c11', 'c11@e.com')
        token_b = _login(client, 'c11@e.com')
        resp_other = client.get(f'/workshop/works/{private_id}/comments', headers=_auth(token_b))
        assert resp_other.status_code == 404


class TestDeleteComment:
    """DELETE /comments/<id>"""

    def _create_comment(self, client, token, art_id, content='待删评论'):
        return _comment(client, art_id, token, content).get_json()['data']['comment']

    def test_author_delete_success(self, client):
        """评论作者删除成功"""
        _register(client, 'cd1', 'cd1@e.com')
        token = _login(client, 'cd1@e.com')
        art_id = _save_artwork(client, token)
        c = self._create_comment(client, token, art_id)

        resp = client.delete(f"/comments/{c['id']}", headers=_auth(token))
        assert resp.status_code == 200
        # 再查列表为空
        lst = client.get(f'/workshop/works/{art_id}/comments')
        assert lst.get_json()['meta']['pagination']['total'] == 0

    def test_non_author_delete_403(self, client):
        """非评论作者删除 → 403"""
        _register(client, 'cd2a', 'cd2a@e.com')
        token_a = _login(client, 'cd2a@e.com')
        art_id = _save_artwork(client, token_a)

        _register(client, 'cd2b', 'cd2b@e.com')
        token_b = _login(client, 'cd2b@e.com')
        c = self._create_comment(client, token_b, art_id)

        resp = client.delete(f"/comments/{c['id']}", headers=_auth(token_a))
        assert resp.status_code == 403

    def test_delete_not_found_404(self, client):
        """评论不存在 → 404"""
        _register(client, 'cd3', 'cd3@e.com')
        token = _login(client, 'cd3@e.com')
        resp = client.delete('/comments/999999', headers=_auth(token))
        assert resp.status_code == 404

    def test_delete_no_auth_401(self, client, app):
        """未登录删除 → 401"""
        _register(client, 'cd4', 'cd4@e.com')
        token = _login(client, 'cd4@e.com')
        art_id = _save_artwork(client, token)
        c = self._create_comment(client, token, art_id)

        anon = app.test_client()
        resp = anon.delete(f"/comments/{c['id']}")
        assert resp.status_code == 401


class TestCommentCountIntegration:
    """comment_count 真实统计（详情/列表）+ 用户隔离"""

    def test_detail_comment_count_real(self, client):
        """详情 comment_count 真实统计"""
        _register(client, 'cc1', 'cc1@e.com')
        token_a = _login(client, 'cc1@e.com')
        art_id = _save_artwork(client, token_a)

        _register(client, 'cc2', 'cc2@e.com')
        token_b = _login(client, 'cc2@e.com')
        _comment(client, art_id, token_b, '第一条')
        _comment(client, art_id, token_b, '第二条')

        resp = client.get(f'/workshop/works/{art_id}', headers=_auth(token_a))
        d = resp.get_json()['data']
        assert d['comment_count'] == 2
        # current_user_status 结构保持
        assert set(d['current_user_status'].keys()) == {'liked', 'collected', 'is_author'}

    def test_list_comment_count_real(self, client):
        """列表 comment_count 批量真实统计"""
        _register(client, 'cc3', 'cc3@e.com')
        token_a = _login(client, 'cc3@e.com')
        art_a = _save_artwork(client, token_a, title='A作品')
        art_b = _save_artwork(client, token_a, title='B作品')

        _register(client, 'cc4', 'cc4@e.com')
        token_b = _login(client, 'cc4@e.com')
        _comment(client, art_a, token_b, '评论A-1')
        _comment(client, art_a, token_b, '评论A-2')
        _comment(client, art_b, token_b, '评论B-1')

        resp = client.get('/workshop/works')
        items = {w['id']: w for w in resp.get_json()['data']}
        assert items[art_a]['comment_count'] == 2
        assert items[art_b]['comment_count'] == 1

    def test_user_isolated_delete_only_own(self, client):
        """用户隔离: 删除他人评论 403；本人评论删除不影响他人评论"""
        _register(client, 'cc5', 'cc5@e.com')
        token_a = _login(client, 'cc5@e.com')
        art_id = _save_artwork(client, token_a)

        _register(client, 'cc6', 'cc6@e.com')
        token_b = _login(client, 'cc6@e.com')
        _register(client, 'cc7', 'cc7@e.com')
        token_c = _login(client, 'cc7@e.com')

        cb = _comment(client, art_id, token_b).get_json()['data']['comment']
        cc = _comment(client, art_id, token_c).get_json()['data']['comment']

        # B 删除 C 的评论 → 403
        resp = client.delete(f"/comments/{cc['id']}", headers=_auth(token_b))
        assert resp.status_code == 403
        # B 删除自己的 → 200
        resp2 = client.delete(f"/comments/{cb['id']}", headers=_auth(token_b))
        assert resp2.status_code == 200
        # C 评论仍在
        lst = client.get(f'/workshop/works/{art_id}/comments')
        assert lst.get_json()['meta']['pagination']['total'] == 1