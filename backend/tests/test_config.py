# ============================================================
# 智绘锡承 - 配置加载测试
# ============================================================
import pytest


class TestConfig:
    """配置管理测试"""

    def test_development_config(self):
        """开发配置默认值"""
        from config import config

        dev = config['development']
        assert dev.DEBUG is True
        assert dev.SQLALCHEMY_TRACK_MODIFICATIONS is False
        assert 'mysql+pymysql://' in dev.SQLALCHEMY_DATABASE_URI
        assert dev.JWT_ACCESS_TOKEN_EXPIRES is not None
        assert 'jwt' in dev.JWT_SECRET_KEY.lower()  # 占位值，非真实密钥

    def test_testing_config(self):
        """测试配置使用 SQLite 内存库"""
        from config import config

        test_cfg = config['testing']
        assert test_cfg.TESTING is True
        assert test_cfg.SQLALCHEMY_DATABASE_URI.startswith('sqlite://')

    def test_production_config(self):
        """生产配置关闭调试"""
        from config import config

        prod = config['production']
        assert prod.DEBUG is False

    def test_config_has_env_sensitive_keys(self):
        """敏感配置键必须存在（值来自环境变量，模板勿填真实值）"""
        from config import Config

        assert hasattr(Config, 'JWT_SECRET_KEY')
        assert hasattr(Config, 'TENCENT_HUNYUAN_API_KEY')
        assert hasattr(Config, 'TENCENT_HUNYUAN_SECRET_KEY')
        assert hasattr(Config, 'TENCENT_TBAAS_API_KEY')
