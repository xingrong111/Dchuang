# 智绘锡承 - 后端 API 契约文档（阶段16-D）

> 版本：v1.0（阶段16-D 交付收口）
> 适用范围：后端 `B_houduan` 分支全部真实接口，供前端 A 同学联调与运维部署参考。
> 内容来源：`backend/app/api/v1/*.py` 当前代码，**无虚构接口**。

---

## 0. 通用约定

### 0.1 前缀与代理

- 后端 Flask 蓝图**不带** `/api` 前缀；前端 Vite 开发代理将 `/api` 剥除后转发（`/api/auth/login` → `/auth/login`）。
- 本契约所有 URL 均为**后端实际路径**（即前端需加 `/api` 前缀）。

### 0.2 统一响应体

成功：

```json
{ "code": 200, "message": "success", "data": { }, "timestamp": "2026-09-03T00:00:00.000000" }
```

失败（所有错误码统一）：

```json
{ "code": 4xx, "message": "错误说明", "data": null, "timestamp": "..." }
```

- `code` 与 HTTP 状态码一致；前端以 `response.code === 200` 判断成功。
- 分页接口 `data` 为数组，分页信息在 `meta.pagination`：

```json
{ "code": 200, "message": "...", "data": [ ... ],
  "meta": { "pagination": { "total": 0, "count": 0, "page": 1, "page_size": 10,
            "total_pages": 0, "has_next": false, "has_prev": false } } }
```

### 0.3 认证方式

- **JWT Bearer**：`Authorization: Bearer <token>`（登录返回 `data.token`）。
- **Session Cookie**：登录后服务端同时建立 Flask Session（HttpOnly），`el-upload` 等原生 XHR 可自动携带。
- 受保护接口未认证 → `401`；`get_authenticated_user()` 采用 JWT 优先 + Session 兜底。

### 0.4 错误码表

| code | 含义 | 典型触发 |
|---|---|---|
| 400 | 参数校验失败 | 字段缺失/格式错误/非法状态/重复创建 |
| 401 | 未认证/凭证无效 | 未登录、JWT 过期、密码错误 |
| 402 | 积分不足 | AI 调用余额不足（`CreditInsufficientError`） |
| 403 | 权限不足 | 非资源作者、非管理员 |
| 404 | 资源不存在 | 任务/作品/评论/Provider 不存在（隔离场景不泄露） |
| 405 | 方法不允许 | 路由存在但方法不符 |
| 413 | 请求体过大 | 上传超过 50MB |
| 500 | 服务器内部错误 | 未捕获异常（兜底） |
| 503 | 服务不可用 | AI Provider 停用 / AI 服务异常 |

### 0.5 常见分页参数

- `page`：页码（默认 1）；`per_page`：每页条数（默认见各接口，最大见各接口）。

---

## 1. Auth（认证）

### 1.1 POST /auth/register —— 用户注册

- 权限：公开
- body：
```json
{ "username": "用户3-20字符(字母/数字/中文)", "email": "a@b.com", "password": "至少6位" }
```
- 响应 200：`data` = 用户信息（`{id, username, email, avatar, bio, location, website, level, is_active, is_verified, created_at, updated_at}`）
- 说明：注册自动创建积分账户（赠送 100）；**不自动登录、不返回 token**。
- 错误：400（字段校验/用户名或邮箱已存在）

### 1.2 POST /auth/login —— 登录

- 权限：公开
- body：`{ "email": "...", "password": "..." }`
- 响应 200：`data = {token, id, username, email, avatar, bio, created_at}`；同时写 Session Cookie。
- 错误：400（空字段）；401（`邮箱或密码错误` / `账号已被禁用`——统一文案不泄露用户存在性）

### 1.3 GET /auth/user —— 当前登录用户（profile）

- 权限：登录（JWT `@jwt_required`）
- 响应 200：`data` = 用户信息（含 email，同注册返回结构）
- 错误：401（无效/缺失凭证）

---

## 2. User（用户中心）

### 2.1 GET /user/credits —— 积分余额与流水（阶段15-B）

- 权限：登录
- 参数：`page`（默认1）/ `per_page`（默认10，最大50）
- 响应 200：`data = {balance: int, transactions: [{id, amount, type, description, reference_id, created_at}]}`，分页信息在 `meta`
- `type`：`RECHARGE`（充值/赠送）/ `AI_GENERATE_3D` / `AI_ANALYZE_STYLE` / `REFUND`；`amount` 正=入账，负=消费
- 错误：401

---

## 3. AI（AI 生成与任务）

> 任务状态：`PENDING` → `RUNNING` → `SUCCESS | FAILED`（终态）。
> Provider：`mock | hunyuan | glm`，由 `AI_PROVIDER` 配置或 Provider 治理表决定。

