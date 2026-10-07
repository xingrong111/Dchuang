# ============================================================
# 智绘锡承 - 模型成本排行测试（阶段16-C）
# 覆盖: GET /admin/statistics/models/ranking
#   - total_cost 降序 + rank 序号
#   - 同 provider 跨 task_type 合并成本与次数
#   - start_date/end_date 过滤
#   - 权限 403
# fixture 显式 AI_PROVIDER=mock + ADMIN_USER_IDS=1（隔离 .env 真实调用）
# ============================================================
from datetime import datetime, timedelta

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


def _admin_token(client):
    _register(client, 'rankadm', 'rankadm@e.com')
    return _login(client, 'rankadm@e.com')


def _seed_credit_tx(app, user_id, rows):
    """rows: [(amount, type, description, days_ago)]"""
    from app.extensions import db as flask_db
    from app.models.credit import CreditTransaction

    with app.app_context():
        for amount, tx_type, desc, days_ago in rows:
            tx = CreditTransaction(
                user_id=user_id, amount=amount, type=tx_type, description=desc)
            if days_ago:
                tx.created_at = datetime.utcnow() - timedelta(days=days_ago)
            flask_db.session.add(tx)
        flask_db.session.commit()


class TestModelRanking:
    """模型成本排行"""

    def _admin_and_user(self, client):
        token = _admin_token(client)
        resp = client.post('/auth/login', json={
            'email': 'rankadm@e.com', 'password': 'password123'})
        uid = resp.get_json()['data']['id']
        return token, uid

    def test_ranking_sorted_and_ranked(self, client, app, db):
        """按 total_cost 降序 + rank 序号 + 同 provider 跨类型合并"""
        token, uid = self._admin_and_user(client)
        _seed_credit_tx(app, uid, [
            # hunyuan: 3D 两次 = 40 + 分析一次 = 5 → 45（第一）
            (-20, 'AI_GENERATE_3D', 'AI_GENERATE_3D:hunyuan', 0),
            (-20, 'AI_GENERATE_3D', 'AI_GENERATE_3D:hunyuan', 0),
            (-5, 'AI_ANALYZE_STYLE', 'AI_ANALYZE_STYLE:hunyuan', 0),
            # mock: 30（第二）
            (-30, 'AI_GENERATE_3D', 'AI_GENERATE_3D:mock', 0),
            # glm: 8（第三）
            (-8, 'AI_ANALYZE_STYLE', 'AI_ANALYZE_STYLE:glm', 0),
            # 充值不计（amount>0）
            (100, 'RECHARGE', '注册赠送初始积分 100', 0),
        ])

        r = client.get('/admin/statistics/models/ranking', headers=_auth(token))
        assert r.status_code == 200
        ranking = r.get_json()['data']['ranking']
        assert [item['provider'] for item in ranking] == ['hunyuan', 'mock', 'glm']
        assert [item['rank'] for item in ranking] == [1, 2, 3]
        hunyuan = ranking[0]
        assert hunyuan['total_cost'] == 45
        assert hunyuan['count'] == 3
        assert hunyuan['task_types']['AI_GENERATE_3D'] == 2
        assert hunyuan['task_types']['AI_ANALYZE_STYLE'] == 1
        assert ranking[1]['total_cost'] == 30
        assert ranking[2]['total_cost'] == 8

    def test_ranking_date_filter(self, client, app, db):
        """start_date/end_date 过滤（范围外消费不计入）"""
        token, uid = self._admin_and_user(client)
        _seed_credit_tx(app, uid, [
            (-20, 'AI_GENERATE_3D', 'AI_GENERATE_3D:hunyuan', 0),   # 今天
            (-20, 'AI_GENERATE_3D', 'AI_GENERATE_3D:hunyuan', 5),   # 5 天前
            (-50, 'AI_GENERATE_3D', 'AI_GENERATE_3D:mock', 5),      # 5 天前
        ])

        # 只查今天 → hunyuan 20；mock 不在
        today = datetime.utcnow().strftime('%Y-%m-%d')
        r = client.get(f'/admin/statistics/models/ranking?start_date={today}',
                       headers=_auth(token))
        ranking = r.get_json()['data']['ranking']
        assert [item['provider'] for item in ranking] == ['hunyuan']
        assert ranking[0]['total_cost'] == 20

        # 全量 → hunyuan 40 第一、mock 50 第二
        r2 = client.get('/admin/statistics/models/ranking', headers=_auth(token))
        ranking2 = r2.get_json()['data']['ranking']
        assert ranking2[0]['provider'] == 'mock'
        assert ranking2[0]['total_cost'] == 50
        assert ranking2[1]['provider'] == 'hunyuan'
        assert ranking2[1]['total_cost'] == 40

    def test_ranking_unknown_provider_desc(self, client, app, db):
        """description 无冒号 → provider='unknown' 单独成行不崩溃"""
        token, uid = self._admin_and_user(client)
        _seed_credit_tx(app, uid, [
            (-20, 'AI_GENERATE_3D', 'AI_GENERATE_3D:hunyuan', 0),
            (-7, 'AI_GENERATE_3D', 'legacy-no-provider', 0),
        ])
        r = client.get('/admin/statistics/models/ranking', headers=_auth(token))
        assert r.status_code == 200
        ranking = r.get_json()['data']['ranking']
        by = {item['provider']: item for item in ranking}
        assert by['hunyuan']['total_cost'] == 20
        assert by['unknown']['total_cost'] == 7

    def test_ranking_empty(self, client, app, db):
        """无消费 → 空排行"""
        token, _ = self._admin_and_user(client)
        r = client.get('/admin/statistics/models/ranking', headers=_auth(token))
        assert r.status_code == 200
        assert r.get_json()['data']['ranking'] == []

    def test_ranking_permission_403(self, client, app, db):
        _register(client, 'rankadm', 'rankadm@e.com')
        _register(client, 'rankusr', 'rankusr@e.com')
        token = _login(client, 'rankusr@e.com')
        r = client.get('/admin/statistics/models/ranking', headers=_auth(token))
        assert r.status_code == 403
