# 智绘锡承 - 前端交接文档（FRONTEND_HANDOFF）

> 版本：v1.1（前后端联调交付，后端 `f47de53`）
> 读者：前端 A 同学（`A_qianduan` 分支开发联调用）
> 配套：详细字段与错误码见 `backend/docs/API_CONTRACT.md`（本文件为前端使用速查）。
> 约束：以下接口均为后端**真实路由**，前端调用时统一加 `/api` 前缀。`B_houduan` 不包含 `frontend/`；前端现状基于只读核对的 `origin/A_qianduan@1f46e66`。
> 后端接口总计：46 个 Method + Route 组合；精确字段以 `API_CONTRACT.md` 为准。

---

## 1. 项目接口基础约定

### 1.1 API 统一前缀

- 后端实际路径无前缀（如 `/auth/login`）；**前端一律请求 `/api/...`**（Vite 开发代理剥除 `/api` 后转发）。
- 例：登录 → `POST /api/auth/login`；作品列表 → `GET /api/workshop/works`。

### 1.2 认证方式（JWT Bearer）

- 登录成功后 `data.token` 即 JWT；后续请求头携带：

```
Authorization: Bearer <token>
```

- axios 拦截器统一注入；`401` 表示未认证/凭证过期，前端应跳转登录页。

### 1.3 上传接口的 Cookie Session 说明

- 登录时后端**同时建立 Flask Session Cookie**（HttpOnly）。
- Vite 同源代理下，`el-upload` 可使用登录建立的 Session Cookie；若前后端跨域部署，必须显式启用 `with-credentials` 并配置允许凭据的 CORS。更稳妥的方案是为上传请求显式附加 Bearer Token。
- axios 场景带 Bearer 头同样可用（双认证兼容，JWT 优先）。

### 1.4 通用响应格式

成功：

```json
{ "code": 200, "message": "success", "data": { }, "timestamp": "..." }
```

失败（**所有错误码统一**）：

```json
{ "code": 4xx/5xx, "message": "错误说明", "data": null, "timestamp": "..." }
```

> 前端判断：`response.code === 200` 即成功（业务 code 与 HTTP 状态码一致）。

### 1.5 分页格式

分页接口的 `data` 为数组，分页信息在 `meta.pagination`：

```json
{ "code": 200, "message": "...", "data": [ ... ],
  "meta": { "pagination": { "total": 0, "count": 0, "page": 1, "page_size": 10,
            "total_pages": 0, "has_next": false, "has_prev": false } } }
```

通用参数：`page`（默认1）、`per_page`（各接口默认/上限见契约）。

---

## 2. 用户模块

| 用途 | 方法/URL | 权限 | 请求 | 关键返回字段 |
|---|---|---|---|---|
| 注册 | `POST /api/auth/register` | 公开 | `{username, email, password}`（用户名3-20位字母/数字/中文，密码≥6） | `data.id/username/email/avatar`；注册即赠 100 积分；**不返回 token** |
| 登录 | `POST /api/auth/login` | 公开 | `{email, password}` | `data.token`（JWT）、`data.id/username/avatar/bio`；同时写 Session Cookie |
| 用户信息 | `GET /api/auth/user` | 登录 | 头 `Authorization: Bearer` | `data.id/username/email/avatar/bio/location/website/level/is_active/is_verified/created_at` |
| 积分查询 | `GET /api/user/credits` | 登录 | 分页 `page/per_page` | `data.balance`、`data.transactions[]`（`amount/type/description/created_at`），分页在 `meta` |

积分流水 `type`：`RECHARGE` / `AI_GENERATE_3D` / `AI_ANALYZE_STYLE` / `REFUND`。

---

## 3. AI 模块

### 3.1 3D 生成流程（重点）

```
用户提交
   ↓  POST /api/ai/generate-3d
   ↓    { task_type: "text_to_3d"|"image_to_3d",
   ↓      prompt: "文生3D必填", input_url: "图生3D必填" }
返回 task_id（可能立即 SUCCESS，也可能 RUNNING）
   ↓  轮询 GET /api/ai/tasks/{id}
   ↓    （后端每次轮询会刷新真实异步任务状态）
SUCCESS 后 task.artwork_id 已回填 → 用 GET /api/workshop/works/{artwork_id} 展示作品
```

### 3.2 任务状态机

| 状态 | 含义 | 前端处理 |
|---|---|---|
| `PENDING` | 已创建待执行 | 等待 |
| `RUNNING` | 执行中（真实 Provider 异步，需轮询） | 轮询 `GET /api/ai/tasks/{id}` |
| `SUCCESS` | 成功，`artwork_id` 已回填 | 展示作品 / 跳详情 |
| `FAILED` | 失败（`error_message` 有原因；积分已自动退款） | 提示并允许 retry |

