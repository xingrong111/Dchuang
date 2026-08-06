# 智绘锡承 - 新中式非遗风格设计系统

## 一、设计理念

### 视觉定位
「新中式非遗风格」—— 融合传统文化底蕴与现代极简美学
- **气质**：典雅、温润、匠心
- **感受**：如青瓷般内敛沉稳，如水墨画般意境深远

### 设计原则
1. **文化传承**：融入锡绣、紫砂、泥人等非遗元素
2. **现代简约**：简洁布局、留白充足、信息清晰
3. **功能优先**：良好的可用性与无障碍设计
4. **响应式**：完美适配移动端到桌面端

---

## 二、色彩体系 (Color Tokens)

### 主色调
```css
:root {
  /* 青瓷色系 - 主色调 */
  --color-primary: #4a90a4;          /* 青瓷主色 */
  --color-primary-hover: #3d7a8d;     /* 悬停状态 */
  --color-primary-active: #2d6172;    /* 激活状态 */
  --color-primary-light: #e8f1f3;     /* 浅色背景 */
  --color-primary-50: #f5f9fa;        /* 极浅色 */

  /* 赭石点缀 - 强调色 */
  --color-accent: #c7693d;            /* 赭石色 */
  --color-accent-hover: #a8552f;      /* 悬停状态 */
  --color-accent-light: #fdf0e9;      /* 浅色背景 */

  /* 金色点缀 - 非遗感 */
  --color-gold: #b8860b;              /* 古铜金 */
  --color-gold-light: #f5e6c8;        /* 浅金色 */

  /* 文本颜色 */
  --color-text-primary: #2c3e50;      /* 主文本 */
  --color-text-secondary: #5d6d7e;    /* 次要文本 */
  --color-text-muted: #95a5a6;        /* 弱化文本 */
  --color-text-inverse: #ffffff;      /* 反色文本 */

  /* 背景颜色 */
  --color-bg-paper: #f8f6f0;          /* 宣纸白 */
  --color-bg-secondary: #f0ede4;      /* 次要背景 */
  --color-bg-tertiary: #e8e4da;       /* 第三层背景 */
  --color-bg-card: #ffffff;           /* 卡片背景 */
  --color-bg-dark: #2c3e50;          /* 深色背景 */

  /* 边框颜色 */
  --color-border: #d5d0c4;           /* 主边框 */
  --color-border-light: #e8e4da;     /* 浅色边框 */
  --color-border-dark: #b8b2a3;      /* 深色边框 */

  /* 功能色 */
  --color-success: #52b788;          /* 成功 */
  --color-warning: #e9a825;          /* 警告 */
  --color-danger: #e57373;            /* 危险 */
  --color-info: #64b5f6;             /* 信息 */
}
```

### 渐变系统
```css
:root {
  /* 主渐变 - 用于Hero区域、按钮 */
  --gradient-primary: linear-gradient(135deg, #4a90a4 0%, #2d6172 100%);
  --gradient-accent: linear-gradient(135deg, #c7693d 0%, #a8552f 100%);
  --gradient-hero: linear-gradient(135deg, #2d6172 0%, #1a3d4a 100%);
  --gradient-gold: linear-gradient(135deg, #b8860b 0%, #8b6914 100%);

  /* 光影效果 */
  --shadow-sm: 0 2px 4px rgba(44, 62, 80, 0.08);
  --shadow-md: 0 4px 12px rgba(44, 62, 80, 0.1);
  --shadow-lg: 0 8px 24px rgba(44, 62, 80, 0.12);
  --shadow-xl: 0 16px 48px rgba(44, 62, 80, 0.16);
  --shadow-card: 0 4px 20px rgba(44, 62, 80, 0.06);
  --shadow-card-hover: 0 8px 32px rgba(44, 62, 80, 0.12);

  /* 特殊效果 */
  --border-radius-sm: 4px;
  --border-radius-md: 8px;
  --border-radius-lg: 16px;
  --border-radius-xl: 24px;
  --border-radius-full: 9999px;

  /* 过渡动画 */
  --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}
```

---

## 三、字体体系 (Typography)

```css
:root {
  /* 字体栈 */
  --font-primary: 'Noto Serif SC', 'Source Han Serif SC', 'Songti SC', 'SimSun', serif;
  --font-secondary: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif;
  --font-mono: 'Fira Code', 'Source Code Pro', monospace;

  /* 字体大小 */
  --text-xs: 0.75rem;      /* 12px */
  --text-sm: 0.875rem;     /* 14px */
  --text-base: 1rem;       /* 16px */
  --text-lg: 1.125rem;     /* 18px */
  --text-xl: 1.25rem;      /* 20px */
  --text-2xl: 1.5rem;      /* 24px */
  --text-3xl: 1.875rem;    /* 30px */
  --text-4xl: 2.5rem;      /* 40px */
  --text-5xl: 3.125rem;    /* 50px */
  --text-6xl: 3.75rem;     /* 60px */

  /* 字重 */
  --font-weight-light: 300;
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;

  /* 行高 */
  --line-height-tight: 1.2;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.7;
}
```

### 字体使用规范
- **标题**：使用 `--font-primary` 衬线字体，体现文化底蕴
- **正文**：使用 `--font-secondary` 无衬线字体，保证可读性
- **装饰文字**：可使用书法风格字体（需引入额外字体）

---

