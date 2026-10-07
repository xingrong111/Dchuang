# 智绘锡承 - 前后端联调执行清单

> 后端基线：`B_houduan@f47de53`；前端盘点快照：`origin/A_qianduan@1f46e66`。
> 本文只说明执行顺序和验收方法。接口字段见 [`API_CONTRACT.md`](./API_CONTRACT.md)，前端改造说明见 [`FRONTEND_HANDOFF.md`](./FRONTEND_HANDOFF.md)。

## 0. 使用方式

状态统一填写：`未开始` / `进行中` / `通过` / `失败`。失败时记录 HTTP 状态、响应 `message`、task_id、复现步骤；禁止记录 Key、Token、Cookie、Authorization、数据库密码或图片 Base64。

联调建议顺序：

`环境 → Auth → Upload → Credits → Community → GLM → Hunyuan 3D → Profile → Admin → 完整回归`

涉及真实 AI 时必须使用受控测试账号、确认余额与 Provider 配置，并避免重复提交。

## 1. 环境

### 后端

- [ ] `DATABASE_URL` 指向联调数据库，不是生产库。
- [ ] `flask db current` 为 `f6a7b8c9d0e1`。
- [ ] `python scripts/check_database.py` 的连接、revision 和核心表均通过。
- [ ] `SECRET_KEY`、`JWT_SECRET_KEY` 已配置，前端不可获取这些值。
- [ ] `AI_PROVIDER` 与本轮要验收的能力一致。
- [ ] 异步 3D 联调时单独启动 Worker；不需要时保持 `AI_WORKER_ENABLED=false`。
- [ ] `GET http://localhost:8000/health` 返回 200。
- [ ] `GET http://localhost:8000/health/ready` 返回 200。

Worker 启动方式以部署配置为准，开发环境可运行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.workers.ai_task_worker
```

### 前端

- [ ] 使用 A 同学前端分支，不在 `B_houduan` 中寻找 `frontend/`。
- [ ] Vite 的 API base 为 `/api`。
- [ ] 开发代理将 `/api` 转发到 `http://localhost:8000` 并剥除前缀。
- [ ] 浏览器 Network 中后端请求没有错误的双重 `/api/api`。
- [ ] axios 超时对 3D 轮询合理；创建请求本身不做隐式重试。

## 2. Auth 联调

| 状态 | 操作 | 前端请求 | 验收标准 |
|---|---|---|---|
| 未开始 | 注册 | `POST /api/auth/register` | 200；返回用户；不返回 token；初始积分账户创建 |
| 未开始 | 登录 | `POST /api/auth/login` | 200；读取 `data.token`；用户信息正确 |
| 未开始 | 当前用户 | `GET /api/auth/user` | Bearer 有效时 200 |
| 未开始 | 未登录访问 | `GET /api/auth/user` | 401；前端清理状态并跳登录 |
| 未开始 | 刷新用户信息 | 同上 | 刷新后原 JWT 仍被保留，后续请求继续带 Bearer |
| 未开始 | 本地退出 | 无后端 logout | 清除 token/用户缓存并回登录页，不请求不存在的 `/auth/logout` |

## 3. Upload 联调

| 状态 | 操作 | 请求 | 验收标准 |
|---|---|---|---|
| 未开始 | 上传图片 | `POST /api/workshop/upload` multipart `file` | 200；`data.url` 位于 `/api/static/uploads/images/` |
| 未开始 | 上传 GLB | 同上 | 200；URL 位于 `/api/static/uploads/models/` |
| 未开始 | 上传头像 | `POST /api/user/upload-avatar` | 200；用户头像更新 |
| 未开始 | 访问文件 | `GET data.url` | 浏览器 200，可显示/下载 |
| 未开始 | 未认证上传 | 上传接口 | 401 |
| 未开始 | 非法扩展/魔数 | 上传接口 | 400，不生成可访问文件 |
| 未开始 | 超大请求 | 上传接口 | 413 |

同源 Vite 代理可使用 Session Cookie；跨域部署必须配置 `withCredentials`，或为上传显式附加 Bearer。

## 4. Credits 联调

- [ ] `GET /api/user/credits` 返回 `data.balance`、`data.transactions` 和 `meta.pagination`。
- [ ] 正数流水显示为入账，负数显示为消费。
- [ ] AI 成功后刷新余额与流水。
- [ ] AI 失败后能看到消费和 `REFUND`，最终余额恢复。
- [ ] 余额不足时 AI 创建返回 402，前端不进入轮询，也不伪造 task。
- [ ] 402、503 与普通 400 使用不同提示；任何付费请求都不自动 retry。

## 5. AI analyze-style

流程：

`上传图片 → 获得 input_url → POST /api/ai/analyze-style → 展示 style/features/report 或安全错误 → 刷新 credits`

