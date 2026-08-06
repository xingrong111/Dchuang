<template>
  <div id="app">
    <!-- 顶部导航栏 -->
    <nav class="app-nav">
      <div class="nav-container">
        <div class="nav-left">
          <router-link to="/" class="logo">
            <div class="logo-icon">
              <span class="logo-text-svg">锡</span>
            </div>
            <span class="logo-text">智绘锡承</span>
          </router-link>

          <div class="nav-links">
            <router-link to="/" class="nav-link">
              <el-icon><HomeFilled /></el-icon>
              <span>首页</span>
            </router-link>
            <router-link to="/museum" class="nav-link">
              <el-icon><OfficeBuilding /></el-icon>
              <span>数字博物馆</span>
            </router-link>
            <router-link to="/workshop" class="nav-link">
              <el-icon><Brush /></el-icon>
              <span>AI共创工坊</span>
            </router-link>
            <router-link to="/community" class="nav-link">
              <el-icon><ChatLineSquare /></el-icon>
              <span>社区广场</span>
            </router-link>
            <router-link to="/shop" class="nav-link">
              <el-icon><ShoppingBag /></el-icon>
              <span>文创商城</span>
            </router-link>
          </div>
        </div>

        <div class="nav-right">
          <template v-if="userStore.user">
            <router-link to="/profile" class="profile-btn">
              <div class="avatar">
                <el-icon :size="16"><User /></el-icon>
              </div>
              <span>{{ userStore.user.username || userStore.user.email }}</span>
            </router-link>
            <button class="logout-btn" @click="handleLogout">
              <el-icon :size="16"><SwitchButton /></el-icon>
              <span>退出</span>
            </button>
          </template>
          <template v-else>
            <router-link to="/login" class="auth-link login">登录</router-link>
            <router-link to="/register" class="auth-link register">
              <span>立即注册</span>
            </router-link>
          </template>
        </div>

        <button class="mobile-menu-btn" @click="showMobileMenu = !showMobileMenu">
          <el-icon :size="24"><Menu /></el-icon>
        </button>
      </div>

      <transition name="slide-fade">
        <div v-if="showMobileMenu" class="mobile-menu">
          <router-link to="/" class="mobile-nav-link" @click="showMobileMenu = false">
            <el-icon><HomeFilled /></el-icon> 首页
          </router-link>
          <router-link to="/museum" class="mobile-nav-link" @click="showMobileMenu = false">
            <el-icon><OfficeBuilding /></el-icon> 数字博物馆
          </router-link>
          <router-link to="/workshop" class="mobile-nav-link" @click="showMobileMenu = false">
            <el-icon><Brush /></el-icon> AI共创工坊
          </router-link>
          <router-link to="/community" class="mobile-nav-link" @click="showMobileMenu = false">
            <el-icon><ChatLineSquare /></el-icon> 社区广场
          </router-link>
          <router-link to="/shop" class="mobile-nav-link" @click="showMobileMenu = false">
            <el-icon><ShoppingBag /></el-icon> 文创商城
          </router-link>
          <div class="mobile-auth" v-if="!userStore.user">
            <router-link to="/login" class="mobile-auth-link" @click="showMobileMenu = false">登录</router-link>
            <router-link to="/register" class="mobile-auth-link primary" @click="showMobileMenu = false">注册</router-link>
          </div>
        </div>
      </transition>
    </nav>

    <!-- 主内容区 -->
    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 页脚 -->
    <footer class="app-footer">
      <div class="footer-pattern"></div>
      <div class="footer-content">
        <div class="footer-section">
          <div class="footer-brand">
            <div class="footer-logo">锡</div>
            <h4>智绘锡承</h4>
          </div>
          <p class="footer-desc">
            非遗数字创新平台，致力于让传统非遗在数字时代焕发新生。
            以AI为笔，以3D为墨，绘就江南非遗新画卷。
          </p>
        </div>
        <div class="footer-section">
          <h4>快速链接</h4>
          <router-link to="/museum">
            <el-icon><OfficeBuilding /></el-icon> 数字博物馆
          </router-link>
          <router-link to="/workshop">
            <el-icon><Brush /></el-icon> AI共创工坊
          </router-link>
          <router-link to="/community">
            <el-icon><ChatLineSquare /></el-icon> 社区广场
          </router-link>
          <router-link to="/shop">
            <el-icon><ShoppingBag /></el-icon> 文创商城
          </router-link>
        </div>
        <div class="footer-section">
          <h4>联系我们</h4>
          <p><el-icon><Message /></el-icon> contact@zhihui-xicheng.com</p>
          <p><el-icon><Location /></el-icon> 江苏省无锡市</p>
          <p><el-icon><Clock /></el-icon> 周一至周日 9:00-21:00</p>
        </div>
        <div class="footer-section">
          <h4>关注我们</h4>
          <p class="footer-follow">扫码关注公众号，获取最新动态</p>
          <div class="social-links">
            <div class="social-item">
              <el-icon :size="22"><ChatDotRound /></el-icon>
              <span>微信</span>
            </div>
            <div class="social-item">
              <el-icon :size="22"><UserFilled /></el-icon>
              <span>微博</span>
            </div>
            <div class="social-item">
              <el-icon :size="22"><Picture /></el-icon>
              <span>抖音</span>
            </div>
          </div>
        </div>
      </div>
      <div class="footer-bottom">
        <div class="footer-bottom-content">
          <p>&copy; 2024 智绘锡承 · 江南非遗数字创新平台</p>
          <div class="footer-links">
            <span>关于我们</span>
            <span class="divider">|</span>
            <span>使用条款</span>
            <span class="divider">|</span>
            <span>隐私政策</span>
            <span class="divider">|</span>
            <span>帮助中心</span>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/userStore'
