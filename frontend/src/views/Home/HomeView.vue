<template>
  <div class="home">
      <!-- Hero 区域 -->
    <section class="hero-section">
      <div class="hero-bg-decoration">
        <div class="ink-wash ink-1"></div>
        <div class="ink-wash ink-2"></div>
        <div class="ink-wash ink-3"></div>
      </div>
      <div class="hero-content">
        <div class="hero-text">
          <div class="hero-seal">锡</div>
          <h1 class="hero-title">智绘锡承</h1>
          <p class="hero-subtitle">让传统非遗在数字时代焕发新生</p>
          <p class="hero-desc">以AI为笔，以3D为墨，绘就江南非遗新画卷</p>
          <div class="hero-buttons">
            <router-link to="/workshop" class="hero-btn primary">
              <el-icon><Brush /></el-icon>
              开始创作
            </router-link>
            <router-link to="/museum" class="hero-btn secondary">
              <el-icon><OfficeBuilding /></el-icon>
              探索博物馆
            </router-link>
          </div>
        </div>
        <div class="hero-visual">
          <div class="visual-container">
            <div class="circle-main"></div>
            <div class="circle-orb orb-1"></div>
            <div class="circle-orb orb-2"></div>
            <div class="circle-orb orb-3"></div>
            <div class="particle p1"></div>
            <div class="particle p2"></div>
            <div class="particle p3"></div>
            <div class="particle p4"></div>
          </div>
        </div>
      </div>
      <div class="hero-cloud-divider">
        <svg viewBox="0 0 1200 40" preserveAspectRatio="none">
          <path d="M0 20 Q 100 5, 200 20 T 400 20 T 600 20 T 800 20 T 1000 20 T 1200 20" fill="none" stroke="#f8f6f0" stroke-width="2"/>
        </svg>
      </div>
    </section>

    <!-- 核心功能 -->
    <section class="features-section">
      <div class="container">
        <div class="section-header">
          <h2 class="section-title">核心功能</h2>
          <p class="section-desc">探索我们为您打造的非遗数字创新体验</p>
        </div>
        <div class="features-grid">
          <div class="feature-card" v-for="feature in features" :key="feature.title">
            <div class="feature-icon" :style="{ background: feature.gradient }">
              <el-icon :size="32"><component :is="feature.icon" /></el-icon>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
            <router-link :to="feature.link" class="feature-link">
              了解更多
              <el-icon><ArrowRight /></el-icon>
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- 热门精选 -->
    <section class="highlights-section">
      <div class="container">
        <div class="section-header with-link">
          <div>
            <h2 class="section-title">热门精选</h2>
            <p class="section-desc">发现更多精彩非遗作品</p>
          </div>
          <router-link to="/community" class="view-all">
            查看全部
            <el-icon><ArrowRight /></el-icon>
          </router-link>
        </div>
        <div class="highlights-grid">
          <div class="highlight-card" v-for="item in highlights" :key="item.id">
            <div class="highlight-image" :style="{ background: item.bgGradient }">
              <span class="highlight-emoji">{{ item.icon }}</span>
              <span class="highlight-category">{{ item.category }}</span>
            </div>
            <div class="highlight-info">
              <h4>{{ item.title }}</h4>
              <p class="highlight-author">
                <el-icon><User /></el-icon>
                {{ item.author }}
              </p>
              <div class="highlight-stats">
                <span><el-icon><Star /></el-icon> {{ item.likes }}</span>
                <span><el-icon><View /></el-icon> {{ item.views }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 统计数据 -->
    <section class="stats-section">
      <div class="container">
        <div class="stats-grid">
          <div class="stat-item" v-for="stat in stats" :key="stat.label">
            <div class="stat-number">{{ stat.value }}</div>
            <div class="stat-divider"></div>
            <div class="stat-label">{{ stat.label }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="cta-section">
      <div class="container">
        <div class="cta-card">
          <div class="cta-decoration-left">
            <svg viewBox="0 0 60 60">
              <circle cx="30" cy="30" r="28" fill="none" stroke="rgba(74,144,164,0.2)" stroke-width="1"/>
              <circle cx="30" cy="30" r="20" fill="none" stroke="rgba(74,144,164,0.3)" stroke-width="1"/>
              <circle cx="30" cy="30" r="12" fill="none" stroke="rgba(74,144,164,0.4)" stroke-width="1"/>
            </svg>
          </div>
          <div class="cta-content">
            <h2>加入我们，共创非遗数字未来</h2>
            <p>成为创作者，分享您的非遗创意作品</p>
            <div class="cta-buttons">
              <router-link to="/register" class="btn-cta primary">免费注册</router-link>
              <router-link to="/about" class="btn-cta ghost">了解更多</router-link>
            </div>
          </div>
          <div class="cta-decoration-right">
            <svg viewBox="0 0 60 60">
              <rect x="5" y="5" width="50" height="50" rx="4" fill="none" stroke="rgba(199,105,61,0.2)" stroke-width="1"/>
              <rect x="15" y="15" width="30" height="30" rx="2" fill="none" stroke="rgba(199,105,61,0.3)" stroke-width="1"/>
              <rect x="22" y="22" width="16" height="16" rx="1" fill="none" stroke="rgba(199,105,61,0.4)" stroke-width="1"/>
            </svg>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { Brush, OfficeBuilding, User, Star, View, ArrowRight, Avatar, ShoppingBag } from '@element-plus/icons-vue'

const features = [
  {
    icon: Brush,
    title: 'AI智能生成',
    description: '文字描述一键生成3D非遗作品，让创意无限延伸',
    link: '/workshop',
    gradient: 'linear-gradient(135deg, #4a90a4 0%, #2d6172 100%)'
  },
  {
    icon: OfficeBuilding,
    title: '数字博物馆',
    description: '沉浸式体验无锡非遗文化，探索历史与艺术的交融',
    link: '/museum',
    gradient: 'linear-gradient(135deg, #52b788 0%, #2d6172 100%)'
  },
  {
    icon: Avatar,
    title: '共创社区',
    description: '与同好交流创作心得，分享创意与灵感',
    link: '/community',
    gradient: 'linear-gradient(135deg, #c7693d 0%, #a8552f 100%)'
  },
  {
    icon: ShoppingBag,
    title: '文创商城',
    description: '数字作品实体化定制，让非遗走进生活',
    link: '/shop',
    gradient: 'linear-gradient(135deg, #b8860b 0%, #8b6914 100%)'
  }
]

const highlights = [
  {
    id: 1,
    title: '现代风格惠山泥人',
    author: '创意达人',
    likes: 124,
    views: 568,
    icon: '🗿',
    category: '惠山泥人',
    bgGradient: 'linear-gradient(135deg, #e8f1f3 0%, #d4e4e8 100%)'
  },
  {
    id: 2,
    title: '数字锡绣 - 江南水乡',
    author: '绣娘传人',
    likes: 89,
    views: 342,
    icon: '🧵',
    category: '锡绣',
    bgGradient: 'linear-gradient(135deg, #fdf0e9 0%, #f5ddce 100%)'
  },
  {
    id: 3,
    title: 'Q版紫砂茶宠',
    author: '陶艺新手',
    likes: 156,
    views: 623,
    icon: '🍵',
    category: '紫砂陶艺',
    bgGradient: 'linear-gradient(135deg, #f5e6c8 0%, #ecd9a8 100%)'
  }
]

const stats = [
  { value: '1,000+', label: '非遗作品' },
  { value: '5,000+', label: '活跃用户' },
  { value: '50+', label: '非遗项目' },
  { value: '100,000+', label: '浏览次数' }
]
</script>

<style scoped>
/* ============ Hero 区域 ============ */
.home {
  width: 100%;
}

.hero-section {
  position: relative;
  background: var(--gradient-hero);
  padding: 0;
  overflow: hidden;
  min-height: 600px;
}

.hero-bg-decoration {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.ink-wash {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.15;
}

.ink-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(74,144,164,0.8), transparent);
  top: -100px;
  right: -50px;
  animation: inkFloat1 8s ease-in-out infinite;
}

.ink-2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(199,105,61,0.6), transparent);
  bottom: 50px;
  left: -80px;
  animation: inkFloat2 10s ease-in-out infinite;
}

