# ============================================================
# 智绘锡承 - AI 任务历史增强测试（阶段15-A）
# 覆盖: GET /ai/history（分页/隔离/Artwork 关联）+ POST /ai/tasks/<id>/retry
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


def _seed_task(app, user_id, status='SUCCESS', task_type='text_to_3d', prompt='历史任务',
               provider='hunyuan', model='hunyuan-3d', artwork_id=None, error=None):
    """直接落库一个 AITask"""
    from app.extensions import db as flask_db
    from app.models.ai_task import AITask

    with app.app_context():
        task = AITask(
            user_id=user_id, provider=provider, model=model,
            task_type=task_type, prompt=prompt, status=status,
            artwork_id=artwork_id, error_message=error,
        )
        flask_db.session.add(task)
        flask_db.session.commit()
        return task.id


def _stub_running_gen():
    """Provider stub: 生成返回 RUNNING"""
    class StubGen:
        provider_name = 'hunyuan'
        model = 'hunyuan-3d'

        def generate_3d(self, task):
            return {'status': 'RUNNING', 'external_task_id': 'job-retry-1',
                    'result_url': None, 'error_message': None}

    return StubGen()


class TestAIHistory:
    """GET /ai/history"""

    def test_history_paginated_desc_with_artwork(self, client, app):
        """历史列表: 分页 + 倒序 + artwork 关联摘要 + 指定字段"""
        _register(client, 'ah1', 'ah1@e.com')
        resp = client.post('/auth/login', json={'email': 'ah1@e.com', 'password': 'password123'})
        data = resp.get_json()['data']

        # 建 Artwork + 关联任务
        art = client.post('/workshop/save', json={'title': '关联作品'},
                          headers=_auth(data['token']))
        art_id = art.get_json()['data']['id']
        tid2 = _seed_task(app, data['id'], prompt='旧任务', artwork_id=art_id)
        tid1 = _seed_task(app, data['id'], prompt='新任务')

        r = client.get('/ai/history', headers=_auth(data['token']))
        assert r.status_code == 200
        body = r.get_json()
        assert body['meta']['pagination']['total'] == 2
        items = body['data']
        # 倒序: 新任务在前
        assert items[0]['prompt'] == '新任务'
        assert items[1]['prompt'] == '旧任务'
        # 指定字段存在
        first = items[0]
        for key in ('id', 'status', 'provider', 'model', 'task_type', 'prompt',
                    'result_url', 'artwork_id', 'created_at'):
            assert key in first
        # artwork 关联摘要（批量无 N+1）
        linked = next(i for i in items if i['artwork_id'] == art_id)
        assert linked['artwork'] == {'id': art_id, 'title': '关联作品',
                                     'thumbnail': None, 'model_url': None}
        unlinked = next(i for i in items if i['artwork_id'] is None)
        assert unlinked['artwork'] is None

    def test_history_user_isolated(self, client, app):
        """历史仅本人任务（用户隔离）"""
        _register(client, 'ah2a', 'ah2a@e.com')
        ra = client.post('/auth/login', json={'email': 'ah2a@e.com', 'password': 'password123'})
        _seed_task(app, ra.get_json()['data']['id'])

        _register(client, 'ah2b', 'ah2b@e.com')
        rb = client.post('/auth/login', json={'email': 'ah2b@e.com', 'password': 'password123'})
        r = client.get('/ai/history', headers=_auth(rb.get_json()['data']['token']))
        assert r.get_json()['meta']['pagination']['total'] == 0

    def test_history_pagination(self, client, app):
        """分页参数生效"""
        _register(client, 'ah3', 'ah3@e.com')
        resp = client.post('/auth/login', json={'email': 'ah3@e.com', 'password': 'password123'})
        data = resp.get_json()['data']
        for i in range(5):
            _seed_task(app, data['id'], prompt=f'任务{i}')

        r = client.get('/ai/history?page=2&per_page=2', headers=_auth(data['token']))
        body = r.get_json()
        assert body['meta']['pagination']['total'] == 5
        assert len(body['data']) == 2

    def test_history_no_auth_401(self, client):
        """未登录 → 401"""
        r = client.get('/ai/history')
        assert r.status_code == 401


class TestRetryTask:
    """POST /ai/tasks/<id>/retry"""

    def _register_login(self, client, name='retry1'):
        _register(client, name, f'{name}@e.com')
        return _login(client, f'{name}@e.com')

    def test_retry_failed_creates_new(self, client, app, monkeypatch):
        """失败任务重试: 创建新任务（复制参数）重新执行，旧任务不变"""
        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: _stub_running_gen())
        token = self._register_login(client)
        resp = client.post('/auth/login', json={'email': 'retry1@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        old_id = _seed_task(app, uid, status='FAILED', prompt='重试紫砂壶',
                            error='生成失败：内容不合规')

        r = client.post(f'/ai/tasks/{old_id}/retry', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['id'] != old_id            # 新任务
        assert d['status'] == 'RUNNING'      # 重新执行（stub RUNNING）
        assert d['provider'] == 'hunyuan'    # provider 一致
        assert d['model'] == 'hunyuan-3d'
        assert d['task_type'] == 'text_to_3d'
        assert d['prompt'] == '重试紫砂壶'
        assert d['error_message'] is None    # 全新执行

        # 旧任务保持不变（仍 FAILED + 原错误）
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask
        with app.app_context():
            old = flask_db.session.get(AITask, old_id)
            assert old.status == 'FAILED'
            assert old.error_message == '生成失败：内容不合规'
            # 仅新增 1 条
            assert AITask.query.filter_by(user_id=uid).count() == 2

    def test_retry_other_user_404(self, client, app):
        """他人任务重试 → 404（不泄露存在性）"""
        _register(client, 'rt1a', 'rt1a@e.com')
        ra = client.post('/auth/login', json={'email': 'rt1a@e.com', 'password': 'password123'})
        uid_a = ra.get_json()['data']['id']
        old_id = _seed_task(app, uid_a, status='FAILED')

        _register(client, 'rt1b', 'rt1b@e.com')
        token_b = _login(client, 'rt1b@e.com')
        r = client.post(f'/ai/tasks/{old_id}/retry', headers=_auth(token_b))
        assert r.status_code == 404

    def test_retry_nonexistent_404(self, client, app):
        """不存在任务 → 404"""
        token = self._register_login(client, 'retry2')
        r = client.post('/ai/tasks/nonexistent-id/retry', headers=_auth(token))
        assert r.status_code == 404

    def test_retry_success_forbidden(self, client, app):
        """SUCCESS 任务禁止重试 → 400"""
        token = self._register_login(client, 'retry3')
        resp = client.post('/auth/login', json={'email': 'retry3@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        tid = _seed_task(app, uid, status='SUCCESS')

        r = client.post(f'/ai/tasks/{tid}/retry', headers=_auth(token))
        assert r.status_code == 400
        assert '仅失败任务可重试' in r.get_json()['message']

    def test_retry_running_forbidden(self, client, app):
        """RUNNING 任务禁止重试 → 400"""
        token = self._register_login(client, 'retry4')
        resp = client.post('/auth/login', json={'email': 'retry4@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        tid = _seed_task(app, uid, status='RUNNING')

        r = client.post(f'/ai/tasks/{tid}/retry', headers=_auth(token))
        assert r.status_code == 400

    def test_retry_no_auth_401(self, client):
        """未登录重试 → 401"""
        r = client.post('/ai/tasks/some-id/retry')
        assert r.status_code == 401