- [ ] body 为 `{input_url, artwork_id?}`，URL 直接使用上传响应值。
- [ ] 成功：HTTP 200、task 为 `SUCCESS`、`error_message=null`，展示真实分析结果。
- [ ] 失败：HTTP 503、AITask 为 `FAILED`、积分自动退款。
- [ ] Provider 非 200 时可安全显示 HTTP/code/message/request_id；不显示完整响应、Key 或请求体。
- [ ] 外部模型可能临时过载；`1305` 是平台过载，不应写死为产品固定状态。
- [ ] 不自动 retry。用户明确再次提交前，应提示可能产生新的积分流水。
- [ ] 风格分析失败不调用 3D retry 接口；需要重试时重新提交 analyze-style。

## 6. AI generate-3d

### 文生 3D

- [ ] `POST /api/ai/generate-3d` body：`{task_type:'text_to_3d', prompt}`。
- [ ] 返回 task 的 provider/model/status 与后端配置一致。

### 图生 3D

- [ ] 先上传图片。
- [ ] 创建 body：`{task_type:'image_to_3d', input_url}`。
- [ ] input_url 不是本站上传路径时前端能展示 400。

### 轮询

- [ ] 保存返回的 `data.id` 作为 task_id。
- [ ] `PENDING/RUNNING` 时定时 `GET /api/ai/tasks/{id}`。
- [ ] 同一 task 同时只保留一个轮询器；页面卸载或进入终态后清理 timer。
- [ ] `SUCCESS` 时停止轮询，读取 `artwork_id` 并查询作品详情。
- [ ] `FAILED` 时停止轮询，展示 `error_message` 并刷新积分。
- [ ] 网络错误采用用户可见的手动恢复，不重复 POST generate。
- [ ] 同输入已有 RUNNING 时后端可能返回原 task；前端按 task id 去重。

### Worker

- [ ] Worker 开启时能自动扫描 RUNNING 任务。
- [ ] Worker 日志不含 Secret。
- [ ] Worker 停止后，任务详情 GET 仍可对 RUNNING+JobId 做一次状态刷新。
- [ ] SUCCESS 后 GLB 已本地持久化或安全回退，Artwork 已创建。

## 7. Community / Artwork

| 状态 | 流程 | 请求 | 验收标准 |
|---|---|---|---|
| 未开始 | 列表 | `GET /api/workshop/works` | 使用 `data[]` 和 `meta.pagination`；字段映射 `like_count/comment_count/collect_count` |
| 未开始 | 详情 | `GET /api/workshop/works/{id}` | 显示作者、统计、`current_user_status`；浏览量增加 |
| 未开始 | 发布 | upload → `POST /api/workshop/save` | JSON 保存；不要向不存在的 `/community/works` 发 multipart |
| 未开始 | 点赞/取消 | `POST/DELETE .../{id}/like` | 使用返回的 `liked` 和 `like_count` 更新 UI |
| 未开始 | 收藏/取消 | `POST/DELETE .../{id}/collect` | 使用 `collected` 和 `collect_count` |
| 未开始 | 评论列表 | `GET .../{id}/comments` | 分页、作者字段正确 |
| 未开始 | 评论/删评 | `POST .../comments` / `DELETE /api/comments/{id}` | 真实持久化；403 正确处理 |
| 未开始 | 编辑/删除作品 | `PUT/DELETE /api/workshop/works/{id}` | 仅作者显示入口；非作者 403 |

注意：后端只支持 `sort=latest`。A 分支当前的搜索、分类、popular/comments 排序应暂时前端处理或隐藏，不要当作后端查询参数。

## 8. Profile

- [ ] `GET /api/auth/user` 显示真实用户资料，且不覆盖丢失 token。
- [ ] `GET /api/user/credits` 显示余额和流水。
- [ ] `GET /api/ai/history` 显示任务及关联 artwork。
- [ ] `GET /api/ai/tasks/statistics` 显示 AI 汇总。
- [ ] `GET /api/workshop/works?author_id=<current_user_id>` 显示本人公开作品。
- [ ] 头像上传后立即更新 store 与页面。
- [ ] 当前后端没有资料编辑、密码修改、订单和“我的收藏列表”接口；对应 Mock 必须明确标记、隐藏或留作后续需求，不能宣称已联调。

## 9. Admin

准备一个 ID 位于 `ADMIN_USER_IDS` 的测试账号，以及一个普通账号。

- [ ] 普通账号访问 `/api/admin/*` 返回 403。
- [ ] 管理员能读取用户、AI、积分、趋势、模型成本和排行统计。
- [ ] 任务列表支持 status/provider/pagination；详情含用户、积分流水和作品。
- [ ] Provider 列表、创建、更新、启停、usage 和 status 均可展示。
- [ ] 停用 Provider 后新调用返回 503；已有 RUNNING 任务仍可收口。
- [ ] Admin retry 仅在人工确认后触发，防止重复成本。
- [ ] CSV 导出使用文件下载响应，不按 JSON 解析。
- [ ] 管理写操作后能在 `/api/admin/logs` 查到审计记录。

