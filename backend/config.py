# ============================================================
# 智绘锡承 - 后端配置管理
# 位置: backend/config.py（依据《项目开发规范文档 v1.0》4.1.2）
# 所有敏感配置必须来自环境变量（.env 或系统环境），严禁硬编码真实密钥
# ============================================================
import os
from datetime import timedelta
from dotenv import load_dotenv

# 加载 backend/.env（若存在）。python-dotenv 不会覆盖已存在的系统环境变量
load_dotenv()


class Config:
    """基础配置（所有环境共享）"""

    # --- Flask 基础 ---
    APP_NAME = os.getenv('APP_NAME', '智绘锡承')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    API_VERSION = os.getenv('API_VERSION', 'v1')
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = False
    TESTING = False

    # --- 数据库（MySQL 8.0，规范 1.2/4.1.2） ---
    # 优先使用完整连接串 DATABASE_URL；未设置时由 DB_* 拼接
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4'.format(
            user=os.getenv('DB_USER', 'nih_dev'),
            password=os.getenv('DB_PASSWORD', ''),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '3306'),
            name=os.getenv('DB_NAME', 'nih_platform'),
        )
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '3600')),
        'pool_pre_ping': True,
    }

    # --- Redis（缓存/限流，阶段3 起使用，本阶段仅预留配置） ---
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # --- JWT（阶段3 实现，规范 4.1.2；JWT_SECRET_KEY 勿填真实值） ---
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'

    # --- Flask Session（阶段5.1：兼容 el-upload 的 Cookie 认证） ---
    # 安全基线: HttpOnly + SameSite=Lax（防止 XSS 读取 / CSRF 跨站携带）
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    # 开发/测试走 HTTP 本地环境，Secure 默认 False；生产环境强制 True（见 ProductionConfig）
    SESSION_COOKIE_SECURE = False
    # Session 有效期（与 JWT 24h 对齐）
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # --- 文件上传（阶段5 使用，规范 4.1.2） ---
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'glb', 'gltf', 'obj', 'stl'}

    # --- 大模型 API（阶段6-9 使用） ---
    # AI Provider 选择: mock | hunyuan | glm（显式指定；默认 mock 用于开发/测试）
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'mock')
    TENCENT_HUNYUAN_API_KEY = os.getenv('TENCENT_HUNYUAN_API_KEY', '')
    TENCENT_HUNYUAN_SECRET_KEY = os.getenv('TENCENT_HUNYUAN_SECRET_KEY', '')
    TENCENT_HUNYUAN_BASE_URL = os.getenv(
        'TENCENT_HUNYUAN_BASE_URL', 'https://hunyuan.tencent.com/api/v1'
    )
    # GLM 多模态（阶段9 预留配置，真实接入时需提供 Key）
    GLM_API_KEY = os.getenv('GLM_API_KEY', '')
    GLM_BASE_URL = os.getenv('GLM_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')

    # --- 区块链（阶段10 使用，本阶段仅预留配置） ---
    TENCENT_TBAAS_API_KEY = os.getenv('TENCENT_TBAAS_API_KEY', '')
    TENCENT_TBAAS_BASE_URL = os.getenv('TENCENT_TBAAS_BASE_URL', '')

    # --- CORS ---
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')

    # --- 限流（规范 4.1.2，阶段3 起启用） ---
    RATELIMIT_DEFAULT = os.getenv('RATELIMIT_DEFAULT', '100 per minute')
    RATELIMIT_STORAGE_URL = REDIS_URL


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """测试环境配置（使用 SQLite 内存库，无需 MySQL）"""
    TESTING = True
    # 测试不依赖 MySQL：SQLite 内存数据库
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'TEST_DATABASE_URL', 'sqlite:///:memory:'
    )
    # SQLite StaticPool 不接受 pool_size/pool_recycle 等连接池参数，需清空
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    # 生产环境必须显式提供以下变量（缺失时留空，启动阶段应校验）
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_ECHO = False
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '').split(',')
    # 生产环境 HTTPS: Session Cookie 必须 Secure
    SESSION_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
