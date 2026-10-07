# 智绘锡承 Frontend

Vue3 + Pinia + Element Plus + Three.js。前端请求 /api，Vite 代理到 localhost:8000 并移除 /api 前缀。

```powershell
npm install
npm run dev
npm run build
```

主要页面：/museum（数字博物馆）、/model-library（三成品/五部件）、/workshop（多模态与组装）、/community、/shop、/profile、/admin。登录页面和具体路由以 src/router 为准，管理接口在后端校验管理员权限。

```powershell
npm test
npm run models:export
npm run models:check
```

改建模源文件后重新导出 GLB 和 manifest.json。资产说明见 public/models/README.md，整体完成度见 ../PROJECT_AUDIT.md。

编辑器支持点击/拖入部件、锚点连接、旋转/缩放、颜色调整、Delete 删除、GLB/OBJ/PNG 导出、上传保存作品。OBJ 仅导出几何，完整彩绘/PBR 使用 GLB。

mock 任务使用固定阿福模型并标注为演示。真实混元/GLM/融合服务需后端配置。图片分析与生成进度由任务接口返回，不把演示结果当真实 AI 结果。

可选 VITE_API_BASE_URL 适用于外部 API；生产部署还需配置 /api 反向代理及 SPA history 回退。npm run lint 只检查，npm run lint:fix 才自动修复。


2026-10-02：Element Plus 按需加载，首页主包约252KB；3D依赖仍为独立大包。移动编辑器画布与参数上下排列。/help、/terms、/privacy 提供真实功能与数据说明。VITE_CONTACT_EMAIL 配置实际联系邮箱。

浏览器验收脚本 scripts/browser-acceptance.mjs 与 scripts/flow-acceptance.mjs 使用独立 run_acceptance.py 数据库和无头 Edge CDP。具体结果保存在 reports/browser；所有 AI 浏览器验收使用 mock，不代表真实云调用。


## 文创产品原型

`/shop`为五款文创概念展示，包含AI设计效果图和可旋转GLB视觉原型；图与模型细节不同，均未打样、不提供购买。`/shop?design=afu-desk`可直达详情。产品工厂见src/three/productFactory.js，导出使用`npm run products:export`，测试使用`npm test`。原图和提示词见operations/deliverables/product-visuals，WebP在public/content，GLB在public/models/products。
