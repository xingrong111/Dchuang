# 智绘锡承 - 后端服务 (B_houduan)

基于 **Python + Flask** 的非遗 3D 模型生成平台后端。

## 技术栈

| 组件 | 选型 | 依据 |
|---|---|---|
| 语言 | Python 3.9+（本机开发环境 3.13.14） | 规范文档 1.3.2 |
| Web 框架 | Flask 3.x | 规范文档 1.2 / 4.1 |
| ORM | Flask-SQLAlchemy (SQLAlchemy 2.x) | 规范文档 4.1.1 |
| 数据库 | MySQL 8.0（开发无 MySQL 时测试用 SQLite） | 规范文档 1.2 / 1.3.3 |
| 迁移 | Flask-Migrate | 规范文档 4.1.1 |
| 跨域 | Flask-CORS | 规范文档 4.1.1 |
| 认证 | JWT（阶段3 实现） | 规范文档 4.1.2 |

## 目录结构

```
backend/
├── app/
│   ├── __init__.py          # Flask 应用工厂
│   ├── extensions.py        # SQLAlchemy / Migrate / CORS 扩展
│   ├── api/                 # API 蓝图（v1）
│   │   └── v1/health.py     # GET /health 健康检查
│   ├── models/              # 数据模型（user.py: User/UserProfile）
│   ├── services/            # 业务服务层（占位）
│   ├── utils/               # response.py 统一响应 / exceptions.py 错误处理
│   └── static/              # 静态文件（uploads/ models/）
├── migrations/              # Flask-Migrate 迁移（需 MySQL 环境生成）
├── tests/                   # pytest 测试
├── config.py                # 配置管理（环境变量驱动）
├── run.py                   # 应用入口
├── requirements.txt
└── .env.example             # 环境变量模板（复制为 .env 使用）
```

## 快速开始

```bash
cd backend

# 1. 创建虚拟环境并安装依赖
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. 配置环境变量（复制模板并填写真实值，.env 已加入 .gitignore）
copy .env.example .env       # Windows

# 3. 启动服务（默认端口 8000，与前端 Vite 代理一致）
python run.py

# 4. 健康检查
curl http://localhost:8000/health
# => {"code":200,"message":"Backend service is running","data":{"status":"healthy"},...}
```

## 数据库（MySQL）

本机未安装 MySQL 时，开发启动不会真实连接数据库（health 接口不依赖数据库）；
测试环境自动使用 SQLite 内存库，无需 MySQL 即可运行 `pytest`。

有 MySQL 环境后：

```bash
# 先按 .env.example 填写 DATABASE_URL（或 DB_* 变量）
flask db init      # 首次初始化迁移目录
flask db migrate -m "init user tables"
flask db upgrade   # 应用迁移，创建 users / user_profiles 表
```

## 测试

```bash
cd backend
python -m pytest tests/ -v
```

## 接口前缀约定（重要）

前端 Vite 开发代理（`frontend/vite.config.js`）会把请求的 `/api` 前缀剥除后转发到
`http://localhost:8000`，因此**后端蓝图不挂 `/api/v1` 前缀**，接口直接以
`/health`、`/auth/login` 等路径注册，与 A_qianduan 前端 axios 调用保持一致
（详见《智绘锡承项目现状与B同学后端开发实施计划》第 4.4 节）。