### 3.1 POST /ai/generate-3d —— 创建 3D 生成任务（文生3D/图生3D）

- 权限：登录
- body：
```json
{
  "task_type": "text_to_3d | image_to_3d",
  "prompt": "文生3D必填", "input_url": "图生3D必填(/api/static/uploads/...相对路径)",
  "model": "可选，缺省用 Provider 实际模型"
}
```
- 响应 200：`data = task`（`{id, provider, model, task_type, prompt, input_url, external_task_id, status, result_url, artwork_id, error_message, created_at, updated_at}`）
- 积分：成功后按动态成本扣费（默认 20，可后台调 `cost_config`）；失败/异常自动退款
- 幂等：同用户同类型同输入存在 RUNNING 任务 → 直接返回已有任务
- 错误：400（校验/非法类型/SSRF 拦截 input_url）；401；402（余额不足）；503（Provider 停用/AI 异常）

### 3.2 POST /ai/analyze-style —— AI 风格分析（多模态）

- 权限：登录
- body：
```json
{ "input_url": "/api/static/uploads/images/xxx.png（必填）", "artwork_id": "可选" }
```
- `artwork_id` 规则：不传 → 纯分析；传且属于本人 → 成功后回写 `style_analysis`；不存在 → 404；他人 → 403
- 响应 200：`data = {task: {...}, style, features: [], report: {}}`
- 积分：成功后扣 5（默认，可动态调）；失败自动退款
- 错误：400；401；402；403（他人作品）；404（作品/任务不存在）；503（Provider 停用/AI 异常）

### 3.3 GET /ai/tasks —— 我的任务列表

- 权限：登录（仅本人）
- 参数：`page`（默认1）/ `per_page`（默认10，最大50）
- 响应 200：分页 `data=[task...]`；只读 DB 状态，不逐条触发第三方查询

### 3.4 GET /ai/tasks/<task_id> —— 任务详情

- 权限：登录（仅本人；他人任务/不存在 → 404 不泄露）
- 响应 200：`data = task`
- 说明：真实异步任务（RUNNING + JobId）读取时触发一次轮询刷新（可能推进为 SUCCESS/FAILED）

### 3.5 POST /ai/tasks/<task_id>/retry —— 重试失败任务

- 权限：登录（仅本人）
- 规则：仅 `FAILED` 可重试；`SUCCESS/RUNNING/PENDING` → 400
- 响应 200：`data = 新任务`（旧任务保留历史）
- 错误：400（状态不允许）；401；404

### 3.6 GET /ai/tasks/statistics —— 我的任务统计

- 权限：登录（仅本人）
- 响应 200：`data = {total, pending, running, success, failed, success_rate, average_duration}`
- `success_rate`：success/total（0~1）；`average_duration`：SUCCESS 任务平均耗时秒

### 3.7 GET /ai/history —— AI 历史（任务 + 作品关联）

- 权限：登录（仅本人）
- 参数：`page` / `per_page`（默认10，最大50）
- 响应 200：分页 `data=[{...task字段, artwork: {id, title, thumbnail, model_url}|null}]`（按创建时间倒序）

---

## 4. Workshop（作品 / 社区）

### 4.1 POST /workshop/save —— 保存作品

- 权限：登录（作者取自已认证身份，忽略客户端 user_id）
- body（白名单字段）：
```json
{ "title": "必填≤200", "description": "...", "tags": [],
  "model_url": "/api/static/uploads/...", "model_format": "glb|gltf|obj|stl",
  "model_size": 123, "thumbnail": "...", "is_ai_generated": false,
  "ai_model": "...", "ai_prompt": "...", "ai_params": {},
  "is_public": true, "allow_download": false, "license_type": "all-rights-reserved" }
```
- 响应 200：`data = artwork`（detail 版）
- 错误：400（无 body/标题缺失过长）；401

### 4.2 GET /workshop/works —— 作品列表（公开）

- 权限：公开
- 参数：`page`/`per_page`（默认10，最大100）/ `sort=latest`（默认）/ `is_ai_generated=true|false` / `author_id=<int>`
- 规则：仅返回 `is_public=True` 公开作品
- 响应 200：分页 `data=[{...artwork, like_count, comment_count, collect_count}]`

### 4.3 GET /workshop/works/<artwork_id> —— 作品详情

- 权限：公开作品任何人；私有仅作者（非作者 → 404 不泄露）
- 响应 200：`data = artwork(detail) + like_count/comment_count/collect_count + current_user_status:{liked, collected, is_author}`
- 副作用：浏览量 +1
- 错误：404

### 4.4 POST /workshop/works/<artwork_id>/like —— 点赞

- 权限：登录
- 幂等：已赞再赞直接成功
- 响应 200：`data = {liked: true, like_count: N}`
- 错误：400（私有作品作者自赞明确 400）；401；404（私有非作者/不存在）

