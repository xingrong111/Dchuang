<template>
  <div class="login-page">
    <div class="login-bg-decoration">
      <div class="ink-wash ink-1"></div>
      <div class="ink-wash ink-2"></div>
      <div class="ink-wash ink-3"></div>
    </div>
    <div class="login-container">
      <div class="login-header">
        <div class="seal-stamp login-seal">锡</div>
        <h2>智绘锡承</h2>
        <p>非遗数字创新平台</p>
      </div>

      <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-width="0" class="login-form">
        <el-form-item prop="email">
          <el-input
            v-model="loginForm.email"
            type="email"
            placeholder="请输入邮箱"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <div class="form-options">
            <el-checkbox v-model="loginForm.rememberMe">记住我</el-checkbox>
            <a href="#" class="forgot-link">忘记密码？</a>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            <span v-if="loading">登录中...</span>
            <span v-else>登 录</span>
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span>还没有账号？</span>
        <router-link to="/register" class="register-link">立即注册</router-link>
      </div>

      <div class="divider">
        <span>其他登录方式</span>
      </div>

      <div class="social-login">
        <el-button icon="User" type="default" size="large" circle>微信</el-button>
        <el-button icon="User" type="default" size="large" circle>QQ</el-button>
        <el-button icon="User" type="default" size="large" circle>微博</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/userStore'

const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  email: '',
  password: '',
  rememberMe: false
})

const loginRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const handleLogin = async () => {
  if (!loginFormRef.value) return

  try {
    await loginFormRef.value.validate()
  } catch (error) {
    return
  }

  loading.value = true

  try {
    const response = await userStore.login({
      email: loginForm.email,
      password: loginForm.password
    })

    if (response && response.code === 200) {
      ElMessage.success('登录成功')
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } else {
      ElMessage.error(response?.message || '登录失败，请检查邮箱和密码')
    }
  } catch (error) {
    console.error('登录失败:', error)
    ElMessage.error(error.response?.data?.message || '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #2d6172 0%, #1a3d4a 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.login-bg-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.ink-wash {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.15;
}

.ink-1 {
  width: 400px;
  height: 400px;
  background: #4a90a4;
  top: -100px;
  left: -100px;
}

.ink-2 {
  width: 350px;
  height: 350px;
  background: #c7693d;
  bottom: -80px;
  right: -80px;
}

.ink-3 {
  width: 250px;
  height: 250px;
  background: #b8860b;
  top: 40%;
  right: 10%;
  opacity: 0.1;
}

.login-container {
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1);
  padding: 48px 40px;
  width: 100%;
  max-width: 420px;
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-seal {
  width: 56px;
  height: 56px;
  font-size: 1.75rem;
  margin: 0 auto 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #c7693d 0%, #a8552f 100%);
  color: white;
  font-family: var(--font-primary);
  font-weight: 700;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(199, 105, 61, 0.4);
  transform: rotate(-2deg);
}

.login-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #2c3e50;
  font-weight: 700;
  font-family: var(--font-primary);
  letter-spacing: 0.05em;
}

.login-header p {
  margin: 0;
  color: #5d6d7e;
  font-size: 14px;
  letter-spacing: 0.1em;
}

.login-form {
  margin-bottom: 20px;
}

.login-form .el-form-item {
  margin-bottom: 20px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.forgot-link {
  color: #4a90a4;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}

.forgot-link:hover {
  color: #2d6172;
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.1em;
  background: linear-gradient(135deg, #4a90a4 0%, #2d6172 100%) !important;
  border: none !important;
  border-radius: 24px !important;
  transition: all 0.3s ease !important;
}

.login-btn:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 20px rgba(74, 144, 164, 0.4) !important;
  filter: brightness(1.05);
}

.login-btn:active {
  transform: translateY(0) !important;
}

.login-footer {
  text-align: center;
  margin-bottom: 25px;
}

.login-footer span {
  color: #5d6d7e;
  font-size: 14px;
}

.register-link {
  color: #4a90a4;
  text-decoration: none;
  font-weight: 600;
  margin-left: 5px;
  transition: color 0.2s;
}

.register-link:hover {
  color: #2d6172;
}

.divider {
  text-align: center;
  margin-bottom: 20px;
  position: relative;
}

.divider span {
  background: rgba(255, 255, 255, 0.96);
  padding: 0 15px;
  color: #95a5a6;
  font-size: 12px;
  letter-spacing: 0.05em;
}

.divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #e8e4da;
  z-index: 0;
}

.divider span {
  position: relative;
  z-index: 1;
}

.social-login {
  display: flex;
  justify-content: center;
  gap: 20px;
}

.social-login .el-button {
  width: 48px;
  height: 48px;
  border-color: #e8e4da;
  background: white;
  transition: all 0.3s ease;
}

.social-login .el-button:hover {
  background: #f5f9fa;
  border-color: #4a90a4;
  color: #4a90a4;
  transform: translateY(-2px);
}
</style>