> 详情返回 `data`（task）：`id / provider / model / task_type / status / result_url / artwork_id / error_message / created_at / updated_at`。

### 3.3 AI 接口清单

| 用途 | 方法/URL | 权限 | 说明 |
|---|---|---|---|
| 3D 生成 | `POST /api/ai/generate-3d` | 登录 | 见上流程；重复提交同输入且存在 RUNNING 任务 → 返回已有任务 |
| 风格分析 | `POST /api/ai/analyze-style` | 登录 | `{input_url, artwork_id?}`；返回 `{task, style, features, report}`；传 `artwork_id` 且属本人 → 成功回写作品分析 |
| 任务列表 | `GET /api/ai/tasks` | 登录（本人） | 分页 |
| 任务详情 | `GET /api/ai/tasks/{task_id}` | 登录（本人） | 读取时触发一次异步刷新，用于轮询 |
| AI 历史 | `GET /api/ai/history` | 登录（本人） | 分页；`data[]` 每项含 task 字段 + `artwork:{id,title,thumbnail,model_url}|null` |
| 任务重试 | `POST /api/ai/tasks/{task_id}/retry` | 登录（本人） | 仅 `FAILED` 可重试；返回新任务 |
| 任务统计 | `GET /api/ai/tasks/statistics` | 登录（本人） | `{total, pending, running, success, failed, success_rate, average_duration}` |

---

## 4. 积分模块

- **查询**：`GET /api/user/credits` → `data.balance` + 流水列表（分页）。
- **扣费与退款均由后端自动完成**，前端只负责展示：
  - generate-3d 成功后扣（默认 20，后台可调）；失败/异常自动退款（`REFUND` 流水）。
  - analyze-style 成功后扣（默认 5）；失败/异常自动退款。
- **`402` = 积分不足**：AI 调用前后端会校验余额，不足返回 `402`（`message` 含所需积分），且**不会创建任务**。前端收到 402 应引导用户充值/提示积分不足。

---

## 5. Workshop 社区模块

| 用途 | 方法/URL | 权限 | 说明 |
|---|---|---|---|
| 作品列表 | `GET /api/workshop/works` | 公开 | 参数 `page/per_page/sort=latest/is_ai_generated/author_id`；仅返回公开作品；每项含 `like_count/comment_count/collect_count` |
| 作品详情 | `GET /api/workshop/works/{id}` | 公开（私有仅作者） | 返回基础字段 + 统计 + `current_user_status`（见下）；浏览量自动+1 |
| 保存作品 | `POST /api/workshop/save` | 登录 | `{title 必填, description, tags, model_url, ...}` |
| 更新/删除作品 | `PUT/DELETE /api/workshop/works/{id}` | 作者 | 非作者 403 |
| 点赞 | `POST /api/workshop/works/{id}/like` | 登录 | 幂等；返回 `{liked:true, like_count}` |
| 取消点赞 | `DELETE /api/workshop/works/{id}/like` | 登录 | 幂等；返回 `{liked:false, like_count}` |
| 发表评论 | `POST /api/workshop/works/{id}/comments` | 登录 | `{content ≤1000}`；返回 `data.comment` |
| 评论列表 | `GET /api/workshop/works/{id}/comments` | 公开（私有仅作者） | 分页 |
| 删除评论 | `DELETE /api/comments/{comment_id}` | 评论作者 | 非作者 403 |
| 收藏 | `POST /api/workshop/works/{id}/collect` | 登录 | 幂等；返回 `{collected:true, collect_count}` |
| 取消收藏 | `DELETE /api/workshop/works/{id}/collect` | 登录 | 幂等；返回 `{collected:false, collect_count}` |

### 详情返回重点：`current_user_status`

`GET /api/workshop/works/{id}` 的 `data` 内（登录后有效）：

```json
"current_user_status": { "liked": false, "collected": false, "is_author": false }
```

- `liked`：当前用户是否已赞（按钮高亮用）
- `collected`：当前用户是否已收藏（收藏图标态用）
- `is_author`：当前用户是否作者（编辑/删除按钮显隐用）
- 未登录浏览时三字段均为 false（公开作品可看不可互动）。

---

## 6. Admin 模块（后台管理）

> 管理员接口前缀 `/api/admin/*`，**仅管理员**可用：未登录 401，非管理员 403（管理员由后端 `ADMIN_USER_IDS` 白名单配置，前端无需感知）。

