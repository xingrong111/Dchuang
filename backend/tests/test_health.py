# ============================================================
# 智绘锡承 - 健康检查接口测试
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


class TestHealth:
    """GET /health 健康检查"""

    def test_health_ok(self, client):
        """返回统一成功响应"""
        resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['code'] == 200
        assert data['message'] == 'Backend service is running'
        assert data['data'] == {'status': 'healthy'}
        assert 'timestamp' in data

    def test_health_method_not_allowed(self, client):
        """POST 不允许（405 统一 JSON）"""
        resp = client.post('/health')
        assert resp.status_code == 405
        data = resp.get_json()
        assert data['code'] == 405
        assert data['data'] is None
