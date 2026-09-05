# 智绘锡承 Backend

“智绘锡承”是一个面向数字文化作品展示与创作的 Web 项目。本目录提供 Flask 后端，覆盖用户认证、作品社区、文件上传、AI 多模态分析、AI 3D 生成、异步任务、积分和后台运营管理。

前端由 `A_qianduan` 分支独立维护；本 README 只描述后端及其联调边界。

## 1. 当前状态

- 后端核心功能已完成，当前处于最终交付与前后端联调阶段。
- 当前代码注册 46 个 HTTP Method + Route 组合（39 个去重 URL）。
- 数据库包含 11 张核心业务表，Alembic 为 10 个 revision 的单链，当前 head 为 `f6a7b8c9d0e1`。
- Migration 已完成 SQLite 与 MySQL 8.4.9 的空库升级验收。
- 当前全量测试基线为 438 passed；提交前应重新运行测试确认。

## 2. 技术栈

- Python 3.9+
- Flask 3.x
- Flask-SQLAlchemy / SQLAlchemy 2.x
- Flask-Migrate / Alembic
- MySQL 8（测试默认使用 SQLite）
- Flask-JWT-Extended + Flask Session
- Flask-CORS
- pytest
- requests（GLM HTTP API）
- Tencent Cloud Python SDK（混元 AI3D）

## 3. 功能模块

### Auth

用户注册、登录和当前用户查询。登录签发 JWT，同时建立 Flask Session；普通 API 主要使用 Bearer Token，上传接口兼容 JWT 与 Session。注册时初始化积分账户。

### Artwork / Workshop 与 Community

- 作品创建、列表、详情、更新和删除。
- 支持公开/私有、作者与 AI 作品过滤、分页和互动计数。
- 点赞/取消、收藏/取消、评论列表、发表评论和作者删除评论。

### AI

- GLM 多模态图片风格分析。
- 腾讯混元文生 3D、图生 3D。
- AI 任务列表、详情、历史、统计和失败任务重试。
- Provider 运行时启停、动态成本及任务治理。

### Credits

注册默认赠送积分；AI 请求创建时预扣，失败自动退款；流水以 `reference_id` 做幂等保护。Provider 的 `cost_config` 可以覆盖环境变量默认成本。

### Admin

管理员由 `ADMIN_USER_IDS` 配置。后台 API 覆盖用户、AI、积分、趋势与成本统计，任务管理，Provider 管理，用量与状态，审计日志和 CSV 导出；当前没有 RBAC 模型。

### Upload / Static 与 Health

- 上传图片、头像和 3D 模型，使用扩展名、内容特征与大小限制校验并以 UUID 保存。
- 腾讯 COS 临时模型地址会尝试安全转存本地，失败时保留原地址作为 fallback。
- `GET /health` 提供存活检查；`GET /health/ready` 检查数据库及生产关键配置。

## 4. 系统架构

```text
Vue / Vite Frontend
        │  /api/*（开发代理移除 /api）
        ▼
Flask API / Auth / Validation
        │
        ├── SQLAlchemy ── MySQL / SQLite
        ├── Service Layer ── Credits / AI Task / Files
        └── AI Provider Factory
                 ├── MockProvider
                 ├── GLMService
                 └── HunyuanService ── Tencent AI3D
                                      │
                                      ▼
                               AI Task Worker
                                      │
                                      ▼
                              GLB + Artwork 回填
```

## 5. 目录结构

