import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue')
  },
  {
    path: '/',
    component: () => import('@/components/common/Layout.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'videos',
        name: 'VideoList',
        component: () => import('@/views/VideoList.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'live',
        name: 'Live',
        component: () => import('@/views/Live.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'prediction',
        name: 'Prediction',
        component: () => import('@/views/Prediction.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'comments',
        name: 'Comments',
        component: () => import('@/views/Comments.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('@/views/Admin.vue'),
        meta: { requiresAuth: true, requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth) {
    if (!userStore.token) {
      next('/login')
    } else if (!userStore.user) {
      // 验证token有效性
      const valid = await userStore.checkAuth()
      if (!valid) {
        next('/login')
        return
      }
    }

    // 管理员权限检查
    if (to.meta.requiresAdmin && !userStore.isAdmin) {
      ElMessage.error('需要管理员权限')
      next('/home')
      return
    }

    next()
  } else {
    // 已登录用户访问登录/注册页时跳转到首页
    if ((to.path === '/login' || to.path === '/register') && userStore.token) {
      next('/home')
    } else {
      next()
    }
  }
})

export default router