### 4.5 DELETE /workshop/works/<artwork_id>/like —— 取消点赞

- 权限：登录；幂等
- 响应 200：`data = {liked: false, like_count: N}`
- 错误：400/401/404（同点赞）

### 4.6 POST /workshop/works/<artwork_id>/collect —— 收藏

- 权限：登录；幂等
- 响应 200：`data = {collected: true, collect_count: N}`
- 错误：400/401/404

### 4.7 DELETE /workshop/works/<artwork_id>/collect —— 取消收藏

- 权限：登录；幂等
- 响应 200：`data = {collected: false, collect_count: N}`
- 错误：400/401/404

### 4.8 PUT /workshop/works/<artwork_id> —— 更新作品（仅作者）

- 权限：登录 + 作者（非作者 403）
- body：同 4.1 白名单字段（title 出现时校验）
- 响应 200：`data = artwork(detail)`
- 错误：400；401；403；404

### 4.9 DELETE /workshop/works/<artwork_id> —— 删除作品（仅作者）

- 权限：登录 + 作者
- 响应 200：`data = {id}`
- 说明：仅删记录，不删上传文件
- 错误：400；401；403；404

### 4.10 POST /workshop/works/<artwork_id>/comments —— 发表评论

- 权限：登录
- body：`{ "content": "必填，≤1000字" }`
- 响应 200：`data = {comment: {id, user_id, artwork_id, content, created_at, updated_at, author:{id, username, avatar}}}`
- 错误：400（空/超长/私有作品作者自评 400）；401；404

### 4.11 GET /workshop/works/<artwork_id>/comments —— 评论列表

- 权限：公开作品任何人；私有仅作者（非作者 404）
- 参数：`page`/`per_page`（默认10，最大50）
- 响应 200：分页 `data=[comment...]`（倒序）

### 4.12 DELETE /comments/<comment_id> —— 删除评论（仅评论作者）

- 权限：登录 + 评论作者
- 响应 200：`data = {id}`
- 错误：401；403；404

---

## 5. Admin（后台运营管理）

> 权限：`ADMIN_USER_IDS`（环境变量逗号分隔用户 ID）。未登录 → 401；非管理员 → 403。
> 管理写操作（创建/更新/删除/重试/toggle）均写 `AdminLog` 审计日志。
> 全部统计只查数据库，不触发任何第三方调用。

### 5.1 统计

#### GET /admin/statistics/users
- 响应 200：`data = {total_users, active_users, new_users_today}`

#### GET /admin/statistics/ai —— AI 任务运营统计
- 参数：`start_date`/`end_date`（YYYY-MM-DD，可选）
- 响应 200：`data = {total_tasks, success, failed, running, success_rate, avg_duration, by_provider: {provider: count}}`

#### GET /admin/statistics/credits —— 积分运营统计
- 响应 200：`data = {total_consumed, total_recharged, today_consumed, top_users: [{user_id, username, consumed}], daily: [{date, consumed}]（近7天）, by_type: [{type, amount}]}`

#### GET /admin/statistics/models —— 模型成本分析
- 参数：`start_date`/`end_date`
- 响应 200：`data = {models: [{provider, task_type, total_cost, count}]}`（成本按积分消费审计 `<TYPE>:<provider>` 解析）

#### GET /admin/statistics/models/ranking —— 模型成本排行（16-C）
- 参数：`start_date`/`end_date`
- 响应 200：`data = {ranking: [{rank, provider, total_cost, count, task_types: {type: count}}]}`（total_cost 降序）

#### GET /admin/statistics/trend —— AI 趋势分析（16-B）
- 参数：`start_date`/`end_date`/`group_by=day|week|month`（默认 day）
- 响应 200：`data = {trend: [{date, total, success, failed, credits}]}`

### 5.2 任务管理

#### GET /admin/tasks
- 参数：`status=PENDING|RUNNING|SUCCESS|FAILED` / `provider` / `page`/`per_page`
- 响应 200：分页 `data=[task + user:{id, username}]`（倒序）

#### GET /admin/tasks/<task_id>
- 响应 200：`data = task + user + credit_transactions[] + artwork:{id,title,thumbnail,model_url}|null`
- 错误：404

#### POST /admin/tasks/<task_id>/retry —— 管理员强制重试
- 规则：任意用户 `FAILED/RUNNING`；`SUCCESS/PENDING` → 400；写 AdminLog
- 响应 200：`data = {old_task, new_task}`

#### GET /admin/tasks/export —— CSV 导出（流式）
- 参数：`status`/`provider`
- 响应 200：`text/csv` 附件（`task_id,user,provider,model,status,cost,created_at,artwork_id`）

