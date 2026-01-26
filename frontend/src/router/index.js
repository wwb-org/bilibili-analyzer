import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/store/user'

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
      valid ? next() : next('/login')
    } else {
      next()
    }
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
