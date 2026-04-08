<template>
  <app-layout title="生产进度查询系统" :breadcrumb="['首页', '生产概览']">
    <div class="dashboard-grid">
      <div class="stat-box"><div class="stat-label">总订单数</div><div class="stat-value">{{ stats.totalOrders }}</div></div>
      <div class="stat-box"><div class="stat-label">计划总数量</div><div class="stat-value">{{ formatNum(stats.totalQuantity) }}</div></div>
      <div class="stat-box"><div class="stat-label">已完成数量</div><div class="stat-value">{{ formatNum(stats.totalCompleted) }}</div></div>
      <div class="stat-box"><div class="stat-label">总体完成率</div><div class="stat-value">{{ completionRate }}%</div></div>
    </div>
    <el-row :gutter="14">
      <el-col :xs="24" :md="12">
        <el-card>
          <div slot="header">状态分布</div>
          <el-table :data="stats.statusStats" border size="small">
            <el-table-column prop="status" label="状态" align="center" />
            <el-table-column prop="count" label="数量" align="center" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card>
          <div slot="header">系统信息</div>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户数">{{ stats.totalUsers }}</el-descriptions-item>
            <el-descriptions-item label="角色数">{{ stats.totalRoles }}</el-descriptions-item>
            <el-descriptions-item label="当前用户">{{ user.nickname || user.username }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </app-layout>
</template>

<script>
import axios from 'axios'
import authStore from '@/services/auth'
import AppLayout from '@/components/AppLayout.vue'

export default {
  name: 'DashboardPage',
  components: { AppLayout },
  data() {
    return {
      user: authStore.getUser(),
      stats: { totalOrders: 0, totalQuantity: 0, totalCompleted: 0, statusStats: [], totalUsers: 0, totalRoles: 0 }
    }
  },
  computed: {
    completionRate() {
      if (!this.stats.totalQuantity) return 0
      return (this.stats.totalCompleted / this.stats.totalQuantity * 100).toFixed(1)
    }
  },
  mounted() {
    this.fetchStats()
  },
  methods: {
    formatNum(v) {
      return Number(v || 0).toLocaleString()
    },
    async fetchStats() {
      try {
        const res = await axios.get('/api/dashboard/stats')
        if (res.data.status === 'success') this.stats = res.data.data || this.stats
      } catch (error) {
        this.$message.error('获取统计数据失败')
      }
    }
  }
}
</script>
