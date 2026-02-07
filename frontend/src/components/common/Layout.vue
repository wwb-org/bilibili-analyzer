<template>
  <div class="app-layout">
    <el-container class="layout-container">
      <!-- 左侧侧边栏 -->
      <el-aside width="240px" class="sidebar">
        <div class="logo-container">
          <img src="@/bilibili.svg" alt="Logo" class="logo-icon" />
          <span class="logo-text">趋势分析系统</span>
        </div>
        
        <el-menu
          :default-active="activeMenu"
          class="sidebar-menu"
          router
          :collapse="false"
        >
          <el-menu-item index="/home">
            <el-icon><DataLine /></el-icon>
            <span>首页仪表盘</span>
          </el-menu-item>
          
          <el-menu-item index="/videos">
            <el-icon><VideoPlay /></el-icon>
            <span>视频数据</span>
          </el-menu-item>
          
          <el-menu-item index="/comments">
            <el-icon><ChatDotRound /></el-icon>
            <span>评论分析</span>
          </el-menu-item>
          
          <el-menu-item index="/keywords">
            <el-icon><PriceTag /></el-icon>
            <span>热词分析</span>
          </el-menu-item>
          
          <el-menu-item index="/live">
            <el-icon><Microphone /></el-icon>
            <span>直播分析</span>
          </el-menu-item>
          
          <el-menu-item index="/prediction">
            <el-icon><TrendCharts /></el-icon>
            <span>智能预测</span>
          </el-menu-item>
          
          <el-menu-item index="/admin" v-if="userStore.user?.role === 'admin'">
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 右侧内容区 -->
      <el-container>
        <el-header class="header">
          <div class="header-left">
            <!-- 面包屑或其他 -->
          </div>
          <div class="header-right">
            <el-dropdown @command="handleCommand">
              <div class="user-info">
                <el-avatar :size="32" class="user-avatar">{{ userAvatar }}</el-avatar>
                <span class="user-name">{{ userStore.user?.username || '用户' }}</span>
                <el-icon><CaretBottom /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                  <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { 
  DataLine, VideoPlay, ChatDotRound, PriceTag, 
  Microphone, TrendCharts, Setting, CaretBottom 
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => route.path)
const userAvatar = computed(() => (userStore.user?.username?.[0] || 'U').toUpperCase())

const handleCommand = (command) => {
  if (command === 'logout') {
    userStore.logout()
    router.push('/login')
  } else if (command === 'profile') {
    router.push('/profile')
  }
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-gray);
}

.layout-container {
  height: 100%;
}

/* 侧边栏样式 */
.sidebar {
  background-color: var(--bg-white);
  border-right: 1px solid var(--border-light);
  display: flex;
  flex-direction: column;
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-light);
}

.logo-icon {
  width: 32px;
  height: 32px;
  margin-right: 12px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.sidebar-menu {
  border-right: none;
  flex: 1;
  padding: 12px 0;
}

:deep(.el-menu-item) {
  height: 50px;
  margin: 4px 12px;
  border-radius: 8px;
  color: var(--text-regular);
}

:deep(.el-menu-item.is-active) {
  background-color: var(--bili-blue-light);
  color: var(--bili-blue);
  font-weight: 500;
}

:deep(.el-menu-item:hover) {
  background-color: var(--bg-gray-light);
  color: var(--text-primary);
}

:deep(.el-menu-item.is-active:hover) {
  background-color: var(--bili-blue-light);
  color: var(--bili-blue);
}

/* 头部样式 */
.header {
  height: 60px;
  background-color: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.user-info:hover {
  background-color: var(--bg-gray-light);
}

.user-avatar {
  background-color: var(--bili-blue);
  color: #fff;
  font-size: 14px;
  margin-right: 8px;
}

.user-name {
  font-size: 14px;
  color: var(--text-primary);
  margin-right: 4px;
}

/* 内容区样式 */
.main-content {
  padding: 24px;
  background-color: var(--bg-gray);
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