.ink-3 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(184,134,11,0.5), transparent);
  top: 50%;
  right: 30%;
  animation: inkFloat3 12s ease-in-out infinite;
}

@keyframes inkFloat1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-30px, 20px); }
}
@keyframes inkFloat2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(40px, -20px); }
}
@keyframes inkFloat3 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-20px, 30px); }
}

.hero-content {
  max-width: var(--container-xl);
  margin: 0 auto;
  padding: var(--space-16) var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-16);
  position: relative;
  z-index: 1;
}

.hero-text {
  flex: 1;
  max-width: 600px;
}

.hero-seal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: var(--gradient-accent);
  color: white;
  font-family: var(--font-primary);
  font-size: var(--text-2xl);
  font-weight: var(--font-weight-bold);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-accent-glow);
  transform: rotate(-3deg);
  margin-bottom: var(--space-5);
}

.hero-title {
  font-family: var(--font-primary);
  font-size: var(--text-6xl);
  font-weight: var(--font-weight-bold);
  color: white;
  margin: 0 0 var(--space-4);
  letter-spacing: 0.1em;
  line-height: var(--line-height-tight);
}

.hero-subtitle {
  font-size: var(--text-2xl);
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 var(--space-4);
  font-weight: var(--font-weight-light);
  letter-spacing: 0.05em;
}

