## 获取完整项目（含三维模型）

三维模型、原始模型档案、分类模型权重及素材压缩包使用 Git LFS。请先安装 Git 和 Git LFS，再克隆指定分支：

```bash
git lfs install
git clone --branch A_qianduan https://github.com/xingrong111/Dchuang.git
cd Dchuang
git lfs pull
```

不要把 LFS 指针文件当作模型文件使用。原始模型有重复归档，完整工作目录约数 GB；只运行网站时使用 `frontend/public` 中的优化模型。仓库包含环境变量模板，真实密钥、个人数据库、依赖安装目录和浏览器登录数据不上传。

克隆后先安装后端依赖并根据 `backend/.env.example` 建立本机 `.env`，运行数据库迁移；前端执行 `npm ci`。本地 SQLite 环境可以使用 `backend/scripts/refresh_public_catalog.py` 初始化社区六件作品及商城十款文创目录；脚本仅支持工作区 `backend/dev.db`，生产数据库应使用部署流程导入，不能直接照搬本机数据库。

GitHub 保存项目代码与资源；公众访问网站还需要部署前后端和数据库，见 [部署说明](deploy/README.md)。

# 智绘锡承

面向惠山泥人数字化展示、AI 辅助创作、3D 部件组装及作品交流的大学生创新项目。

项目完成度、实际测试结果和未完成项见 [项目审查报告](PROJECT_AUDIT.md)。3D 资产来源为本项目程序化建模，不是混元生成结果。

## 启动

后端（默认 8000）：

```powershell
cd backend
.\.venv\Scripts\python.exe -m flask db upgrade
.\.venv\Scripts\python.exe run.py
```

首次部署需要按 backend/.env.example 配置数据库与环境，不要覆盖已有 .env。已有迁移，勿重新 flask db init。

另开终端启动前端：

```powershell
cd frontend
npm install
npm run dev
```

本地分类服务（可选，8001）：

```powershell
cd model
.\.venv\Scripts\python.exe main_api.py
```

真实 AI 配置在 backend/.env：AI_GENERATION_PROVIDER=hunyuan，AI_ANALYSIS_PROVIDER=glm 或 fusion；需要相应凭据，本地 fusion 还需要分类服务。mock 用于离线演示，展示固定阿福资产。

## 目录

- frontend：Vue3 页面、Three.js 工坊及公开 /model-library 资产库。
- backend：Flask API、数据库迁移、任务/积分、商城和管理接口。
- model：分类模型、标注数据、训练评估和 FastAPI 推理。
- operations：非遗、展品、故事、宣传文案及图片索引。

3D 资产清单与视觉验收规则见 [模型说明](frontend/public/models/README.md)。

## 检查

```powershell
cd frontend
npm test
npm run models:export
npm run models:check
npm run build
```

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

生产构建通过不等于真实云服务、研究指标和上线部署已经验收，具体边界见审查报告。


## 最新补全交付（2026-10-02）

- [运行、备份与恢复](deploy/README.md)
- [固定留出测试与模型对比](model/reports/研究结果.md)
- [可编辑答辩HTML模板](operations/deliverables/答辩模板.html)
- [可编辑界面SVG源稿](operations/deliverables/界面设计稿.svg)
- [商业与运营执行方案](operations/docs/商业与运营实施方案.md)
- [用户调研问卷](operations/docs/用户调研问卷.md)

当前后端465项测试通过，前端构建/lint和本地浏览器交互通过。当前本机SQLite已先创建快照再升级到新migration；其他目标数据库仍需执行 flask db upgrade。生产WSGI依赖、外部账户、真实调研/授权及正式部署仍按审查报告列明，不能将模板与演示视为真实验收证据。