```text
backend/
├── app/
│   ├── api/v1/                  # auth、user、upload、artwork、ai、admin、health
│   ├── models/                  # 11 个领域模型
│   ├── services/                # Provider、任务、积分与 AI3D SDK 适配
│   ├── workers/                 # AI 异步任务 Worker
│   ├── utils/                   # 认证、响应、异常、文件与状态工具
│   ├── static/uploads/          # images、avatars、models 运行时文件
│   ├── __init__.py              # Flask 应用工厂
│   └── extensions.py            # DB、Migrate、CORS、JWT
├── docs/
│   ├── API_CONTRACT.md          # 完整 API 契约
│   ├── FRONTEND_HANDOFF.md      # 前端接入说明
│   └── INTEGRATION_CHECKLIST.md # 联调执行清单
├── migrations/versions/         # 10 个 Alembic revision
├── scripts/check_database.py    # 只读数据库与 migration 检查
├── tests/                       # pytest 测试
├── config.py                    # development/testing/production 配置
├── run.py                       # 应用入口及可选 Worker 线程
├── requirements.txt
└── .env.example                 # 环境变量模板
```

## 6. 快速开始（Windows PowerShell）

### 环境要求

- Python 3.9+
- MySQL 8（正式开发/部署数据库）
- 前端联调时默认使用端口 8000

### 创建环境并安装依赖

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 配置环境变量

```powershell
Copy-Item .env.example .env
```

编辑 `.env` 并填入当前环境的值。`.env` 包含敏感信息，不得提交到 Git。开发环境可使用：

```dotenv
FLASK_CONFIG=development
AI_PROVIDER=mock
AI_WORKER_ENABLED=false
```

生产环境必须显式设置：

```dotenv
FLASK_CONFIG=production
SECRET_KEY=<long-random-secret>
JWT_SECRET_KEY=<another-long-random-secret>
DATABASE_URL=mysql+pymysql://<user>:<password>@<host>:3306/<database>?charset=utf8mb4
CORS_ORIGINS=https://<frontend-origin>
```

示例只表示格式，不可直接用于真实环境。全部配置项以 [`.env.example`](./.env.example) 为准。

### 初始化或升级数据库

确保 `DATABASE_URL` 指向目标数据库，然后执行：

```powershell
flask db heads
flask db upgrade
python scripts/check_database.py
```

仓库已包含完整 migration 目录，不要再次执行 `flask db init`，也不要用 `db.create_all()` 代替正式 migration。

### 启动后端

`run.py` 通过 `FLASK_CONFIG` 环境变量选择配置：

```powershell
$env:FLASK_CONFIG = "development"
python run.py
```

默认监听 `0.0.0.0:8000`，可通过 `PORT` 修改。`python run.py production` 不是当前实现支持的配置选择方式，位置参数会被忽略。

## 7. 关键环境变量

| 类别 | 变量 | 说明 |
|---|---|---|
| 运行 | `FLASK_CONFIG`、`PORT` | 配置环境和监听端口 |
| 安全 | `SECRET_KEY`、`JWT_SECRET_KEY` | 生产环境必须显式设置 |
| 数据库 | `DATABASE_URL` | production 必填，优先于开发环境的 `DB_*` fallback |
| CORS | `CORS_ORIGINS` | 多个 Origin 使用英文逗号分隔 |
| Provider | `AI_PROVIDER` | `mock`、`glm` 或 `hunyuan` |
| GLM | `GLM_API_KEY`、`GLM_BASE_URL`、`GLM_MODEL`、`GLM_TIMEOUT`、`GLM_MAX_IMAGE_SIZE` | 风格分析配置 |
| Hunyuan | `TENCENT_SECRET_ID`、`TENCENT_SECRET_KEY`、`TENCENT_HUNYUAN_REGION`、`TENCENT_HUNYUAN_ENDPOINT`、`HUNYUAN_3D_MODEL` | 腾讯 AI3D 配置 |
| Task | `AI_TASK_TIMEOUT_SECONDS` | RUNNING 任务超时，默认 1800 秒 |
| Worker | `AI_WORKER_ENABLED`、`AI_WORKER_INTERVAL_SECONDS` | 默认关闭；间隔默认 30 秒 |
| Credits | `AI_COST_3D_GENERATE`、`AI_COST_STYLE_ANALYZE` | 默认成本分别为 20、5 |
| Admin | `ADMIN_USER_IDS` | 管理员用户 ID，英文逗号分隔 |

