# ============================================================
# 智绘锡承 - 审计日志查询 + 任务 CSV 导出测试（阶段16-B）
# ============================================================
import io

import pytest


@pytest.fixture
def app(tmp_path):
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'
    app.config['ADMIN_USER_IDS'] = '1'
    return app


@pytest.fixture
def db(app):
    from app.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app, db):
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


def _seed_admin_logs(app, admin_ids, count=5):
    from app.extensions import db as flask_db
    from app.models.admin_log import AdminLog

    with app.app_context():
        for i in range(count):
            flask_db.session.add(AdminLog(
                admin_user_id=admin_ids[i % len(admin_ids)],
                action='task_retry' if i % 2 == 0 else 'provider_update',
                target_type='aitask' if i % 2 == 0 else 'ai_provider',
                target_id=f't-{i}', detail=f'{{"i": {i}}}'))
        flask_db.session.commit()


class TestAdminLogs:
    """GET /admin/logs"""

    def _admin_token(self, client):
        _register(client, 'logad', 'logad@e.com')
        return _login(client, 'logad@e.com')

    def test_paginated(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={
            'email': 'logad@e.com', 'password': 'password123'})
        admin_uid = resp.get_json()['data']['id']
        _seed_admin_logs(app, [admin_uid], count=5)

        r = client.get('/admin/logs?per_page=3', headers=_auth(token))
        body = r.get_json()
        assert body['meta']['pagination']['total'] == 5
        assert len(body['data']) == 3

    def test_filter_action(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={
            'email': 'logad@e.com', 'password': 'password123'})
        admin_uid = resp.get_json()['data']['id']
        _seed_admin_logs(app, [admin_uid], count=6)

        r = client.get('/admin/logs?action=task_retry', headers=_auth(token))
        items = r.get_json()['data']
        assert len(items) == 3
        assert all(i['action'] == 'task_retry' for i in items)

    def test_filter_target_type(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={
            'email': 'logad@e.com', 'password': 'password123'})
        admin_uid = resp.get_json()['data']['id']
        _seed_admin_logs(app, [admin_uid], count=6)

        r = client.get('/admin/logs?target_type=ai_provider', headers=_auth(token))
        items = r.get_json()['data']
        assert len(items) == 3
        assert all(i['target_type'] == 'ai_provider' for i in items)

    def test_permission(self, client):
        _register(client, 'lg1', 'lg1@e.com')
        _login(client, 'lg1@e.com')
        _register(client, 'lg2', 'lg2@e.com')
        token2 = _login(client, 'lg2@e.com')
        r = client.get('/admin/logs', headers=_auth(token2))
        assert r.status_code == 403


class TestTaskExport:
    """GET /admin/tasks/export CSV"""

    def _admin_token(self, client):
        _register(client, 'expad', 'expad@e.com')
        return _login(client, 'expad@e.com')

    def _seed_tasks(self, app, user_ids):
        """造任务：SUCCESS(消费 20) + FAILED + RUNNING"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask
        from app.models.credit import CreditTransaction

        with app.app_context():
            for i, (status, user_id) in enumerate([
                    ('SUCCESS', user_ids[0]), ('FAILED', user_ids[0]),
                    ('RUNNING', user_ids[0])]):
                task = AITask(user_id=user_id, provider='hunyuan', model='hunyuan-3d',
                              task_type='text_to_3d', prompt=f'导出任务{i}', status=status,
                              external_task_id=f'job-{i}' if status == 'RUNNING' else None)
                flask_db.session.add(task)
                flask_db.session.flush()
                if status == 'SUCCESS':
                    flask_db.session.add(CreditTransaction(
                        user_id=user_id, amount=-20, type='AI_GENERATE_3D',
                        description='AI_GENERATE_3D:hunyuan', reference_id=task.id))
            flask_db.session.commit()

    def test_csv_fields_and_content(self, client, app):
        token = self._admin_token(client)
        resp = client.post('/auth/login', json={
            'email': 'expad@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        self._seed_tasks(app, [uid])

        r = client.get('/admin/tasks/export', headers=_auth(token))
        assert r.status_code == 200
        assert 'text/csv' in r.content_type
        text = r.get_data(as_text=True)
        rows = list(csv_reader(text))
        header = rows[0]
        assert header == ['task_id', 'user', 'provider', 'model', 'status',
                          'cost', 'created_at', 'artwork_id']
        assert len(rows) == 4  # header + 3 tasks
        # SUCCESS 行 cost=20
        success_row = next(row for row in rows[1:] if row[4] == 'SUCCESS')
        assert success_row[1] == 'expad'  # user
        assert success_row[2] == 'hunyuan'  # provider
        assert success_row[5] == '20'  # cost
        failed_row = next(row for row in rows[1:] if row[4] == 'FAILED')
        assert failed_row[5] == '0'  # 无消费

    def test_csv_streaming_generator(self, client, app):
        """流式: 响应体由生成器分页产出（不一次加载全部——分页 fetch 500/页）"""
        from app.api.v1.admin import _iter_task_rows

        token = self._admin_token(client)
        resp = client.post('/auth/login', json={
            'email': 'expad@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        self._seed_tasks(app, [uid])

        # 生成器逐块产出（assert 有 yield 能力）
        gen = _iter_task_rows({'status': '', 'provider': ''}, header=True)
        chunks = list(gen)
        assert len(chunks) >= 1
        full = ''.join(chunks)
        assert full.startswith('task_id,user,provider,model,status,cost,created_at,artwork_id')

    def test_csv_permission(self, client):
        _register(client, 'ex1', 'ex1@e.com')
        _login(client, 'ex1@e.com')
        _register(client, 'ex2', 'ex2@e.com')
        token2 = _login(client, 'ex2@e.com')
        r = client.get('/admin/tasks/export', headers=_auth(token2))
        assert r.status_code == 403


def csv_reader(text):
    import csv
    return list(csv.reader(io.StringIO(text)))