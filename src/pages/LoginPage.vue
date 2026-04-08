<template>
  <div class="login-view">
    <div class="login-shell">
      <section class="brand-pane">
        <div class="brand-tag">PRODUCTION CONTROL</div>
        <div class="brand-main">
          <img class="brand-logo" src="/assets/logo.ico" alt="logo">
          <h1>ABUS 装嵌生产进度管理系统</h1>
        </div>
        <p class="brand-desc">聚焦订单节拍、产线执行与状态追踪，让生产信息更清晰可控。</p>
      </section>

      <section class="form-pane">
        <div class="form-title">账号登录</div>
        <el-form :model="loginForm" class="login-form" @submit.native.prevent>
          <el-form-item label="用户名">
            <el-input v-model.trim="loginForm.username" placeholder="请输入用户名" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" @keyup.enter.native="handleLogin" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">登录</el-button>
          </el-form-item>
        </el-form>
      </section>
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

<style scoped>
.login-view {
  --steel-900: #111821;
  --steel-800: #182432;
  --steel-700: #243447;
  --steel-200: #d5dbe3;
  --line: rgba(255, 255, 255, 0.08);
  --accent: #19a7a8;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px;
  background:
    linear-gradient(120deg, rgba(255, 255, 255, 0.04) 0, rgba(255, 255, 255, 0) 32%),
    repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.03) 0, rgba(255, 255, 255, 0.03) 1px, transparent 1px, transparent 42px),
    linear-gradient(145deg, var(--steel-900), var(--steel-800) 55%, #1b2b3d);
  font-family: "IBM Plex Sans", "Noto Sans SC", "Microsoft YaHei", sans-serif;
}

.login-shell {
  width: min(980px, 100%);
  min-height: 520px;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.36);
  animation: rise-in 420ms ease-out;
}

.brand-pane {
  position: relative;
  padding: 44px 42px;
  color: #f2f6fb;
  background:
    linear-gradient(160deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0) 40%),
    radial-gradient(circle at 10% 10%, rgba(25, 167, 168, 0.16), transparent 34%),
    linear-gradient(180deg, #233244 0%, #1a2736 100%);
}

.brand-pane::after {
  content: "";
  position: absolute;
  inset: 16px;
  border: 1px solid var(--line);
  border-radius: 10px;
  pointer-events: none;
}

.brand-tag {
  display: inline-block;
  padding: 6px 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  font-size: 11px;
  letter-spacing: 1.2px;
  color: var(--steel-200);
}

.brand-main {
  margin-top: 28px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.brand-logo {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.16);
  padding: 4px;
  object-fit: contain;
}

.brand-main h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.35;
  letter-spacing: 0.8px;
  font-weight: 600;
}

.brand-desc {
  margin-top: 26px;
  max-width: 420px;
  color: rgba(242, 246, 251, 0.86);
  font-size: 14px;
  line-height: 1.9;
}

.form-pane {
  background: #f7f9fb;
  padding: 52px 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.form-title {
  color: #1f2b38;
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 20px;
  letter-spacing: 1px;
}

.login-form {
  width: 100%;
}

.login-btn {
  width: 100%;
  height: 44px;
  border-radius: 9px;
  border: none;
  font-size: 15px;
  letter-spacing: 1px;
  background: linear-gradient(90deg, #167f8a, var(--accent));
}

.form-pane /deep/ .el-form-item__label {
  font-weight: 600;
  color: #314454;
}

.form-pane /deep/ .el-input__inner {
  height: 42px;
  border-radius: 9px;
  border-color: #cfd8e3;
  background: #ffffff;
  transition: border-color 180ms ease;
}

.form-pane /deep/ .el-input__inner:focus {
  border-color: #167f8a;
}

@keyframes rise-in {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 900px) {
  .login-shell {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .brand-pane {
    padding: 30px 24px;
  }

  .brand-main h1 {
    font-size: 22px;
  }

  .form-pane {
    padding: 30px 24px 26px;
  }
}
</style>
