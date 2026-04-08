import Vue from 'vue'
import Router from 'vue-router'
import authStore, { installAuthInterceptor, tryRestoreSession } from '@/services/auth'

import LoginPage from '@/pages/LoginPage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'
import AssemblyProgressPage from '@/pages/AssemblyProgressPage.vue'
import ChecklistPage from '@/pages/ChecklistPage.vue'
import UserManagementPage from '@/pages/UserManagementPage.vue'
import RoleManagementPage from '@/pages/RoleManagementPage.vue'
import ForbiddenPage from '@/pages/ForbiddenPage.vue'

Vue.use(Router)

const router = new Router({
  mode: 'history',
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: LoginPage },
    { path: '/dashboard', component: DashboardPage },
    { path: '/assembly', component: AssemblyProgressPage, meta: { permission: 'assembly:query' } },
    { path: '/list', component: ChecklistPage, meta: { permission: 'checklist:query' } },
    { path: '/users', component: UserManagementPage, meta: { permission: 'user:view' } },
    { path: '/roles', component: RoleManagementPage, meta: { permission: 'role:view' } },
    { path: '/forbidden', component: ForbiddenPage }
  ]
})

installAuthInterceptor(router)

router.beforeEach(async (to, from, next) => {
  if (to.path === '/login') {
    const hasUser = !!authStore.getUser().id
    next(hasUser ? '/dashboard' : undefined)
    return
  }

  if (!authStore.getUser().id) {
    const ok = await tryRestoreSession()
    if (!ok) {
      next('/login')
      return
    }
  }

  const permission = to.meta && to.meta.permission
  if (permission && !authStore.getPermissions().includes(permission)) {
    next('/forbidden')
    return
  }

  next()
})

export default router