`TENCENT_HUNYUAN_API_KEY`、`TENCENT_HUNYUAN_SECRET_KEY` 和 `TENCENT_HUNYUAN_BASE_URL` 是历史兼容字段，当前 AI3D SDK 使用 `TENCENT_SECRET_ID` / `TENCENT_SECRET_KEY`。

## 8. 数据库与 Migration

当前共有 11 个模型和对应业务表：

| 模型 | 表 |
|---|---|
| `User` | `users` |
| `UserProfile` | `user_profiles` |
| `Artwork` | `artworks` |
| `AITask` | `ai_tasks` |
| `Like` | `artwork_likes` |
| `Comment` | `artwork_comments` |
| `Collection` | `artwork_collections` |
| `CreditAccount` | `credit_accounts` |
| `CreditTransaction` | `credit_transactions` |
| `AdminLog` | `admin_logs` |
| `AIProviderConfig` | `ai_providers` |

关键关系包括用户与资料的一对一、用户与作品/任务的一对多、作品互动唯一约束，以及作品删除时互动级联、任务 `artwork_id` 置空。

Migration 当前为 10 个 revision 的单链，head 是 `f6a7b8c9d0e1`。部署前可执行：

```powershell
flask db current
flask db heads
python scripts/check_database.py
```

检查脚本只执行连接、metadata 和版本查询，不执行 DDL。

## 9. AI Provider 与任务

Provider 工厂支持：

- `mock`：开发、测试和演示使用，不调用第三方。
- `glm`：承担多模态风格分析，不支持 3D 生成。
- `hunyuan`：承担腾讯混元文生 3D 和图生 3D，不承担风格分析。

`AI_PROVIDER` 是新请求的全局 Provider 选择，不代表多个 Provider 会自动同时工作。内部任务刷新或管理重试可以按任务保存的 Provider 显式选择；`AIProviderConfig.enabled=false` 会阻止该 Provider 的新调用。真实 Provider 缺少凭据时会明确报错，不会静默降级为 Mock。

当前接口使用边界：

- `POST /ai/analyze-style` 前应选择 `AI_PROVIDER=glm`。
- `POST /ai/generate-3d` 前应选择 `AI_PROVIDER=hunyuan`。
- 不调用第三方的本地流程测试可选择 `AI_PROVIDER=mock`。

AI 任务状态机：

```text
PENDING → RUNNING → SUCCESS
                  └→ FAILED
```

任务保存 Provider、模型、任务类型、第三方 `external_task_id`、结果 URL、错误和关联 Artwork。超时任务进入 FAILED；失败任务可按接口约束创建新任务重试。3D 成功后 Worker 持久化结果并创建 Artwork，再回填 `artwork_id`。

## 10. Worker

Worker 扫描带第三方 JobId 的 RUNNING 任务，查询腾讯任务状态，并完成 SUCCESS/FAILED、GLB 转存和 Artwork 创建。

默认配置：

```dotenv
AI_WORKER_ENABLED=false
AI_WORKER_INTERVAL_SECONDS=30
AI_TASK_TIMEOUT_SECONDS=1800
```

开发和测试默认关闭，避免意外启动多个 Worker。需要异步 3D 收口时，可在启动应用前临时启用：

```powershell
$env:AI_WORKER_ENABLED = "true"
python run.py
```

此时 `run.py` 在 daemon 线程中启动 Worker，并处理 SIGTERM/SIGINT。多实例部署时应确保任务不会被多个进程重复扫描；这是部署建议，不是当前代码提供的分布式锁能力。

## 11. 积分系统

- 注册默认创建余额为 100 的积分账户及赠送流水。
- AI 3D 默认成本 20，风格分析默认成本 5。
- 创建 AI 任务时预扣；Provider 或执行失败时使用 `REFUND` 流水退款。
- 消费和退款通过 `reference_id` 防止同一任务重复记账。
- `AIProviderConfig.cost_config` 可覆盖环境变量默认成本。
- 余额不足返回 HTTP 402。

