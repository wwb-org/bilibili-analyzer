<template>
  <div class="profile-container">
    <div class="page-header">
      <h2 class="page-title">个人中心</h2>
      <span class="page-desc">管理您的账户信息</span>
    </div>

    <div class="profile-main">
      <!-- 左栏：用户卡片 -->
      <div class="left-col">
        <div class="card user-card">
          <!-- 头像 -->
          <div class="avatar-area" @click="triggerAvatarUpload">
            <img
              v-if="avatarUrl"
              :src="avatarUrl"
              class="avatar-img"
              referrerpolicy="no-referrer"
            />
            <div v-else class="avatar-letter" :class="isAdmin ? 'avatar-admin' : 'avatar-user'">
              {{ avatarLetter }}
            </div>
            <div class="avatar-overlay">
              <span>{{ uploading ? '上传中...' : '更换头像' }}</span>
            </div>
            <input
              ref="avatarInput"
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              style="display: none"
              @change="handleAvatarChange"
            />
          </div>
          <!-- 用户名 + 角色 -->
          <div class="username-row">
            <template v-if="editingName">
              <input
                ref="nameInput"
                class="name-edit-input"
                v-model="newUsername"
                maxlength="20"
                placeholder="2-20个字符"
                @keyup.enter="handleSaveName"
                @keyup.escape="editingName = false"
              />
              <button class="name-btn name-btn-save" @click="handleSaveName" :disabled="savingName">
                {{ savingName ? '...' : '保存' }}
              </button>
              <button class="name-btn name-btn-cancel" @click="editingName = false">取消</button>
            </template>
            <template v-else>
              <div class="user-name">{{ user?.username || '-' }}</div>
              <button class="name-edit-icon" @click="startEditName" title="修改昵称">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            </template>
          </div>
          <span class="role-tag" :class="isAdmin ? 'role-admin' : 'role-user'">
            {{ isAdmin ? '管理员' : '普通用户' }}
          </span>

          <div class="divider"></div>

          <!-- 信息列表 -->
          <div class="info-list">
            <div class="info-row">
              <span class="info-label">邮箱</span>
              <span class="info-value">{{ user?.email || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">注册时间</span>
              <span class="info-value">{{ formatDate(user?.created_at) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">账号状态</span>
              <span class="info-value status-active">正常</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右栏 -->
      <div class="right-col">
        <!-- B站绑定卡片 -->
        <div class="card">
          <div class="card-title-row">
            <h3 class="card-title">B站账号绑定</h3>
            <span class="card-subtitle">绑定后可展示B站头像和昵称</span>
          </div>

          <!-- 已绑定状态 -->
          <div v-if="user?.bilibili_uid" class="bili-bound">
            <div class="bili-info">
              <img
                :src="user.bilibili_avatar"
                class="bili-avatar"
                referrerpolicy="no-referrer"
              />
              <div class="bili-detail">
                <div class="bili-name">{{ user.bilibili_name }}</div>
                <div class="bili-sign">{{ user.bilibili_sign || '这个人很懒，什么都没写~' }}</div>
                <div class="bili-uid">UID: {{ user.bilibili_uid }}</div>
              </div>
            </div>
            <button class="btn-outline btn-danger-outline" @click="handleUnbind" :disabled="unbinding">
              {{ unbinding ? '解绑中...' : '解除绑定' }}
            </button>
          </div>

          <!-- 未绑定状态 -->
          <div v-else class="bili-unbound">
            <div class="bind-form">
              <input
                type="number"
                class="form-input"
                v-model="biliUid"
                placeholder="请输入B站UID"
              />
              <button class="btn-primary" @click="handleBind" :disabled="binding">
                {{ binding ? '绑定中...' : '绑定' }}
              </button>
            </div>
            <div class="bind-tip">
              在B站个人空间页面的URL中可以找到UID，如 space.bilibili.com/<b>12345</b>
            </div>
          </div>
        </div>

        <!-- 修改密码卡片 -->
        <div class="card">
          <div class="card-title-row">
            <h3 class="card-title">修改密码</h3>
          </div>
          <form class="pwd-form" @submit.prevent="handleChangePwd">
            <div class="form-group">
              <label class="form-label">当前密码</label>
              <input type="password" class="form-input" v-model="pwdForm.old_password" placeholder="请输入当前密码" />
            </div>
            <div class="form-group">
              <label class="form-label">新密码</label>
              <input type="password" class="form-input" v-model="pwdForm.new_password" placeholder="请输入新密码（至少6位）" />
            </div>
            <div class="form-group">
              <label class="form-label">确认新密码</label>
              <input type="password" class="form-input" v-model="pwdForm.confirm_password" placeholder="请再次输入新密码" />
            </div>
            <span class="form-error" v-if="pwdError">{{ pwdError }}</span>
            <button type="submit" class="btn-primary" :disabled="changingPwd">
              {{ changingPwd ? '提交中...' : '修改密码' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, nextTick } from 'vue'
import { useUserStore } from '@/store/user'
import { changePassword, bindBilibili, unbindBilibili, uploadAvatar, changeUsername } from '@/api/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

const userStore = useUserStore()
const user = computed(() => userStore.user)
const isAdmin = computed(() => userStore.isAdmin)
const avatarLetter = computed(() => (user.value?.username?.[0] || 'U').toUpperCase())

// 头像 URL（优先级：自定义 > B站 > 无）
const avatarUrl = computed(() => {
  if (user.value?.avatar) return `/uploads/${user.value.avatar}`
  if (user.value?.bilibili_avatar) return user.value.bilibili_avatar
  return ''
})

// ====== 头像上传 ======
const avatarInput = ref(null)
const uploading = ref(false)

const triggerAvatarUpload = () => {
  if (!uploading.value) avatarInput.value?.click()
}

const handleAvatarChange = async (e) => {
  const file = e.target.files?.[0]
  if (!file) return

  if (file.size > 2 * 1024 * 1024) {
    ElMessage.warning('头像文件不能超过 2MB')
    return
  }
  if (!['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)) {
    ElMessage.warning('仅支持 JPG、PNG、GIF、WebP 格式')
    return
  }

  uploading.value = true
  try {
    await uploadAvatar(file)
    await userStore.fetchUser()
    ElMessage.success('头像更新成功')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '头像上传失败')
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

// ====== 修改昵称 ======
const editingName = ref(false)
const newUsername = ref('')
const savingName = ref(false)
const nameInput = ref(null)

const startEditName = () => {
  newUsername.value = user.value?.username || ''
  editingName.value = true
  nextTick(() => nameInput.value?.focus())
}

const handleSaveName = async () => {
  const name = newUsername.value.trim()
  if (!name || name.length < 2) {
    ElMessage.warning('昵称长度不能少于2个字符')
    return
  }
  if (name.length > 20) {
    ElMessage.warning('昵称长度不能超过20个字符')
    return
  }
  if (name === user.value?.username) {
    editingName.value = false
    return
  }

  savingName.value = true
  try {
    const res = await changeUsername({ new_username: name })
    // 更新token（因为JWT的sub是username）
    if (res.data?.access_token) {
      userStore.setToken(res.data.access_token)
    }
    await userStore.fetchUser()
    ElMessage.success('昵称修改成功')
    editingName.value = false
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '昵称修改失败')
  } finally {
    savingName.value = false
  }
}

// ====== B站绑定 ======
const biliUid = ref('')
const binding = ref(false)
const unbinding = ref(false)

const handleBind = async () => {
  const uid = parseInt(biliUid.value)
  if (!uid || uid <= 0) {
    ElMessage.warning('请输入有效的B站UID')
    return
  }
  binding.value = true
  try {
    await bindBilibili(uid)
    await userStore.fetchUser()
    ElMessage.success('绑定成功')
    biliUid.value = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '绑定失败')
  } finally {
    binding.value = false
  }
}

const handleUnbind = async () => {
  try {
    await ElMessageBox.confirm('确定要解除B站账号绑定吗？', '确认解绑', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  unbinding.value = true
  try {
    await unbindBilibili()
    await userStore.fetchUser()
    ElMessage.success('已解绑')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '解绑失败')
  } finally {
    unbinding.value = false
  }
}

// ====== 修改密码 ======
const pwdForm = reactive({ old_password: '', new_password: '', confirm_password: '' })
const pwdError = ref('')
const changingPwd = ref(false)

const handleChangePwd = async () => {
  pwdError.value = ''
  if (!pwdForm.old_password) { pwdError.value = '请输入当前密码'; return }
  if (pwdForm.new_password.length < 6) { pwdError.value = '新密码长度不能少于6位'; return }
  if (pwdForm.new_password !== pwdForm.confirm_password) { pwdError.value = '两次输入的密码不一致'; return }

  changingPwd.value = true
  try {
    await changePassword({ old_password: pwdForm.old_password, new_password: pwdForm.new_password })
    ElMessage.success('密码修改成功')
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    changingPwd.value = false
  }
}

// ====== 工具函数 ======
const formatDate = (dt) => {
  if (!dt) return '-'
  const d = new Date(dt)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

onMounted(() => {
  userStore.fetchUser()
})
</script>

<style scoped>
.profile-container {
  max-width: 960px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 2px;
}
.page-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 两列布局 */
.profile-main {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}
.left-col {
  width: 300px;
  flex-shrink: 0;
}
.right-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 卡片 */
.card {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  padding: 24px;
}

.card-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 16px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}
.card-subtitle {
  font-size: 12px;
  color: var(--text-placeholder);
}

/* 用户卡片 */
.user-card {
  text-align: center;
}
.avatar-area {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
  position: relative;
  cursor: pointer;
}
.avatar-img {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid var(--bg-gray);
}
.avatar-letter {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 700;
  color: #fff;
}
.avatar-overlay {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}
.avatar-overlay span {
  color: #fff;
  font-size: 12px;
}
.avatar-area:hover .avatar-overlay {
  opacity: 1;
}
.avatar-user {
  background-color: var(--bili-blue);
}
.avatar-admin {
  background-color: var(--bili-pink);
}

.user-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.username-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 8px;
  min-height: 28px;
}
.name-edit-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--text-placeholder);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.1s;
}
.name-edit-icon:hover {
  color: var(--bili-blue);
  background: var(--bili-blue-light);
}
.name-edit-input {
  width: 120px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--bili-blue);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-primary);
  outline: none;
  text-align: center;
}
.name-btn {
  height: 26px;
  padding: 0 10px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: opacity 0.1s;
}
.name-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.name-btn-save {
  background: var(--bili-blue);
  color: #fff;
}
.name-btn-save:hover:not(:disabled) {
  opacity: 0.85;
}
.name-btn-cancel {
  background: var(--bg-gray);
  color: var(--text-secondary);
}
.name-btn-cancel:hover {
  background: var(--border-light);
}
.role-tag {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.role-admin {
  background: rgba(251, 114, 153, 0.1);
  color: var(--bili-pink);
}
.role-user {
  background: var(--bili-blue-light);
  color: var(--bili-blue);
}

.divider {
  height: 1px;
  background: var(--border-light);
  margin: 16px 0;
}

/* 信息列表 */
.info-list {
  text-align: left;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}
.info-row + .info-row {
  border-top: 1px solid var(--bg-gray);
}
.info-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.info-value {
  font-size: 13px;
  color: var(--text-primary);
  font-weight: 500;
}
.status-active {
  color: var(--color-success);
}

/* B站绑定 - 已绑定 */
.bili-bound {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.bili-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}
.bili-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  border: 2px solid var(--bg-gray);
}
.bili-detail {
  flex: 1;
  min-width: 0;
}
.bili-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}
.bili-sign {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bili-uid {
  font-size: 11px;
  color: var(--text-placeholder);
  margin-top: 2px;
}

/* B站绑定 - 未绑定 */
.bili-unbound {}
.bind-form {
  display: flex;
  gap: 10px;
}
.bind-form .form-input {
  flex: 1;
}
.bind-form .btn-primary {
  width: auto;
  flex-shrink: 0;
  padding: 0 24px;
}
.bind-tip {
  font-size: 12px;
  color: var(--text-placeholder);
  margin-top: 10px;
  line-height: 1.5;
}

/* 表单 */
.form-group {
  margin-bottom: 16px;
}
.form-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}
.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
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
/* 隐藏 number input 的上下箭头 */
.form-input[type="number"]::-webkit-outer-spin-button,
.form-input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.form-input[type="number"] {
  -moz-appearance: textfield;
}

.form-error {
  display: block;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--color-error);
}

/* 按钮 */
.btn-primary {
  width: 100%;
  height: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  border: none;
  border-radius: 8px;
  font-size: 14px;
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

.btn-outline {
  height: 34px;
  padding: 0 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  cursor: pointer;
  transition: all 0.1s;
  flex-shrink: 0;
}
.btn-danger-outline {
  border: 1px solid var(--color-error);
  color: var(--color-error);
}
.btn-danger-outline:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.06);
}
.btn-danger-outline:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pwd-form .btn-primary {
  margin-top: 4px;
}
</style>