import {
  HomeFilled,
  OfficeBuilding,
  Brush,
  ChatLineSquare,
  ShoppingBag,
  User,
  SwitchButton,
  Menu,
  ChatDotRound,
  UserFilled,
  Picture,
  Message,
  Location,
  Clock
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const showMobileMenu = ref(false)

onMounted(() => {
  if (userStore.user) {
    userStore.fetchUserInfo().catch(() => {})
  }
})

const handleLogout = () => {
  userStore.logout()
  router.push('/login')
  showMobileMenu.value = false
}
</script>

<style scoped>
#app {
  font-family: var(--font-secondary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--color-text-primary);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-paper);
}

/* ============ 导航栏 ============ */
.app-nav {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: 1000;
  border-bottom: 1px solid var(--color-border-light);
}

.nav-container {
  max-width: var(--container-2xl);
  margin: 0 auto;
  padding: 0 var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: var(--nav-height);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: var(--space-10);
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
  color: var(--color-text-primary);
}

.logo-icon {
  width: 38px;
  height: 38px;
  background: var(--gradient-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-glow);
  transition: transform var(--transition-fast);
}

.logo:hover .logo-icon {
  transform: rotate(-5deg) scale(1.05);
}

.logo-text-svg {
  color: white;
  font-family: var(--font-primary);
  font-size: var(--text-lg);
  font-weight: var(--font-weight-bold);
}