## 四、间距体系 (Spacing)

```css
:root {
  /* 基础间距单位: 4px */
  --space-1: 0.25rem;    /* 4px */
  --space-2: 0.5rem;     /* 8px */
  --space-3: 0.75rem;    /* 12px */
  --space-4: 1rem;       /* 16px */
  --space-5: 1.5rem;     /* 24px */
  --space-6: 2rem;       /* 32px */
  --space-8: 3rem;       /* 48px */
  --space-10: 4rem;      /* 64px */
  --space-12: 5rem;      /* 80px */
  --space-16: 6rem;      /* 96px */
}
```

### 布局间距规则
- **组件内边距**：`--space-4` 到 `--space-6`
- **卡片间距**：`--space-5` 到 `--space-6`
- **区块间距**：`--space-10` 到 `--space-16`
- **页面边距**：移动端 `--space-4`，桌面端 `--space-6`

---

## 五、栅格系统 (Grid)

```css
:root {
  /* 容器宽度 */
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;
  --container-2xl: 1440px;

  /* 栅格间隙 */
  --grid-gap-sm: 12px;
  --grid-gap-md: 16px;
  --grid-gap-lg: 24px;
  --grid-gap-xl: 32px;
}

/* 响应式断点 */
/* sm: 640px  |  md: 768px  |  lg: 1024px  |  xl: 1280px  |  2xl: 1440px */
```

---

## 六、组件规范

### 导航栏
- 高度：64px
- 背景：`--color-bg-paper`（磨砂玻璃效果）
- Logo：左侧，青瓷色图标
- 导航链接：居中，当前页高亮使用 `--color-primary` 下划线
- 用户区：右侧

### 按钮
```css
/* 主按钮 */
.btn-primary {
  background: var(--gradient-primary);
  color: white;
  padding: 12px 32px;
  border-radius: var(--border-radius-full);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-normal);
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* 次要按钮 */
.btn-secondary {
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  padding: 12px 32px;
  border-radius: var(--border-radius-full);
  transition: all var(--transition-normal);
}
.btn-secondary:hover {
  background: var(--color-primary-light);
}
```

### 卡片
```css
.card {
  background: var(--color-bg-card);
  border-radius: var(--border-radius-lg);
  box-shadow: var(--shadow-card);
  transition: all var(--transition-normal);
  overflow: hidden;
}
.card:hover {
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-4px);
}
```

### 表单
```css
.input {
  background: var(--color-bg-paper);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius-md);
  padding: 12px 16px;
  transition: all var(--transition-fast);
}
.input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
  outline: none;
}
```

---

## 七、动效规范

### 微交互
- **按钮悬停**：`translateY(-2px)` + 阴影加深
- **卡片悬停**：`translateY(-4px)` + 阴影加深
- **过渡时间**：150ms ~ 300ms

### 页面过渡
- **淡入效果**：新页面元素依次淡入
- **滚动触发**：滚动时元素从下方淡入

### 装饰动画
- 首页Hero区域：水墨晕染效果、云纹流动
- 加载状态：青瓷色旋转器

---

## 八、布局架构

### 整体布局
```
┌─────────────────────────────────────────┐
│  顶部导航栏 (固定)                        │
├─────────────────────────────────────────┤
│                                         │
│  Hero区域 / 页面头部                     │
│                                         │
├─────────────────────────────────────────┤
│  主要内容区域 (12栅格)                   │
│  ┌────┬────────────────────┬────┐       │
│  │侧栏│     主内容区       │侧栏│       │
│  └────┴────────────────────┴────┘       │
│                                         │
├─────────────────────────────────────────┤
│  页脚                                    │
└─────────────────────────────────────────┘
```

### 侧边栏布局
- 宽度：240px（展开），64px（折叠）
- 背景：`--color-bg-paper`
- 菜单项：图标 + 文字，悬停时高亮

---

## 九、与旧版对比

| 项目 | 旧版 | 新版 |
|------|------|------|
| **主色** | 紫绿渐变 (#667eea) | 青瓷色系 (#4a90a4) |
| **辅色** | 无明确辅色 | 赭石色 (#c7693d) |
| **背景** | 浅灰 (#f5f5f5) | 宣纸白 (#f8f6f0) |
| **字体** | 系统默认 | 思源宋体 + PingFang |
| **圆角** | 20-30px（过大） | 4-16px（克制） |
| **阴影** | 浓重阴影 | 轻盈多层次阴影 |
| **导航** | 渐变背景 | 磨砂玻璃 + 青瓷下划线 |
| **按钮** | 普通圆角 | 胶囊形 + 渐变 |
| **整体风格** | 现代科技风 | 新中式非遗风 |

---

## 十、实施计划

### 第一阶段：基础样式
1. 更新 `theme.css` 为新设计系统
2. 更新 `main.css` 基础样式
3. 更新导航栏样式

### 第二阶段：核心页面
1. 首页 (HomeView)
2. 登录/注册页
3. 数字博物馆 (MuseumView)
4. 文创商城 (MarketView)

### 第三阶段：功能页面
1. 社区广场 (CommunityView)
2. AI共创工坊 (WorkshopView)
3. 个人中心 (ProfileView)

### 第四阶段：细节优化
1. 响应式适配
2. 动画效果
3. 无障碍优化

---

*注：本文档为设计规范参考文档，实际代码实现请查看对应的Vue组件文件。*