.hero-desc {
  font-size: var(--text-lg);
  color: rgba(255, 255, 255, 0.75);
  margin: 0 0 var(--space-8);
  line-height: var(--line-height-relaxed);
}

.hero-buttons {
  display: flex;
  gap: var(--space-4);
}

.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-full);
  font-size: var(--text-base);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  transition: all var(--transition-normal);
  cursor: pointer;
}

.hero-btn.primary {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 4px 20px rgba(74, 144, 164, 0.4);
}

.hero-btn.primary:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 30px rgba(74, 144, 164, 0.5);
}

.hero-btn.secondary {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.hero-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: white;
  transform: translateY(-3px);
}

/* Hero Visual */
.hero-visual {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.visual-container {
  position: relative;
  width: 340px;
  height: 340px;
}

.circle-main {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 280px;
  height: 280px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(74,144,164,0.2) 0%, rgba(45,97,114,0.3) 100%);
  border: 1px solid rgba(255,255,255,0.1);
  animation: mainPulse 4s ease-in-out infinite;
}

.circle-orb {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.15);
}

.orb-1 {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, rgba(199,105,61,0.15), rgba(199,105,61,0.05));
  animation: orbitSpin 8s linear infinite;
}

.orb-2 {
  top: 30%;
  left: 60%;
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, rgba(184,134,11,0.2), rgba(184,134,11,0.05));
  animation: floatOrb 5s ease-in-out infinite;
}

.orb-3 {
  top: 70%;
  left: 30%;
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, rgba(74,144,164,0.3), rgba(74,144,164,0.1));
  animation: floatOrb 6s ease-in-out infinite reverse;
}

.particle {
  position: absolute;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
}

.p1 { top: 20%; left: 30%; animation: particleFloat 4s ease-in-out infinite; }
.p2 { top: 60%; left: 70%; animation: particleFloat 5s ease-in-out infinite 1s; }
.p3 { top: 40%; left: 80%; animation: particleFloat 6s ease-in-out infinite 2s; }
.p4 { top: 75%; left: 20%; animation: particleFloat 4.5s ease-in-out infinite 0.5s; }

@keyframes mainPulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.05); }
}

@keyframes orbitSpin {
  0% { transform: translate(-50%, -50%) rotate(0deg); }
  100% { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes floatOrb {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(15px, -15px); }
}

@keyframes particleFloat {
  0%, 100% { transform: translateY(0); opacity: 0.6; }
  50% { transform: translateY(-20px); opacity: 1; }
}

/* 云纹分隔 */
.hero-cloud-divider {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
}

.hero-cloud-divider svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* ============ 通用容器 ============ */
.container {
  max-width: var(--container-xl);
  margin: 0 auto;
  padding: 0 var(--space-6);
}

/* ============ Section Header ============ */
.section-header {
  text-align: center;
  margin-bottom: var(--space-12);
}

.section-header.with-link {
  text-align: left;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.section-header .section-title {
  margin-bottom: var(--space-2);
}

.section-header .section-desc {
  font-size: var(--text-lg);
  color: var(--color-text-secondary);
  margin: 0;
}

.view-all {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-primary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
}

.view-all:hover {
  background: var(--color-primary-light);
}

/* ============ Features ============ */
.features-section {
  padding: var(--space-16) 0;
  background: var(--color-bg-paper);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-6);
}

.feature-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  padding: var(--space-8) var(--space-6);
  text-align: center;
  box-shadow: var(--shadow-card);
  transition: all var(--transition-normal);
  border: 1px solid transparent;
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: var(--shadow-card-hover);
  border-color: var(--color-primary-light);
}

.feature-icon {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--space-5);
  color: white;
  box-shadow: var(--shadow-md);
}

.feature-card h3 {
  font-family: var(--font-primary);
  font-size: var(--text-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

.feature-card p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--line-height-relaxed);
  margin: 0 0 var(--space-5);
}

.feature-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  color: var(--color-primary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-sm);
  transition: gap var(--transition-fast);
}

.feature-link:hover {
  gap: var(--space-2);
}

