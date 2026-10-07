<template>
  <div class="forgot-password page-container">
    <div class="forgot-card">
      <h2 class="title">找回密码</h2>
      <p class="subtitle">通过邮箱验证码重置密码</p>

      <!-- 步骤1: 输入邮箱 -->
      <div v-if="step === 1" class="step">
        <el-form ref="emailFormRef" :model="emailForm" :rules="emailRules" @submit.prevent="sendCode">
          <el-form-item prop="email">
            <el-input
              v-model="emailForm.email"
              placeholder="请输入注册邮箱"
              size="large"
              :prefix-icon="Message"
              clearable
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            class="action-btn"
            :loading="sendingCode"
            @click="sendCode"
          >
            {{ countdown > 0 ? `${countdown}s 后可重新发送` : '发送验证码' }}
          </el-button>
        </el-form>
      </div>

      <!-- 步骤2: 输入验证码 + 新密码 -->
      <div v-if="step === 2" class="step">
        <el-alert type="info" :closable="false" class="email-hint">
          验证码已发送至 <b>{{ emailForm.email }}</b>
          <span v-if="isDevMode">（开发模式：请查看后端控制台）</span>
        </el-alert>
        <el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" @submit.prevent="handleReset">
          <el-form-item prop="code">
            <el-input
              v-model="resetForm.code"
              placeholder="6 位验证码"
              size="large"
              maxlength="6"
              :prefix-icon="Key"
              clearable
            />
          </el-form-item>
          <el-form-item prop="new_password">
            <el-input
              v-model="resetForm.new_password"
              type="password"
              placeholder="新密码（至少 6 位）"
              size="large"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
          <el-form-item prop="confirm_password">
            <el-input
              v-model="resetForm.confirm_password"
              type="password"
              placeholder="确认新密码"
              size="large"
              :prefix-icon="Lock"
              show-password
              clearable
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            class="action-btn"
            :loading="resetting"
            @click="handleReset"
          >
            重置密码
          </el-button>
        </el-form>
        <el-button text class="back-link" @click="step = 1">← 返回上一步</el-button>
      </div>

      <!-- 步骤3: 重置成功 -->
      <div v-if="step === 3" class="step success-step">
        <el-icon size="64" color="#67C23A"><SuccessFilled /></el-icon>
        <p>密码重置成功！</p>
        <el-button type="primary" size="large" class="action-btn" @click="$router.push('/login')">
          去登录
        </el-button>
      </div>

      <div class="footer">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Message, Key, Lock, SuccessFilled } from '@element-plus/icons-vue'
import { ref, onUnmounted } from 'vue'

import { ElMessage } from 'element-plus'
import { forgotPassword, resetPassword } from '@/api/auth'



const step = ref(1)
const sendingCode = ref(false)
const resetting = ref(false)
const countdown = ref(0)
let timer = null

// 开发模式提示（SMTP 未配置时后端会打印验证码到控制台）
const isDevMode = import.meta.env.DEV

const emailFormRef = ref()
const resetFormRef = ref()

const emailForm = ref({ email: '' })
const resetForm = ref({ code: '', new_password: '', confirm_password: '' })

const emailRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

const validateConfirm = (rule, value, callback) => {
  if (value !== resetForm.value.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const resetRules = {
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为 6 位', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

const sendCode = async () => {
  if (!emailFormRef.value) return
  await emailFormRef.value.validate(async (valid) => {
    if (!valid) return
    sendingCode.value = true
    try {
      await forgotPassword(emailForm.value.email)
      ElMessage.success('验证码已发送')
      step.value = 2
      countdown.value = 60
      timer = setInterval(() => {
        countdown.value--
        if (countdown.value <= 0) clearInterval(timer)
      }, 1000)
    } catch (e) {
      ElMessage.error(e.message || '发送失败')
    } finally {
      sendingCode.value = false
    }
  })
}

const handleReset = async () => {
  if (!resetFormRef.value) return
  await resetFormRef.value.validate(async (valid) => {
    if (!valid) return
    resetting.value = true
    try {
      await resetPassword({
        email: emailForm.value.email,
        code: resetForm.value.code,
        new_password: resetForm.value.new_password,
      })
      step.value = 3
      ElMessage.success('密码重置成功')
    } catch (e) {
      ElMessage.error(e.message || '重置失败')
    } finally {
      resetting.value = false
    }
  })
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.forgot-password {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.forgot-card {
  background: #fff;
  border-radius: 16px;
  padding: 40px;
  width: 440px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.title {
  text-align: center;
  font-size: 24px;
  margin: 0 0 8px;
  color: #303133;
}

.subtitle {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin: 0 0 32px;
}

.step {
  margin-bottom: 20px;
}

.action-btn {
  width: 100%;
  margin-top: 8px;
}

.email-hint {
  margin-bottom: 20px;
}

.back-link {
  width: 100%;
  margin-top: 12px;
}

.success-step {
  text-align: center;
  padding: 20px 0;
}

.success-step p {
  font-size: 18px;
  color: #303133;
  margin: 16px 0 24px;
}

.footer {
  text-align: center;
  margin-top: 24px;
}

.footer a {
  color: #409EFF;
  text-decoration: none;
  font-size: 14px;
}

.footer a:hover {
  text-decoration: underline;
}
</style>
