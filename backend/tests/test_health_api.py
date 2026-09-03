# ============================================================
# 智绘锡承 - 健康检查接口测试（阶段16-D 交付收口）
# 覆盖:
#   - GET /health: 200（存活探针，status/version/timestamp）
#   - GET /health/ready: 就绪成功 200 {ready:true}
#   - DB 异常 → 503（统一错误体）
#   - 缺少必要配置 → 503
#   - POST /health → 405 统一 JSON
# ============================================================
import pytest


@pytest.fixture
def app():
    """创建测试应用（SQLite 内存库，无需 MySQL）"""
    from app import create_app

    app = create_app('testing')
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestHealthLiveness:
    """GET /health 存活探针"""

    def test_health_200(self, client):
        """存活探针 200：统一成功体 + status/version/timestamp"""
        resp = client.get('/health')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['code'] == 200
        data = body['data']
        assert data['status'] == 'ok'
        assert data['version']  # APP_VERSION 非空
        assert 'timestamp' in data
        assert 'timestamp' in body

    def test_health_method_not_allowed_405(self, client):
        """POST /health → 405 统一 JSON"""
        resp = client.post('/health')
        assert resp.status_code == 405
        body = resp.get_json()
        assert body['code'] == 405
        assert body['data'] is None


class TestHealthReadiness:
    """GET /health/ready 就绪探针"""

    def test_ready_success(self, client):
        """DB 连通 + 必要配置齐全 → 200 {ready:true}"""
        resp = client.get('/health/ready')
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['code'] == 200
        assert body['data'] == {'ready': True}

    def test_ready_db_error_503(self, app, client, monkeypatch):
        """数据库连接失败 → 503 统一错误体（探针不 500）"""
        def _broken_ping():
            raise RuntimeError('connection refused')

        monkeypatch.setattr('app.api.v1.health._db_ping', _broken_ping)
        resp = client.get('/health/ready')
        assert resp.status_code == 503
        body = resp.get_json()
        assert body['code'] == 503
        assert body['data'] is None
        assert '数据库' in body['message']

    def test_ready_missing_config_503(self, app, client):
        """缺少必要配置（JWT_SECRET_KEY 置空）→ 503"""
        app.config['JWT_SECRET_KEY'] = ''
        resp = client.get('/health/ready')
        assert resp.status_code == 503
        body = resp.get_json()
        assert body['code'] == 503
        assert body['data'] is None
        assert 'JWT_SECRET_KEY' in body['message']