积分是站内审计和用量治理机制，不等同于第三方平台的现金余额或 Token 配额。

## 12. 文件上传与模型资源

运行时上传目录为：

```text
app/static/uploads/
├── images/
├── avatars/
└── models/
```

服务器进程必须对该目录拥有写权限。后端返回的资源 URL 已包含前端代理前缀，例如：

```text
/api/static/uploads/models/<uuid>.glb
```

前端应直接使用 API 返回 URL，不要拼接服务器文件系统路径。远程模型下载只允许 HTTPS 和腾讯 COS 白名单域名，并校验响应大小与 GLB 内容。

## 13. API 与前端联调

后端 Blueprint 自身不挂统一 `/api` 前缀。开发环境中，前端 Vite proxy 把浏览器请求的 `/api` 移除后转发给 Flask：

```text
前端：POST /api/ai/generate-3d
                  │ Vite proxy 去掉 /api
                  ▼
后端：POST /ai/generate-3d
```

接口模块包括 Auth、User、Upload、Workshop/Community、AI、Admin 和 Health，共 46 个 Method + Route 组合。

- 完整字段、认证和错误码：[API_CONTRACT.md](./docs/API_CONTRACT.md)
- 前端接入与当前 A 分支差异：[FRONTEND_HANDOFF.md](./docs/FRONTEND_HANDOFF.md)
- 逐项联调与验收顺序：[INTEGRATION_CHECKLIST.md](./docs/INTEGRATION_CHECKLIST.md)

不要调用后端不存在的 `/auth/logout`、`/workshop/generate`、`/workshop/parts` 或 `/community/*` 路由。

## 14. 测试

测试默认使用 `TEST_DATABASE_URL`，未配置时为 SQLite 内存数据库，不依赖 MySQL，也不会调用真实 AI Provider。

```powershell
pytest
pytest -q
pytest tests/test_migration_upgrade.py -q
```

当前交付基线为 438 passed。测试数量会随代码演进变化，应以本次实际输出为准。

## 15. 健康检查与部署检查

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/ready
```

`/health` 用于进程存活判断；`/health/ready` 检查数据库连接、`SECRET_KEY`、`JWT_SECRET_KEY` 和数据库 URI。生产启动前还应执行：

```powershell
python scripts/check_database.py production
```

生产环境至少确认：

- `FLASK_CONFIG=production`。
- `SECRET_KEY`、`JWT_SECRET_KEY` 和 `DATABASE_URL` 已显式配置。
- `CORS_ORIGINS` 是真实前端 Origin，而不是通配符。
- 所选真实 Provider 的凭据完整。
- 上传目录可写。
- Worker 和管理员 ID 符合部署计划。

## 16. 当前边界

- 前端由 `A_qianduan` 分支维护，后端分支不直接修改前端。
- Admin 权限是 `ADMIN_USER_IDS` 配置式权限，不是 RBAC。
- Worker 默认关闭，当前实现不是分布式任务队列。
- AI Provider 依赖第三方账户、权限、额度、限流和平台实时可用性；平台异常不等同于后端逻辑失败。
- Redis、限流与区块链变量目前仅为预留配置，不应描述为已交付功能。
- 后端没有资料编辑、密码修改、订单、商城、博物馆数据、“我的收藏列表”和 parts 接口。
- 搜索、推荐、支付、WebSocket 和新 Provider 不在当前后端范围内。
- `run.py` 使用 Flask 内置服务器；正式公网部署应由部署方选择合适的生产 WSGI/反向代理方案。

## 17. Git 与开发约定

- 不提交 `.env`、API Key、数据库密码、JWT/Session Secret 或第三方响应原文。
- 数据库结构变更必须通过 Alembic migration，并在独立测试数据库验证。
- 不用 `db.create_all()` 代替正式升级。
- 修改后运行相关测试；重要交付运行全量 `pytest` 和 `git diff --check`。
- 后端接口变更同步维护 API 契约与前端交接资料。
- 不自动 `git push`；推送由项目负责人确认后执行。
