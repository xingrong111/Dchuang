# ============================================================
# 智绘锡承 - 平台积分系统测试（阶段15-B）
# 覆盖: 注册初始化/余额/消费/不足/退款/隔离/AI 扣费/AI 失败退款/重复不重复扣费
# fixture 显式 AI_PROVIDER=mock（隔离 backend/.env 的 hunyuan，禁止真实腾讯调用）
# ============================================================
import pytest


@pytest.fixture
def app(tmp_path):
    """创建测试应用（SQLite 内存库 + 临时上传目录 + Mock Provider）"""
    from app import create_app

    app = create_app('testing')
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')
    app.config['AI_PROVIDER'] = 'mock'  # 显式 Mock（隔离 .env）
    app.config['AI_COST_3D_GENERATE'] = 20
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


def _register(client, username='credit1', email='credit1@e.com'):
    resp = client.post('/auth/register', json={
        'username': username, 'email': email, 'password': 'password123',
    })
    assert resp.status_code == 200
    return resp.get_json()['data']


def _login(client, email='credit1@e.com'):
    resp = client.post('/auth/login', json={'email': email, 'password': 'password123'})
    assert resp.status_code == 200
    return resp.get_json()['data']['token']


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


class TestRegisterInit:
    """注册自动创建账户 + 初始 100"""

    def test_register_creates_account_100(self, client):
        """注册后 GET /user/credits: balance=100 + RECHARGE 流水"""
        _register(client)
        token = _login(client)
        r = client.get('/user/credits', headers=_auth(token))
        assert r.status_code == 200
        d = r.get_json()['data']
        assert d['balance'] == 100
        txs = d['transactions']
        assert len(txs) == 1
        assert txs[0]['type'] == 'RECHARGE'
        assert txs[0]['amount'] == 100

    def test_register_duplicate_no_double_account(self, client, app):
        """同一用户重复注册不产生双账户（唯一 email 拦截）"""
        _register(client)
        resp = client.post('/auth/register', json={
            'username': 'credit1', 'email': 'credit1@e.com', 'password': 'password123',
        })
        assert resp.status_code == 400  # 用户名/邮箱已存在


class TestCreditService:
    """CreditService 单元（app context）"""

    def _make_user(self, app, db):
        from app.extensions import db as flask_db
        from app.models.user import User

        with app.app_context():
            user = User(username='svc1', email='svc1@e.com', password='pass123')
            flask_db.session.add(user)
            flask_db.session.commit()
            return user.id

    def test_get_balance(self, app, db):
        """余额查询（注册初始化后 100；无账户 0）"""
        from app.services.credit import CreditService

        uid = self._make_user(app, db)
        with app.app_context():
            CreditService.init_account(uid)
            assert CreditService.get_balance(uid) == 100
            assert CreditService.get_balance(999999) == 0  # 无账户

    def test_consume_success(self, app, db):
        """消费成功: 余额减少 + 交易记录（amount 负数）"""
        from app.extensions import db as flask_db
        from app.models.credit import CreditTransaction
        from app.services.credit import CreditService

        uid = self._make_user(app, db)
        with app.app_context():
            CreditService.init_account(uid)
            bal = CreditService().consume(uid, 20, 'AI_GENERATE_3D', reference_id='task-1')
            assert bal == 80
            tx = (CreditTransaction.query
                  .filter_by(user_id=uid, type='AI_GENERATE_3D').first())
            assert tx.amount == -20
            assert tx.reference_id == 'task-1'

    def test_consume_insufficient_raises(self, app, db):
        """余额不足 → CreditInsufficientError（402），余额不变"""
        from app.extensions import db as flask_db
        from app.models.user import User
        from app.services.credit import CreditService
        from app.utils.exceptions import CreditInsufficientError

        with app.app_context():
            user = User(username='svc2', email='svc2@e.com', password='pass123')
            flask_db.session.add(user)
            flask_db.session.commit()
            # 不初始化 → 余额 0
            with pytest.raises(CreditInsufficientError):
                CreditService().consume(user.id, 10, 'AI_GENERATE_3D')
            assert CreditService.get_balance(user.id) == 0

    def test_consume_idempotent_by_reference(self, app, db):
        """同 reference 重复消费 → 只扣一次"""
        from app.extensions import db as flask_db
        from app.models.credit import CreditTransaction
        from app.models.user import User
        from app.services.credit import CreditService

        with app.app_context():
            user = User(username='svc3', email='svc3@e.com', password='pass123')
            flask_db.session.add(user)
            flask_db.session.commit()
            CreditService.init_account(user.id)
            CreditService().consume(user.id, 20, 'AI_GENERATE_3D', reference_id='task-x')
            bal2 = CreditService().consume(user.id, 20, 'AI_GENERATE_3D', reference_id='task-x')
            assert bal2 == 80  # 未重复扣
            assert CreditTransaction.query.filter_by(
                user_id=user.id, reference_id='task-x', type='AI_GENERATE_3D'
            ).count() == 1

    def test_refund(self, app, db):
        """退款（REFUND 正向）恢复余额；同 reference 不重复退"""
        from app.extensions import db as flask_db
        from app.models.credit import CreditTransaction
        from app.models.user import User
        from app.services.credit import CreditService

        with app.app_context():
            user = User(username='svc4', email='svc4@e.com', password='pass123')
            flask_db.session.add(user)
            flask_db.session.commit()
            CreditService.init_account(user.id)
            CreditService().consume(user.id, 20, 'AI_GENERATE_3D', reference_id='task-r')
            bal = CreditService().recharge(user.id, 20, 'REFUND', reference_id='task-r',
                                           description='失败退款')
            assert bal == 100
            # 幂等: 再退不重复
            CreditService().recharge(user.id, 20, 'REFUND', reference_id='task-r')
            assert CreditService.get_balance(user.id) == 100
            assert CreditTransaction.query.filter_by(
                user_id=user.id, type='REFUND', reference_id='task-r'
            ).count() == 1


