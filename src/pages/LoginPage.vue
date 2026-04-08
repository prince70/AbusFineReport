<template>
  <div class="app-login">
    <div class="login-card">
      <div class="login-head">
        <div class="login-brand">
          <img class="brand-logo-lg" src="/assets/logo.ico" alt="logo">
          <h1>ABUS嵌生产进度管理系统</h1>
        </div>
      </div>
      <div class="login-body">
        <el-form :model="loginForm" @submit.native.prevent>
          <el-form-item label="用户名">
            <el-input v-model.trim="loginForm.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" @keyup.enter.native="handleLogin" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" style="width: 100%;" :loading="loading" @click="handleLogin">登录</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import authStore from '@/services/auth'

export default {
  name: 'LoginPage',
  data() {
    return {
      loginForm: { username: '', password: '' },
      loading: false
    }
  },
  methods: {
    async handleLogin() {
      if (!this.loginForm.username || !this.loginForm.password) {
        this.$message.warning('请输入用户名和密码')
        return
      }
      this.loading = true
      try {
        const res = await axios.post('/api/login', this.loginForm)
        if (res.data.status !== 'success') {
          this.$message.error(res.data.message || '登录失败')
          return
        }
        authStore.saveAuth(res.data)
        this.$message.success('登录成功')
        this.$router.push('/dashboard')
      } catch (error) {
        this.$message.error('登录失败，请检查网络')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