| 用途 | 方法/URL | 说明 |
|---|---|---|
| 用户统计 | `GET /api/admin/statistics/users` | `{total_users, active_users, new_users_today}` |
| AI 统计 | `GET /api/admin/statistics/ai` | `{total_tasks, success, failed, running, success_rate, avg_duration, by_provider}`；支持 `start_date/end_date` |
| 积分统计 | `GET /api/admin/statistics/credits` | `{total_consumed, total_recharged, today_consumed, top_users, daily[7], by_type}` |
| 趋势分析 | `GET /api/admin/statistics/trend` | `group_by=day|week|month`；`{trend:[{date,total,success,failed,credits}]}` |
| 模型成本 | `GET /api/admin/statistics/models` | `{models:[{provider, task_type, total_cost, count}]}` |
| 模型排行 | `GET /api/admin/statistics/models/ranking` | `{ranking:[{rank, provider, total_cost, count, task_types}]}`（成本降序） |
| Provider 列表/创建 | `GET/POST /api/admin/providers` | 创建 `{name, type:3d|analysis, enabled?, cost_config?}` |
| Provider 更新/删除 | `PUT/DELETE /api/admin/providers/{id}` | 有任务记录禁止删除（400） |
| Provider 用量 | `GET /api/admin/providers/{id}/usage` | `{total_tasks, status_counts, total_cost, ...}` |
| Provider 启停 | `POST /api/admin/providers/{id}/toggle` | `{enabled?}`，缺省翻转；`enabled=false` 即停用该模型（新调用 503） |
| **Provider 状态** | `GET /api/admin/providers/status` | 模型健康面板：`{provider, enabled, running_tasks, last_used_at}` |
| Task 列表 | `GET /api/admin/tasks` | `status/provider` 过滤，分页 |
| Task 详情 | `GET /api/admin/tasks/{id}` | task + user + 积分流水 + artwork |
| Task 强制重试 | `POST /api/admin/tasks/{id}/retry` | 任意用户 `FAILED/RUNNING` |
| Task 导出 | `GET /api/admin/tasks/export` | CSV 流式下载 |
| 审计日志 | `GET /api/admin/logs` | `action/target_type/admin_user_id` 过滤，分页 |

---

## 7. 错误码说明

| code | 含义 | 前端建议 |
|---|---|---|
| 400 | 参数校验失败（缺字段/格式错/非法状态/重复） | 展示 `message`，修正表单 |
| 401 | 未认证/凭证无效 | 跳转登录页 |
| 402 | 积分不足 | 提示积分不足，引导充值/获取积分 |
| 403 | 权限不足（非作者/非管理员） | 隐藏操作入口或提示无权限 |
| 404 | 资源不存在 | 展示"不存在"（隔离场景后端不泄露存在性） |
| 405 | 请求方法不允许 | 检查 URL 与 method 是否匹配 |
| 503 | AI Provider 停用 / AI 服务异常 | 提示"模型暂不可用" |
| 500 | 服务器内部错误 | 通用兜底提示 |

> 所有错误响应体统一 `{code, message, data:null}`，直接取 `message` 展示即可。

---

## 8. 前端页面对应关系

| 前端页面/模块 | 对应接口 |
|---|---|
| 登录/注册页 | `/api/auth/login`、`/api/auth/register` |
| 首页社区（作品瀑布流） | `GET /api/workshop/works`（列表）、`GET /api/workshop/works/{id}`（详情） |
| 作品详情/互动 | 详情 + `POST/DELETE .../like`、`POST/DELETE .../collect`、`GET/POST .../comments`、`DELETE /api/comments/{id}` |
| AI 生成页 | `POST /api/ai/generate-3d`、轮询 `GET /api/ai/tasks/{id}`、`POST /api/ai/analyze-style`、`POST /api/ai/tasks/{id}/retry` |
| 我的 AI 历史 | `GET /api/ai/history`、`GET /api/ai/tasks/statistics` |
| 个人中心 | `GET /api/auth/user`、`GET /api/user/credits`、`POST /api/user/upload-avatar`、`GET /api/workshop/works?author_id=我`（我的作品） |
| 上传 | `POST /api/workshop/upload`（图片/模型）、`POST /api/user/upload-avatar`（头像） |
| 后台管理（管理员） | `/api/admin/*`（统计/任务/Provider/日志，见第 6 节） |

---

## 9. 当前 A 分支接入现状（只读快照）

> 核对来源：`origin/A_qianduan@1f46e66`。A 同学继续开发后，应在合并/联调前重新跑一遍清单。

### 9.1 已接真实后端

