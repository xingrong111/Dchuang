# 生产运行与恢复

适用于现有 Vue + Flask 项目。新数据库必须先迁移；本机测试数据与开发数据库分别保留。

## 配置与启动

在 `backend/.env` 设置生产 SECRET_KEY、JWT_SECRET_KEY、DATABASE_URL 和实际 HTTPS CORS_ORIGINS。禁止示例密钥。设置 `AI_WORKER_ENABLED=false`，生产 WSGI 不启动内嵌 Worker。

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:FLASK_CONFIG='production'
.\.venv\Scripts\python.exe -m flask db upgrade
.\.venv\Scripts\python.exe serve.py
```

独立终端运行 `python worker.py`。操作系统文件锁限制同一主机同一路径只能运行一个 Worker；多主机部署应只在指定一台运行 Worker，文件锁不提供跨主机协调。Worker 与 API 使用同一数据库和上传目录。

前端 `npm run build` 后由 Nginx 托管 dist；示例 nginx.conf 将 `/api/` 去掉后代理至 API，并提供 SPA 路由回退。部署方必须在实际域名上配置有效 TLS 证书：当前 HTTP 示例适用于 TLS 终止代理后或本机测试，不能直接认定 HTTPS 上线完成。生产 Secure Cookie 要求浏览器使用 HTTPS。

Linux 服务文件需先创建无登录 `nih` 账号，调整路径与目录所有者，再安装到 systemd。Windows 可用组织批准的服务管理器运行同样两个 Python 入口；不自动安装系统级服务。

## 备份与恢复

先停止 API、Worker 以及其他写入进程，保证数据库与文件一致。备份是包含账户密码哈希和订单个人信息的私有 ZIP，不包含 `.env`，应放入受限访问、加密的备份存储。

```powershell
python scripts/backup_restore.py backup backups/2026-10-02.zip --offline
```

恢复时使用**新建、空的、已迁移到同一 revision 的数据库和空上传目录**，通过目标环境变量连接恢复库，然后执行：

```powershell
python scripts/backup_restore.py restore backups/2026-10-02.zip --offline
```

脚本拒绝已有业务数据、已有上传文件、路径逃逸、清单/校验不一致和 migration 版本不匹配。验证码不恢复。校验 SHA256 用于发现损坏，不是备份来源的数字签名。先在隔离恢复库验证登录、作品、模型和订单后，再由部署方切换连接；脚本不会清空旧库。

## 观测与验收

```powershell
python scripts/load_test.py --url http://127.0.0.1:8000/workshop/works --requests 100 --concurrency 8
```

报告记录端点、并发、失败数、p95 和原始耗时。它不调用付费生成，不把只读接口吞吐当作 AI 并发能力。上线还需用实际数据库做 MySQL migration、订单库存并发、真实云调用/邮件/链上回执测试及端到端浏览器流程。

本机 Waitress 依赖安装因网络 TLS 错误失败；serve.py 尚未进行生产 WSGI 运行验收。数据库/文件离线备份恢复已通过独立测试库往返测试。
