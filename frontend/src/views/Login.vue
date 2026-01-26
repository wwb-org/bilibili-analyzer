<template>
  <div class="login-page">
    <!-- 左侧：瀑布流背景区域 -->
    <div class="left-section">
      <div class="brand-info">
        <img src="@/bilibili.svg" alt="Logo" class="brand-logo" />
        <h1 class="brand-title">B站视频趋势分析系统</h1>
        <p class="brand-desc">基于大数据的视频内容趋势分析平台</p>
      </div>
    </div>

    <!-- 右侧：登录表单区域 -->
    <div class="right-section">
      <div class="form-container">
        <h2 class="form-title">欢迎回来</h2>
        <p class="form-subtitle">请登录您的账号</p>

        <form class="login-form" @submit.prevent="handleLogin">
          <div class="form-group">
            <label class="form-label">用户名</label>
            <input
              type="text"
              class="form-input"
              v-model="form.username"
              placeholder="请输入用户名"
            />
            <span class="form-error" v-if="errors.username">{{ errors.username }}</span>
          </div>
          <div class="form-group">
            <label class="form-label">密码</label>
            <input
              type="password"
              class="form-input"
              v-model="form.password"
              placeholder="请输入密码"
            />
            <span class="form-error" v-if="errors.password">{{ errors.password }}</span>
          </div>
          <button type="submit" class="btn-primary" :disabled="loading">
            <span class="btn-spinner" v-if="loading"></span>
            <span>{{ loading ? '登录中...' : '登录' }}</span>
          </button>
          <div class="form-footer">
            <span>没有账号？</span>
            <router-link to="/register" class="link-primary">立即注册</router-link>
          </div>
        </form>
      </div>
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
import { login } from '@/api/auth'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const errors = reactive({
  username: '',
  password: ''
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

const validateField = (field) => {
  if (field === 'username') {
    errors.username = form.username.trim() ? '' : '请输入用户名'
  } else if (field === 'password') {
    errors.password = form.password ? '' : '请输入密码'
  }
}

const validateForm = () => {
  validateField('username')
  validateField('password')
  return !errors.username && !errors.password
}

const handleLogin = async () => {
  if (!validateForm()) return

  loading.value = true
  try {
    const res = await login(form)
    userStore.setToken(res.access_token)
    await userStore.fetchUser()
    showToast('登录成功', 'success')
    setTimeout(() => router.push('/home'), 500)
  } catch (error) {
    showToast(error.response?.data?.detail || '登录失败', 'error')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 页面容器 - 左右分栏 */
.login-page {
  min-height: 100vh;
  display: flex;
}

/* 左侧区域 - 瀑布流背景 */
.left-section {
  flex: 7;
  background-color: #141414;
  background-image: url('/login-bg.jpg');
  background-size: cover;
  background-position: center;
  position: relative;
  display: flex;
  align-items: flex-start;
  padding: 60px;
}

.brand-info {
  color: #fff;
  z-index: 1;
  padding: 28px 32px;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.brand-logo {
  width: 64px;
  height: auto;
  margin-bottom: 20px;
}

.brand-title {
  font-size: 32px;
  font-weight: 600;
  margin: 0 0 12px 0;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
}

.brand-desc {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}

/* 右侧区域 - 登录表单 */
.right-section {
  flex: 3;
  min-width: 420px;
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.form-container {
  width: 100%;
  max-width: 360px;
}

.form-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.form-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0 0 32px 0;
}

/* 表单组 */
.form-group {
  margin-bottom: 20px;
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