## 10. Model display

- [ ] 从 Artwork 详情读取 `model_url`，示例 `/api/static/uploads/models/<uuid>.glb`。
- [ ] 使用 `GLTFLoader`，不要用占位立方体代表成功结果。
- [ ] loader 直接使用 API URL，不拼接 Windows/服务器磁盘路径。
- [ ] 显示加载中、加载失败和空模型状态。
- [ ] 加载成功后根据 bounding box 调整相机和 OrbitControls target。
- [ ] 替换模型或卸载页面时释放 geometry、material、texture 和 renderer。
- [ ] 404、跨域、GLB 解析失败分别可诊断。

## 11. 错误码验收

| code | 前端动作 |
|---:|---|
| 400 | 展示后端 `message`，定位字段或非法状态 |
| 401 | 清除登录态并跳转登录；避免循环弹窗 |
| 402 | 提示积分不足，不创建轮询器 |
| 403 | 提示无权限，并隐藏作者/管理员操作 |
| 404 | 显示资源不存在；停止对应轮询 |
| 405 | 视为前端 method/path 缺陷，记录并修复 |
| 413 | 提示文件超过限制 |
| 500 | 通用服务异常，不展示堆栈 |
| 503 | 展示安全 Provider 消息，刷新任务/积分，不自动 retry |

## 12. 页面/API 映射验收

| 页面 | 必须接入 |
|---|---|
| Login/Register | register、login、auth/user |
| AI Workshop | upload、generate-3d、task polling、analyze-style、retry（仅3D） |
| Community | works list/detail/save、like、collect、comments |
| Profile | auth/user、credits、AI history/statistics、author works、avatar upload |
| Admin | statistics、tasks、providers、logs、CSV export |
| 3D Preview | Artwork model_url + GLTFLoader |

## 13. 推荐联调顺序

1. 后端 ready 与 Vite proxy。
2. 注册、登录、JWT 保持。
3. 图片/头像/GLB 上传及静态访问。
4. Credits 初始余额。
5. Workshop 保存、列表、详情。
6. 点赞、收藏、评论。
7. GLM analyze-style（需要明确真实调用授权）。
8. Hunyuan text-to-3D，再做 image-to-3D（分别受控授权）。
9. Worker、任务轮询、Artwork 和 GLB 展示。
10. Profile 聚合。
11. Admin 权限与运营接口。
12. 失败路径、退款和完整回归。

## 14. 最终完整流程

- [ ] 注册 → 登录 → token 持久化。
- [ ] 上传图片 → 静态 URL 可访问。
- [ ] AI 分析或生成 → task 状态真实变化。
- [ ] RUNNING → SUCCESS/FAILED 终态，不产生僵尸任务。
- [ ] SUCCESS → Artwork → Community 详情 → GLB 展示。
- [ ] Like / Comment / Collect 持久化且刷新后仍存在。
- [ ] Profile 显示作品、任务和积分。
- [ ] Admin 能看到任务、成本、Provider 和审计记录。
- [ ] 失败调用退款正确，前端没有自动重复付费请求。

## 15. 验收总表

| 模块 | 状态 | 验收人 | 日期 | 失败记录/备注 |
|---|---|---|---|---|
| 环境与代理 | 未开始 |  |  |  |
| Auth | 未开始 |  |  |  |
| Upload | 未开始 |  |  |  |
| Credits | 未开始 |  |  |  |
| Artwork/Community | 未开始 |  |  |  |
| GLM analyze-style | 未开始 |  |  |  |
| Hunyuan 3D | 未开始 |  |  |  |
| Worker/轮询 | 未开始 |  |  |  |
| GLB/Three.js | 未开始 |  |  |  |
| Profile | 未开始 |  |  |  |
| Admin | 未开始 |  |  |  |
| 错误与退款 | 未开始 |  |  |  |
| 完整 E2E | 未开始 |  |  |  |

## 16. 前端必须修改项

### P0

- 修复 `userStore.fetchUserInfo()` 覆盖并丢失 JWT。
- 将 AI 生成从本地动画/`/workshop/generate` 切换为 generate-3d + task polling。
- 将 Community 从本地数组和 `/community/*` 切换为 Workshop/Comments 实际接口。
- 增加 `GLTFLoader`，从 Artwork 的 `model_url` 加载真实 GLB。
- 接入 credits，并正确处理 402、失败退款和 503。

### P1

- 接入 analyze-style、AI history/statistics、3D retry。
- 接入收藏、评论列表/删除、作品编辑/删除和 `current_user_status`。
- 用真实作者作品替换 Profile Mock；对后端未提供的数据区块明确降级。
- 新增 Admin API 封装与页面，或在本轮范围不含后台 UI 时明确延期。

### P2

- 完善分页、空态、骨架屏、轮询退避与组件资源释放。
- Museum、Shop、订单、语音和零件编辑等无后端契约模块继续保持明确的演示/纯前端标签。
