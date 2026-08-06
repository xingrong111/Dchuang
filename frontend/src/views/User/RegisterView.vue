<template>
  <div class="register-page">
    <div class="register-bg-decoration">
      <div class="ink-wash ink-1"></div>
      <div class="ink-wash ink-2"></div>
      <div class="ink-wash ink-3"></div>
    </div>
    <div class="register-container">
      <div class="register-header">
        <div class="seal-stamp register-seal">锡</div>
        <h2>智绘锡承</h2>
        <p>非遗数字创新平台 · 加入我们</p>
      </div>

      <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-width="0" class="register-form">
        <el-form-item prop="username">
          <el-input
            v-model="registerForm.username"
            type="text"
            placeholder="请输入用户名"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="email">
          <el-input
            v-model="registerForm.email"
            type="email"
            placeholder="请输入邮箱"
            prefix-icon="Message"
            size="large"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <div class="agreement">
            <el-checkbox v-model="registerForm.agree">
              我已阅读并同意
              <a href="#" class="agreement-link">《用户协议》</a>
              和
              <a href="#" class="agreement-link">《隐私政策》</a>
            </el-checkbox>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="register-btn"
            :loading="loading"
            @click="handleRegister"
          >
            <span v-if="loading">注册中...</span>
            <span v-else>注 册</span>
          </el-button>
        </el-form-item>
      </el-form>

      <div class="register-footer">
        <span>已有账号？</span>
        <router-link to="/login" class="login-link">立即登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Message, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/userStore'

const registerFormRef = ref(null)
const loading = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agree: false
})

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3-20个字符之间', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9\u4e00-\u9fa5]+$/, message: '用户名只能包含字母、数字和中文', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
    { pattern: /^(?=.*[a-zA-Z])(?=.*[0-9])/, message: '密码需包含字母和数字', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const router = useRouter()
const userStore = useUserStore()

const handleRegister = async () => {
  if (!registerFormRef.value) return

  if (!registerForm.agree) {
    ElMessage.warning('请先阅读并同意用户协议和隐私政策')
    return
  }

  try {
    await registerFormRef.value.validate()
  } catch (error) {
    return
  }

  loading.value = true

  try {
    const response = await userStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })

    if (response && response.code === 200) {
      ElMessage.success('注册成功，请登录')
      router.push('/login')
    } else {
      ElMessage.error(response?.message || '注册失败')
    }
  } catch (error) {
    console.error('注册失败:', error)
    ElMessage.error(error.response?.data?.message || '注册失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #2d6172 0%, #1a3d4a 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

.register-bg-decoration {
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
  right: -100px;
}

.ink-2 {
  width: 350px;
  height: 350px;
  background: #c7693d;
  bottom: -80px;
  left: -80px;
}

.ink-3 {
  width: 250px;
  height: 250px;
  background: #b8860b;
  bottom: 30%;
  left: 10%;
  opacity: 0.1;
}

.register-container {
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1);
  padding: 48px 40px;
  width: 100%;
  max-width: 460px;
  position: relative;
  z-index: 1;
}

.register-header {
  text-align: center;
  margin-bottom: 32px;
}

.register-seal {
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

.register-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #2c3e50;
  font-weight: 700;
  font-family: var(--font-primary);
  letter-spacing: 0.05em;
}

.register-header p {
  margin: 0;
  color: #5d6d7e;
  font-size: 14px;
  letter-spacing: 0.1em;
}

.register-form {
  margin-bottom: 20px;
}

.register-form .el-form-item {
  margin-bottom: 18px;
}

.agreement {
  font-size: 13px;
  color: #5d6d7e;
}

.agreement-link {
  color: #4a90a4;
  text-decoration: none;
  transition: color 0.2s;
}

.agreement-link:hover {
  color: #2d6172;
}

.register-btn {
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

.register-btn:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 20px rgba(74, 144, 164, 0.4) !important;
  filter: brightness(1.05);
}

.register-btn:active {
  transform: translateY(0) !important;
}

.register-footer {
  text-align: center;
}

.register-footer span {
  color: #5d6d7e;
  font-size: 14px;
}

.login-link {
  color: #4a90a4;
  text-decoration: none;
  font-weight: 600;
  margin-left: 5px;
  transition: color 0.2s;
}

.login-link:hover {
  color: #2d6172;
}
</style>
