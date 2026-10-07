# 品牌与交互交付

配色、字体、间距、圆角及动效参数见 tokens.json；六个原创 SVG 图标见 icons.svg，统一 24px 画布、1.8px 线宽，使用 currentColor，可直接编辑。

以石青为主色、陶红与哑金作强调，米白背景承托彩塑内容。界面文字优先可读性，不用图案遮挡功能信息。首屏为文化与创作入口，涉及演示 AI、订单金额和权限时明确说明实际行为。

按钮反馈使用 150ms、面板进入使用 200ms，不对 3D 画布自动旋转。系统“减少动态效果”开启时停用非必要动画，已接入应用全局样式。

SVG 图标可通过 `<svg><use href="icons.svg#museum"/></svg>` 引用。答辩模板与项目同色系，包含可编辑 HTML 版式。此交付不是 Figma 云文件；Blender 源工程需在安装 Blender 的机器运行 model/build_blender_sources.py 生成。