- `src/api/auth.js` + `store/userStore.js` 已调用登录、注册、当前用户接口，登录正确读取 `response.data.token`。
- `src/api/index.js` 的 `baseURL` 默认 `/api`，Vite 代理正确剥离 `/api` 并转发 `localhost:8000`。
- `src/api/workshop.js` 的 `saveWork`、`uploadFile` 路径与后端一致；当前实际使用的是 `AdvancedMultiModalInput` 图片上传。
- Community 页面和 Profile 页面中的 `el-upload` action 使用了真实上传路径。

### 9.2 仍为 Mock / 本地状态

- `AIWorkshopCanvas.vue` 用定时器模拟进度，并随机创建 Three.js 几何体；未调用 AI API。
- `AdvancedMultiModalInput.vue` 文本确认使用 `setTimeout` 模拟；图片只上传，未接 analyze-style 或 image-to-3D。
- `CommunityView.vue` 的作品、点赞、评论、发布全部为本地数组修改，未导入 community API。
- `ProfileView.vue` 的我的作品、收藏、订单、资料修改和密码修改均为本地 Mock。
- `MultiModalInputView.vue` 仅显示旋转立方体，没有加载后端 GLB。
- 当前 A 分支没有 Admin 页面或 Admin API 封装。

### 9.3 错误或过时路径

| 前端文件 | 当前路径/行为 | 正确后端能力 |
|---|---|---|
| `src/api/workshop.js` | `POST /workshop/generate` | `POST /api/ai/generate-3d` |
| `src/api/workshop.js` | `GET /workshop/parts` | 后端无此接口；零件编辑保持纯前端或移除请求 |
| `src/api/community.js` | `/community/works*` | `/api/workshop/works*` |
| `src/api/community.js` | `POST /community/works` multipart | 先 `/api/workshop/upload`，再 JSON `POST /api/workshop/save` |
| `src/api/auth.js` | `POST /auth/logout` | 后端无此接口；当前只做本地退出 |

### 9.4 尚未使用的后端能力

- AI generate/analyze、任务详情轮询、任务列表、历史、统计和失败任务重试。
- Credits 余额与流水，以及 402 和失败退款后的刷新。
- Community 详情、取消点赞、收藏/取消收藏、评论列表和删除评论。
- 作品更新/删除、按作者与 AI 标记过滤。
- 全部 Admin API、Provider 状态、CSV 导出和审计日志。
- `/health` 与 `/health/ready`（通常由部署监控使用）。

## 10. model_url 与 Three.js

- `SUCCESS` 任务优先使用 `artwork_id` 查询作品详情，再读取 `data.model_url`；`result_url` 可用于任务态展示，但最终作品以 Artwork 为准。
- 后端本地持久化 URL 形如 `/api/static/uploads/models/<uuid>.glb`，浏览器经 Vite 代理即可访问。
- A 分支当前只创建内置几何体，没有导入 `GLTFLoader`。应使用 `three/examples/jsm/loaders/GLTFLoader.js` 加载 GLB，并处理 loading、404、解析失败、对象释放及相机适配。
- 不要拼接后端文件系统路径；直接把 API 返回的 URL 交给 loader。若部署为不同域名，应通过统一 API base URL 解析。

## 11. 认证与前端状态注意事项

- `userStore.login()` 保存的对象含 token，当前 axios 拦截器可以正确注入 Bearer。
- 当前 `fetchUserInfo()` 会用 `/auth/user` 返回值整体覆盖 `user`，但该响应不含 token，之后 Bearer 会丢失。必须保留原 token或把 token 独立存储。
- `/auth/user` 本身要求 JWT；上传接口才支持 JWT/Session 双认证。
- 401 时清除登录态并跳转登录；402 单独提示积分不足；503 展示 Provider 安全错误消息但不要自动重试付费操作。

## 12. 联调执行入口

逐步执行、验收状态表和失败记录模板见 [`INTEGRATION_CHECKLIST.md`](./INTEGRATION_CHECKLIST.md)。

## 附：简版联调 Checklist

1. 登录拿 `token` → 全局 axios 注入 Bearer。
2. 上传用 el-upload（Cookie Session 免 token）确认 `/api/workshop/upload` 返回 `data.url`。
3. 走通一条 AI 3D 生成：提交 → 轮询详情 → SUCCESS → 展示作品 → 积分余额减少。
4. 余额不足（402）与失败退款（REFUND）的前端提示与余额刷新。
5. 社区互动全链路（赞/藏/评/删评）+ `current_user_status` 状态同步。
6. 管理员账户（后端白名单）验证后台各统计与 Provider 启停后新调用返回 503。