/* ============ Highlights ============ */
.highlights-section {
  padding: var(--space-16) 0;
  background: var(--gradient-paper);
}

.highlights-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-6);
}

.highlight-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  transition: all var(--transition-normal);
}

.highlight-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-card-hover);
}

.highlight-image {
  height: 200px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.highlight-emoji {
  font-size: 5rem;
}

.highlight-category {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary);
  color: white;
  font-size: var(--text-xs);
  font-weight: var(--font-weight-medium);
  border-radius: var(--radius-full);
}

.highlight-info {
  padding: var(--space-5);
}

.highlight-info h4 {
  font-family: var(--font-primary);
  font-size: var(--text-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.highlight-author {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-3);
}

.highlight-stats {
  display: flex;
  gap: var(--space-5);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.highlight-stats span {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

/* ============ Stats ============ */
.stats-section {
  padding: var(--space-12) 0;
  background: var(--gradient-hero);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-6);
  text-align: center;
}

.stat-item {
  padding: var(--space-4);
}

.stat-number {
  font-family: var(--font-primary);
  font-size: var(--text-5xl);
  font-weight: var(--font-weight-bold);
  color: white;
  line-height: 1;
  margin-bottom: var(--space-3);
}

.stat-divider {
  width: 40px;
  height: 3px;
  background: var(--gradient-primary);
  margin: 0 auto var(--space-3);
  border-radius: 2px;
}

.stat-label {
  font-size: var(--text-base);
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: 0.1em;
}

/* ============ CTA ============ */
.cta-section {
  padding: var(--space-16) 0;
  background: var(--color-bg-paper);
}

.cta-card {
  position: relative;
  background: var(--color-bg-card);
  border-radius: var(--radius-2xl);
  padding: var(--space-12) var(--space-8);
  text-align: center;
  box-shadow: var(--shadow-xl);
  overflow: hidden;
}

.cta-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--gradient-primary);
}

.cta-decoration-left,
.cta-decoration-right {
  position: absolute;
  width: 80px;
  height: 80px;
  opacity: 0.3;
}

.cta-decoration-left {
  top: var(--space-6);
  left: var(--space-6);
}

.cta-decoration-right {
  bottom: var(--space-6);
  right: var(--space-6);
}

.cta-content {
  position: relative;
  z-index: 1;
}

.cta-content h2 {
  font-family: var(--font-primary);
  font-size: var(--text-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

.cta-content p {
  font-size: var(--text-lg);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-8);
}

.cta-buttons {
  display: flex;
  justify-content: center;
  gap: var(--space-4);
}

.btn-cta {
  display: inline-flex;
  align-items: center;
  padding: var(--space-3) var(--space-8);
  border-radius: var(--radius-full);
  font-size: var(--text-base);
  font-weight: var(--font-weight-medium);
  text-decoration: none;
  transition: all var(--transition-normal);
}

.btn-cta.primary {
  background: var(--gradient-primary);
  color: white;
  box-shadow: var(--shadow-md);
}

.btn-cta.primary:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.btn-cta.ghost {
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-border);
}

.btn-cta.ghost:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

/* ============ 响应式 ============ */
@media (max-width: 1024px) {
  .hero-content {
    padding: var(--space-12) var(--space-6);
    gap: var(--space-10);
  }

  .hero-title {
    font-size: var(--text-5xl);
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .highlights-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-8);
  }
}

@media (max-width: 768px) {
  .hero-section {
    min-height: auto;
  }

  .hero-content {
    flex-direction: column;
    text-align: center;
    padding: var(--space-10) var(--space-5);
  }

  .hero-title {
    font-size: var(--text-4xl);
  }

  .hero-subtitle {
    font-size: var(--text-xl);
  }

  .hero-desc {
    font-size: var(--text-base);
  }

  .hero-buttons {
    justify-content: center;
    flex-wrap: wrap;
  }

  .hero-visual {
    display: none;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .highlights-grid {
    grid-template-columns: 1fr;
  }

  .section-header.with-link {
    flex-direction: column;
    gap: var(--space-4);
    align-items: flex-start;
  }

  .cta-content h2 {
    font-size: var(--text-3xl);
  }

  .cta-buttons {
    flex-direction: column;
    align-items: center;
  }
}

@media (max-width: 480px) {
  .hero-title {
    font-size: var(--text-3xl);
    letter-spacing: 0.05em;
  }

  .features-section,
  .highlights-section,
  .cta-section {
    padding: var(--space-10) 0;
  }

  .stats-section {
    padding: var(--space-8) 0;
  }

  .stat-number {
    font-size: var(--text-3xl);
  }
}
</style>