### 5.3 Provider 运营管理

#### GET /admin/providers —— 配置列表
- 响应 200：`data = {providers: [{id, name, enabled, type}]}`

#### POST /admin/providers —— 创建配置
- body：`{ "name": "hunyuan|glm|mock（唯一）", "type": "3d|analysis", "enabled": true(默认), "cost_config": {} }`
- 响应 200：`data = provider detail（含 cost_config/时间戳）`
- 错误：400（重复/非法 type）；401/403

#### PUT /admin/providers/<provider_id> —— 更新配置
- body：`{ "enabled": bool } | { "cost_config": {} } | { "type": "3d|analysis" }`（至少一项）
- 响应 200：`data = provider detail`
- 错误：400；401/403；404

#### DELETE /admin/providers/<provider_id> —— 删除配置
- 限制：存在该 provider 的任务记录 → 400 禁止删除
- 响应 200：`data = {id}`
- 错误：400；401/403；404

#### GET /admin/providers/<provider_id>/usage —— Provider 用量统计（16-C）
- 响应 200：`data = {provider: detail, total_tasks, status_counts: {PENDING,RUNNING,SUCCESS,FAILED}, success_rate, avg_duration, by_task_type, total_cost, consume_count}`

#### POST /admin/providers/<provider_id>/toggle —— 启停开关（16-C）
- body 可选：`{ "enabled": bool }`；缺省翻转当前值；写 AdminLog
- 响应 200：`data = {provider: detail, old_enabled, new_enabled}`

#### GET /admin/providers/status —— Provider 运行状态（16-D，模型健康面板）
- 响应 200：`data = {providers: [{provider, enabled, running_tasks, last_used_at}]}`
  - `enabled`：配置记录值（无记录 → true 兼容）；`running_tasks`：当前 RUNNING 任务数；`last_used_at`：最近任务更新时间（无任务 → null）
- 错误：401/403

### 5.4 审计日志

#### GET /admin/logs
- 参数：`action` / `target_type` / `admin_user_id` / `page`/`per_page`
- 响应 200：分页 `data=[{id, admin_user_id, action, target_type, target_id, detail, created_at}]`

---

## 6. Upload（文件上传，配套）

### 6.1 POST /workshop/upload —— 上传图片/3D 模型
- 权限：登录（JWT 或 Session）
- body：`multipart/form-data`，字段名 `file`（图片→images/，glb/gltf/obj/stl→models/）
- 响应 200：`data = {url: "/api/static/uploads/images/xxx.png"}`

### 6.2 POST /user/upload-avatar —— 上传头像
- 权限：登录；body：`multipart/form-data` 字段 `file` → 存 avatars/ 并更新用户头像
- 响应 200：`data = {url: "/api/static/uploads/avatars/xxx.png"}`

### 6.3 GET /static/uploads/<path> —— 静态文件访问（公开）
- 无认证；`send_from_directory` 防路径穿越

---

## 7. Health（健康检查，16-D）

### 7.1 GET /health —— 存活探针（无认证）
- 响应 200：`data = {status: "ok", version: "1.0.0", timestamp: "..."}`

### 7.2 GET /health/ready —— 就绪探针（无认证）
- 检查：数据库连通（SELECT 1）+ 必要配置（SECRET_KEY/JWT_SECRET_KEY/SQLALCHEMY_DATABASE_URI）
- 响应 200：`data = {ready: true}`
- 错误：503（数据库连接失败 / 缺少必要配置，统一错误体）

---

## 8. 附录

### 8.1 前端调用提示（交接给 A 同学）

1. 所有请求前先 `/auth/login` 拿 `token`；axios 拦截器统一注入 `Authorization: Bearer <token>`。
2. `el-upload` 场景无需手动带 token（登录已建立 Session Cookie），后端双认证兼容。
3. AI 任务创建后状态可能为 `RUNNING`（异步）：轮询 `GET /ai/tasks/<id>` 直到 `SUCCESS/FAILED`。
4. AI 调用的积分扣费/失败退款无需前端处理（后端自动）；前端展示 `GET /user/credits` 即可。
5. 管理员接口以 `ADMIN_USER_IDS` 白名单控制，非管理员一律 403。
6. 健康检查接口为运维/部署探针，前端一般无需调用。

### 8.2 通用错误响应示例（任意错误码）

```json
{ "code": 503, "message": "该 AI 模型已停用: mock", "data": null, "timestamp": "2026-09-03T00:00:00.000000" }
```

### 8.3 相关说明

- 任务/作品删除等采用软性语义或级联策略见具体接口；`artwork_id` 回填遵循"成功才建作品（方案 B）"。
- 时间字段均为 ISO8601 字符串（UTC）。
- 本契约与代码同步维护：若接口行为变更，请同步更新本文档。
