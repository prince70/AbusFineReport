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
    { path: '/list', redirect: '/list/grinding' },
    { path: '/list/grinding', component: ChecklistPage, meta: { permission: 'checklist:query', workshop: 'grinding', workshopLabel: '打磨车间', sourceTable: '昨日打磨数据_外协' } },
    { path: '/list/key', component: ChecklistPage, meta: { permission: 'checklist:query', workshop: 'key', workshopLabel: '钥匙车间', sourceTable: '昨日钥匙数据_外协' } },
    { path: '/list/body', component: ChecklistPage, meta: { permission: 'checklist:query', workshop: 'body', workshopLabel: '锁体车间', sourceTable: '昨日锁体数据_外协' } },
    { path: '/list/beam', component: ChecklistPage, meta: { permission: 'checklist:query', workshop: 'beam', workshopLabel: '锁梁车间', sourceTable: '昨日锁梁数据_外协' } },
    { path: '/list/core', component: ChecklistPage, meta: { permission: 'checklist:query', workshop: 'core', workshopLabel: '锁芯车间', sourceTable: '昨日锁芯数据_外协' } },
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