.logo-text {
  font-family: var(--font-primary);
  font-size: var(--text-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  letter-spacing: 0.1em;
}

.nav-links {
  display: flex;
  gap: var(--space-1);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  position: relative;
}

.nav-link:hover {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.nav-link.router-link-exact-active {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.nav-link.router-link-exact-active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 3px;
  background: var(--gradient-primary);
  border-radius: 2px;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.auth-link {
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
}

.auth-link:hover {
  color: var(--color-primary);
}

.auth-link.register {
  background: var(--gradient-primary);
  color: var(--color-text-inverse);
}

.auth-link.register:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.profile-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-primary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  transition: all var(--transition-fast);
}

.profile-btn:hover {
  background: var(--color-bg-secondary);
}

.avatar {
  width: 32px;
  height: 32px;
  background: var(--gradient-primary);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  background: transparent;
  color: var(--color-text-muted);
  border: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.logout-btn:hover {
  color: var(--color-danger);
  background: rgba(229, 115, 115, 0.1);
}

.mobile-menu-btn {
  display: none;
  background: transparent;
  border: none;
  color: var(--color-text-primary);
  cursor: pointer;
  padding: var(--space-2);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.mobile-menu-btn:hover {
  background: var(--color-bg-secondary);
}

/* ============ 移动端菜单 ============ */
.mobile-menu {
  position: absolute;
  top: var(--nav-height);
  left: 0;
  right: 0;
  background: white;
  box-shadow: var(--shadow-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  border-bottom: 1px solid var(--color-border-light);
}

.mobile-nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-text-primary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-base);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
}

.mobile-nav-link:hover {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.mobile-auth {
  display: flex;
  gap: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
  margin-top: var(--space-2);
}

.mobile-auth-link {
  flex: 1;
  text-align: center;
  padding: var(--space-3);
  border-radius: var(--radius-full);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  font-size: var(--text-sm);
  transition: all var(--transition-fast);
}

.mobile-auth-link:not(.primary) {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.mobile-auth-link.primary {
  color: var(--color-text-inverse);
  background: var(--gradient-primary);
}

/* ============ 主内容区 ============ */
.app-main {
  flex: 1;
}

/* 页面过渡 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-normal), transform var(--transition-normal);
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all var(--transition-normal);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ============ 页脚 ============ */
.app-footer {
  background: var(--color-bg-dark);
  color: white;
  position: relative;
  margin-top: var(--space-16);
  overflow: hidden;
}

.footer-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-primary);
}

.footer-content {
  max-width: var(--container-2xl);
  margin: 0 auto;
  padding: var(--space-10) var(--space-6) var(--space-8);
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: var(--space-8);
}

.footer-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.footer-logo {
  width: 44px;
  height: 44px;
  background: var(--gradient-accent);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-family: var(--font-primary);
  font-size: var(--text-xl);
  font-weight: var(--font-weight-bold);
  box-shadow: var(--shadow-accent-glow);
}

.footer-section h4 {
  font-family: var(--font-primary);
  font-size: var(--text-lg);
  font-weight: var(--font-weight-semibold);
  margin: 0 0 var(--space-4);
  color: white;
}

.footer-desc {
  color: rgba(255, 255, 255, 0.65);
  font-size: var(--text-sm);
  line-height: var(--line-height-relaxed);
  margin: 0;
}

.footer-section a {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  font-size: var(--text-sm);
  padding: var(--space-2) 0;
  transition: all var(--transition-fast);
}

.footer-section a:hover {
  color: var(--color-primary-light);
  transform: translateX(4px);
}

.footer-section p {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: rgba(255, 255, 255, 0.65);
  font-size: var(--text-sm);
  margin: 0 0 var(--space-2);
}

.footer-section p .el-icon {
  color: var(--color-primary);
}

.footer-follow {
  color: rgba(255, 255, 255, 0.55);
  font-size: var(--text-sm);
  margin: 0 0 var(--space-4);
}

.social-links {
  display: flex;
  gap: var(--space-4);
}

.social-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.social-item:hover {
  color: var(--color-primary-light);
  transform: translateY(-2px);
}

.social-item span {
  font-size: var(--text-xs);
}

.footer-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding: var(--space-5) var(--space-6);
}

.footer-bottom-content {
  max-width: var(--container-2xl);
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.footer-bottom p {
  color: rgba(255, 255, 255, 0.45);
  font-size: var(--text-sm);
  margin: 0;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.footer-links span {
  color: rgba(255, 255, 255, 0.45);
  transition: color var(--transition-fast);
  cursor: pointer;
}

.footer-links span:hover {
  color: var(--color-primary-light);
}

.footer-links .divider {
  color: rgba(255, 255, 255, 0.2);
  cursor: default;
}

.footer-links .divider:hover {
  color: rgba(255, 255, 255, 0.2);
}

/* ============ 响应式 ============ */
@media (max-width: 1024px) {
  .nav-links {
    gap: var(--space-1);
  }

  .nav-link {
    padding: var(--space-2) var(--space-3);
  }

  .nav-link span {
    display: none;
  }

  .nav-link .el-icon {
    font-size: var(--text-lg);
  }

  .footer-content {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .nav-links {
    display: none;
  }

  .nav-right {
    display: none;
  }

  .mobile-menu-btn {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .nav-container {
    padding: 0 var(--space-4);
  }

  .footer-content {
    grid-template-columns: 1fr;
    gap: var(--space-6);
    padding: var(--space-8) var(--space-4);
  }

  .footer-bottom-content {
    flex-direction: column;
    text-align: center;
  }

  .app-footer {
    padding-bottom: var(--space-4);
  }
}
</style>
