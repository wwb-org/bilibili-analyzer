<template>
  <div class="register-page">
    <!-- 注册区域 -->
    <div class="card-container">
      <!-- Logo区域 -->
      <div class="logo-wrapper">
        <img src="@/bilibili.svg" alt="Bilibili Logo" class="logo-img" />
      </div>
      <!-- 系统名称 -->
      <h1 class="page-title">用户注册</h1>
      <!-- 注册表单 -->
      <form class="register-form" @submit.prevent="handleRegister">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input
            type="text"
            class="form-input"
            v-model="form.username"
            placeholder="请输入用户名（3-20个字符）"
          />
          <span class="form-error" v-if="errors.username">{{ errors.username }}</span>
        </div>
        <div class="form-group">
          <label class="form-label">邮箱</label>
          <input
            type="email"
            class="form-input"
            v-model="form.email"
            placeholder="请输入邮箱"
          />
          <span class="form-error" v-if="errors.email">{{ errors.email }}</span>
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input
            type="password"
            class="form-input"
            v-model="form.password"
            placeholder="请输入密码（至少6位）"
          />
          <span class="form-error" v-if="errors.password">{{ errors.password }}</span>
        </div>
        <div class="form-group">
          <label class="form-label">确认密码</label>
          <input
            type="password"
            class="form-input"
            v-model="form.confirmPassword"
            placeholder="请再次输入密码"
          />
          <span class="form-error" v-if="errors.confirmPassword">{{ errors.confirmPassword }}</span>
        </div>
        <button type="submit" class="btn-primary" :disabled="loading">
          <span class="btn-spinner" v-if="loading"></span>
          <span>{{ loading ? '注册中...' : '注册' }}</span>
        </button>
        <div class="form-footer">
          <span>已有账号？</span>
          <router-link to="/login" class="link-primary">立即登录</router-link>
        </div>
      </form>
    </div>
    <!-- Toast提示 -->
    <Transition name="toast">
      <div class="toast" :class="toast.type" v-if="toast.show">
        {{ toast.message }}
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import request from '@/api'

const router = useRouter()
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const errors = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const toast = reactive({
  show: false,
  message: '',
  type: 'success'
})

const showToast = (message, type = 'success') => {
  toast.message = message
  toast.type = type
  toast.show = true
  setTimeout(() => {
    toast.show = false
  }, 3000)
}

const validateForm = () => {
  let valid = true

  // 用户名验证
  if (!form.username.trim()) {
    errors.username = '请输入用户名'
    valid = false
  } else if (form.username.length < 3 || form.username.length > 20) {
    errors.username = '用户名长度在3-20个字符'
    valid = false
  } else {
    errors.username = ''
  }

  // 邮箱验证
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!form.email.trim()) {
    errors.email = '请输入邮箱'
    valid = false
  } else if (!emailRegex.test(form.email)) {
    errors.email = '请输入正确的邮箱格式'
    valid = false
  } else {
    errors.email = ''
  }

  // 密码验证
  if (!form.password) {
    errors.password = '请输入密码'
    valid = false
  } else if (form.password.length < 6) {
    errors.password = '密码长度不能少于6位'
    valid = false
  } else {
    errors.password = ''
  }

  // 确认密码验证
  if (!form.confirmPassword) {
    errors.confirmPassword = '请再次输入密码'
    valid = false
  } else if (form.confirmPassword !== form.password) {
    errors.confirmPassword = '两次输入的密码不一致'
    valid = false
  } else {
    errors.confirmPassword = ''
  }

  return valid
}

const handleRegister = async () => {
  if (!validateForm()) return

  loading.value = true
  try {
    await request.post('/api/auth/register', {
      username: form.username,
      email: form.email,
      password: form.password
    })
    showToast('注册成功，请登录', 'success')
    setTimeout(() => router.push('/login'), 500)
  } catch (error) {
    showToast(error.response?.data?.detail || '注册失败', 'error')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 页面背景 - 网格图案 */
.register-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: var(--bg-gray-light);
  background-image:
    linear-gradient(var(--bg-gray-dark) 1px, transparent 1px),
    linear-gradient(90deg, var(--bg-gray-dark) 1px, transparent 1px);
  background-size: 30px 30px;
}

/* 注册容器 */
.card-container {
  width: 480px;
  padding: 40px 50px;
  background-color: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 12px;
}

/* Logo区域 */
.logo-wrapper {
  display: flex;
  justify-content: center;
}

.logo-img {
  width: 80px;
  height: auto;
}

/* 标题 */
.page-title {
  margin: 16px 0 24px 0;
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary);
}

/* 表单组 */
.form-group {
  margin-bottom: 18px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.form-input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary);
  background-color: var(--bg-white);
  outline: none;
  transition: border-color 0.1s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--bili-blue);
}

.form-input::placeholder {
  color: var(--text-placeholder);
}

.form-error {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-error);
}

/* 按钮 */
.btn-primary {
  width: 100%;
  height: 46px;
  margin-top: 8px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #fff;
  background-color: var(--bili-blue);
  cursor: pointer;
  transition: background-color 0.1s;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--bili-blue-hover);
}

.btn-primary:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

/* 加载动画 */
@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* 页脚 */
.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary);
}

.link-primary {
  color: var(--bili-blue);
  text-decoration: none;
  margin-left: 4px;
}

.link-primary:hover {
  color: var(--bili-blue-hover);
}

/* Toast提示 */
.toast {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  color: #fff;
  z-index: 1000;
}

.toast.success {
  background-color: var(--color-success);
}

.toast.error {
  background-color: var(--color-error);
}

/* Toast动画 */
.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}
</style>