class TestCreditAI:
    """AI 生成扣费/退款/重复保护集成"""

    def test_generate_deducts_credit(self, client, app):
        """AI 3D 生成成功（mock）→ 扣 20 积分 + AI_GENERATE_3D 流水"""
        from app.models.credit import CreditTransaction

        _register(client)
        token = _login(client)
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '生成紫砂壶',
        }, headers=_auth(token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['status'] == 'SUCCESS'

        r = client.get('/user/credits', headers=_auth(token))
        assert r.get_json()['data']['balance'] == 80  # 100 - 20
        types = [t['type'] for t in r.get_json()['data']['transactions']]
        assert 'AI_GENERATE_3D' in types
        assert 'RECHARGE' in types

    def test_generate_failure_refunds(self, client, app, monkeypatch):
        """AI 生成失败（mock fail）→ 自动退款，余额恢复 100"""
        from app.services.mock import MockProvider

        monkeypatch.setattr('app.api.v1.ai.get_ai_service',
                            lambda: MockProvider(mock_behavior='fail'))
        _register(client)
        token = _login(client)
        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '必然失败的任务',
        }, headers=_auth(token))
        assert resp.status_code == 200
        assert resp.get_json()['data']['status'] == 'FAILED'

        r = client.get('/user/credits', headers=_auth(token))
        d = r.get_json()['data']
        assert d['balance'] == 100  # 扣 20 后退回
        types = [t['type'] for t in d['transactions']]
        assert 'AI_GENERATE_3D' in types
        assert 'REFUND' in types

    def test_generate_duplicate_no_double_charge(self, client, app, monkeypatch):
        """重复任务（同 prompt RUNNING）去重命中 → 不重复扣费"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask

        class StubRunningGen:
            provider_name = 'hunyuan'
            model = 'hunyuan-3d'

            def generate_3d(self, task):
                return {'status': 'RUNNING', 'external_task_id': 'job-dup-c',
                        'result_url': None, 'error_message': None}

        monkeypatch.setattr('app.api.v1.ai.get_ai_service', lambda: StubRunningGen())
        _register(client)
        token = _login(client)

        body = {'task_type': 'text_to_3d', 'prompt': '重复扣费测试'}
        r1 = client.post('/ai/generate-3d', json=body, headers=_auth(token))
        assert r1.get_json()['data']['status'] == 'RUNNING'
        r2 = client.post('/ai/generate-3d', json=body, headers=_auth(token))
        assert '正在执行' in r2.get_json()['message']  # 去重命中

        r = client.get('/user/credits', headers=_auth(token))
        assert r.get_json()['data']['balance'] == 80  # 仅扣一次（100-20）
        with app.app_context():
            assert AITask.query.count() == 1

    def test_insufficient_credits_402(self, client, app):
        """余额不足 → 402 且不创建任务"""
        from app.extensions import db as flask_db
        from app.models.ai_task import AITask
        from app.models.credit import CreditAccount, CreditTransaction

        _register(client)
        token = _login(client)
        # 清空余额（消费到不足）
        with app.app_context():
            from app.models.user import User
            user = User.query.filter_by(username='credit1').first()
            uid = user.id
            acct = CreditAccount.query.filter_by(user_id=uid).first()
            acct.balance = 5
            flask_db.session.commit()

        resp = client.post('/ai/generate-3d', json={
            'task_type': 'text_to_3d', 'prompt': '余额不足测试',
        }, headers=_auth(token))
        assert resp.status_code == 402
        assert '积分不足' in resp.get_json()['message']
        with app.app_context():
            assert AITask.query.count() == 0  # 未创建任务
            assert CreditTransaction.query.filter_by(user_id=uid).count() == 1  # 仅注册充值


class TestCreditsAPI:
    """GET /user/credits 分页/隔离/401"""

    def test_no_auth_401(self, client):
        """未登录 → 401"""
        r = client.get('/user/credits')
        assert r.status_code == 401

    def test_user_isolated(self, client):
        """用户隔离: 各自余额/流水独立"""
        _register(client, 'crdA', 'crdA@e.com')
        token_a = _login(client, 'crdA@e.com')
        _register(client, 'crdB', 'crdB@e.com')
        token_b = _login(client, 'crdB@e.com')

        # A 消费一次（mock 3D 生成）
        client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': 'A的任务'},
                    headers=_auth(token_a))
        bal_a = client.get('/user/credits', headers=_auth(token_a)).get_json()['data']['balance']
        bal_b = client.get('/user/credits', headers=_auth(token_b)).get_json()['data']['balance']
        assert bal_a == 80
        assert bal_b == 100  # B 不受影响

    def test_pagination(self, client):
        """流水分页"""
        _register(client)
        token = _login(client)
        # 触发多次交易: 生成成功不退款产生 1 条 AI 交易
        client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': '任务1'},
                    headers=_auth(token))
        client.post('/ai/generate-3d', json={'task_type': 'text_to_3d', 'prompt': '任务2'},
                    headers=_auth(token))

        r = client.get('/user/credits?per_page=2', headers=_auth(token))
        body = r.get_json()
        assert body['meta']['pagination']['total'] == 3  # 充值 + 2 次 AI
        assert len(body['data']['transactions']) == 2
        assert body['data']['balance'] == 60