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
    # 腾讯混元生3D（阶段12-B: AI3D 产品真实接入，SDK 封装）
    # 凭据来自腾讯云控制台-CAM 访问管理（SecretId/SecretKey 成对），仅存 .env（gitignored）
    TENCENT_SECRET_ID = os.getenv('TENCENT_SECRET_ID', '')
    TENCENT_SECRET_KEY = os.getenv('TENCENT_SECRET_KEY', '')
    # AI3D 服务地域与产品 endpoint（SDK 默认按产品生成，一般无需覆盖）
    TENCENT_HUNYUAN_REGION = os.getenv('TENCENT_HUNYUAN_REGION', 'ap-guangzhou')
    TENCENT_HUNYUAN_ENDPOINT = os.getenv('TENCENT_HUNYUAN_ENDPOINT', '')
    # 生3D 模型名（按开通产品配置，如 hunyuan3d 系列；留空使用服务端默认）
    HUNYUAN_3D_MODEL = os.getenv('HUNYUAN_3D_MODEL', '')
    # AI 异步任务超时（秒，默认 30 分钟；RUNNING 超时未终态 → FAILED，阶段13-B3）
    AI_TASK_TIMEOUT_SECONDS = int(os.getenv('AI_TASK_TIMEOUT_SECONDS', '1800'))
    # AI 积分消耗规则（阶段15-B: 平台积分系统；对应腾讯 3D 生成实际消耗）
    AI_COST_3D_GENERATE = int(os.getenv('AI_COST_3D_GENERATE', '20'))
    AI_COST_STYLE_ANALYZE = int(os.getenv('AI_COST_STYLE_ANALYZE', '5'))
    # AI 后台任务 Worker（阶段15-C）: 默认关闭（开发/测试不自动启动，避免多 Worker）
    AI_WORKER_ENABLED = os.getenv('AI_WORKER_ENABLED', 'false').strip().lower() in ('1', 'true', 'yes')
    AI_WORKER_INTERVAL_SECONDS = int(os.getenv('AI_WORKER_INTERVAL_SECONDS', '30'))
    # 后台管理员用户 ID（阶段16-A: 配置式，逗号分隔，如 '1,2'；不新增 User 角色字段）
    ADMIN_USER_IDS = os.getenv('ADMIN_USER_IDS', '')
    # GLM 多模态（阶段9 预留配置，真实接入时需提供 Key）
    GLM_API_KEY = os.getenv('GLM_API_KEY', '')
    GLM_BASE_URL = os.getenv('GLM_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
    # GLM 视觉模型（阶段11-A: 默认 glm-4v-flash 免费模型）
    GLM_MODEL = os.getenv('GLM_MODEL', 'glm-4v-flash')
    # GLM HTTP 请求超时（秒）
    GLM_TIMEOUT = int(os.getenv('GLM_TIMEOUT', '30'))
    # GLM 图片最大字节数（默认 10MB，防超大图片内存占用）
    GLM_MAX_IMAGE_SIZE = int(os.getenv('GLM_MAX_IMAGE_SIZE', '10485760'))

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
