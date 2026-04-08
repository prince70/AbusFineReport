<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="logo">
        <img class="brand-logo" src="/assets/logo.ico" alt="logo">
        <span>生产管理平台</span>
      </div>
      <el-menu :default-active="activeMenu" background-color="transparent" text-color="#fff" active-text-color="#fff" @select="handleSelect">
        <template v-for="menu in menus">
          <el-submenu v-if="menu.children && menu.children.length" :index="menu.path" :key="menu.id">
            <template slot="title"><i :class="menu.icon"></i><span>{{ menu.name }}</span></template>
            <el-menu-item v-for="child in menu.children" :key="child.id" :index="normalizePath(child.path)">{{ child.name }}</el-menu-item>
          </el-submenu>
          <el-menu-item v-else :index="normalizePath(menu.path)" :key="menu.id"><i :class="menu.icon"></i><span slot="title">{{ menu.name }}</span></el-menu-item>
        </template>
      </el-menu>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="topbar-title"><img src="/assets/logo.ico" alt="logo"><span>{{ title }}</span></div>
        <div>
          <span style="margin-right: 10px; color: #606266;">欢迎，{{ user.nickname || user.username }}</span>
          <el-button size="mini" @click="handleLogout">退出</el-button>
        </div>
      </header>
      <section class="content">
        <div class="breadcrumbs">
          <el-breadcrumb separator=">">
            <el-breadcrumb-item v-for="item in breadcrumb" :key="item">{{ item }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <slot></slot>
      </section>
    </main>
  </div>
</template>

<script>
import axios from 'axios'
import authStore from '@/services/auth'

export default {
  name: 'AppLayout',
  props: {
    title: { type: String, default: '' },
    breadcrumb: { type: Array, default: () => [] }
  },
  data() {
    return {
      user: authStore.getUser(),
      menus: authStore.getMenus(),
      activeMenu: this.$route.path
    }
  },
  mounted() {
    axios.get('/api/me').then(res => {
      if (res.data && res.data.status === 'success' && res.data.data) {
        const payload = {
          user: {
            id: res.data.data.id,
            username: res.data.data.username,
            nickname: res.data.data.nickname
          },
          permissions: res.data.data.permissions || [],
          menus: res.data.data.menus || []
        }
        authStore.saveAuth(payload)
        this.user = authStore.getUser()
        this.menus = authStore.getMenus()
      }
    }).catch(() => {})
  },
  watch: {
    '$route.path'(val) {
      this.activeMenu = val
    }
  },
  methods: {
    normalizePath(path) {
      if (path === '/system/users') return '/users'
      if (path === '/system/roles') return '/roles'
      return path || '/dashboard'
    },
    handleSelect(path) {
      if (path !== this.$route.path) {
        this.$router.push(path)
      }
    },
    async handleLogout() {
      try {
        await axios.post('/api/logout')
      } catch (e) {
        // Ignore logout API errors and clear local session anyway.
      }
      authStore.clear()
      this.$router.push('/login')
    }
  }
}
</script>
