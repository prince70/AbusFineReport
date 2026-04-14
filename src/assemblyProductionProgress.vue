<template>
  <Layout :breadcrumbItems="breadcrumbItems">
    <div class="assembly-progress-container">
      <!-- 登录表单 -->
      <el-card v-if="!isLoggedIn" class="login-card">
        <h2 class="login-title">装嵌生产进度查询系统</h2>
        <el-form :model="loginForm" @submit.native.prevent>
          <el-form-item label="用户名">
            <el-input v-model="loginForm.username" placeholder="请输入用户名" style="width: 300px" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" style="width: 300px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleLogin" :loading="loginLoading">登录</el-button>
          </el-form-item>
        </el-form>
        <div class="login-hint">测试账号: admin / admin123</div>
      </el-card>

      <!-- 查询表单 -->
      <el-card v-else class="search-card">
        <el-form :model="searchForm" inline>
          <el-form-item label="生产车间">
            <el-select v-model="searchForm.生产车间" placeholder="请选择生产车间" clearable filterable style="width: 200px">
              <el-option v-for="item in workshops" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>

          <el-form-item label="订单号">
            <el-input v-model="searchForm.订单号" placeholder="请输入订单号" clearable style="width: 200px" />
          </el-form-item>

          <el-form-item label="料品编码">
            <el-input v-model="searchForm.料品编码" placeholder="请输入料品编码" clearable style="width: 200px" />
          </el-form-item>

          <el-form-item label="料品名称">
            <el-input v-model="searchForm.料品名称" placeholder="请输入料品名称" clearable style="width: 200px" />
          </el-form-item>

          <el-form-item label="开始日期">
            <el-date-picker
              v-model="searchForm.开始日期"
              type="date"
              placeholder="选择开始日期"
              value-format="yyyy-MM-dd"
              :picker-options="{
                disabledDate: time => searchForm.结束日期 && time > new Date(searchForm.结束日期)
              }"
              style="width: 200px"
            />
          </el-form-item>

          <el-form-item label="结束日期">
            <el-date-picker
              v-model="searchForm.结束日期"
              type="date"
              placeholder="选择结束日期"
              value-format="yyyy-MM-dd"
              :picker-options="{
                disabledDate: time => searchForm.开始日期 && time < new Date(searchForm.开始日期)
              }"
              style="width: 200px"
            />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" @click="handleSearch" :loading="loading">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
            <el-button type="success" @click="handleExport">导出Excel</el-button>
            <el-button @click="handleLogout" plain>退出</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 数据表格 -->
      <el-card v-if="isLoggedIn" class="table-card">
        <div class="table-header">
          <div class="header-left">
            <span class="title">装嵌生产进度查询结果</span>
          </div>
          <div class="header-right">
            <span class="stat-item">总数据条数：<strong>{{ totalCount }}</strong></span>
            <span class="stat-item">符合条件：<strong>{{ tableData.length }}</strong> 条</span>
            <span class="stat-item">当前页：<strong>{{ currentPage }}</strong> / {{ totalPages }}</span>
          </div>
        </div>

        <el-table :data="paginatedData" v-loading="loading" border stripe style="width: 100%" max-height="600"
          :header-cell-style="{ background: '#409EFF', color: '#fff', fontWeight: 'bold' }"
          show-summary
          :summary-method="getSummaries">
          <el-table-column type="index" label="序号" width="60" align="center" :index="indexMethod" />
          <el-table-column prop="订单号" label="订单号" width="140" align="center" />
          <el-table-column prop="料品编码" label="料品编码" width="120" align="center" />
          <el-table-column prop="料品名称" label="料品名称" width="150" />
          <el-table-column prop="料品规格" label="料品规格" width="150" />
          <el-table-column prop="生产车间" label="生产车间" width="120" align="center" />
          <el-table-column prop="计划数量" label="计划数量" width="100" align="center" />
          <el-table-column prop="已完成数量" label="已完成数量" width="110" align="center" />
          <el-table-column prop="进行中数量" label="进行中数量" width="110" align="center" />
          <el-table-column prop="未开始数量" label="未开始数量" width="110" align="center" />
          <el-table-column prop="完成率" label="完成率" width="100" align="center">
            <template slot-scope="scope">
              <span :style="{ color: getCompletionRateColor(scope.row.完成率) }">
                {{ scope.row.完成率 }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="计划开始日期" label="计划开始日期" width="120" align="center" />
          <el-table-column prop="计划结束日期" label="计划结束日期" width="120" align="center" />
          <el-table-column prop="实际开始日期" label="实际开始日期" width="120" align="center" />
          <el-table-column prop="实际结束日期" label="实际结束日期" width="120" align="center" />
          <el-table-column prop="进度状态" label="进度状态" width="100" align="center">
            <template slot-scope="scope">
              <el-tag :type="getStatusType(scope.row.进度状态)" size="small">
                {{ scope.row.进度状态 }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="备注" label="备注" min-width="200">
            <template slot-scope="scope">
              <div style="white-space: normal; word-break: break-all; line-height: 1.5;">
                {{ scope.row.备注 }}
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页组件 -->
        <div class="pagination-container">
          <el-pagination @size-change="handleSizeChange" @current-change="handleCurrentChange"
            :current-page="currentPage" :page-size="pageSize" :page-sizes="pageSizeOptions"
            layout="total, sizes, prev, pager, next, jumper" :total="tableData.length" background />
        </div>
      </el-card>
    </div>
  </Layout>
</template>

<script>
import axios from 'axios'

export default {
  name: 'assemblyProductionProgress',
  data() {
    return {
      isLoggedIn: false,
      loginForm: {
        username: '',
        password: ''
      },
      loginLoading: false,
      breadcrumbItems: ['All Process 全流程', '装嵌生产进度查询'],
      searchForm: {
        生产车间: '',
        订单号: '',
        料品编码: '',
        料品名称: '',
        开始日期: null,
        结束日期: null
      },
      workshops: [],
      tableData: [],
      totalCount: 0,
      loading: false,
      currentPage: 1,
      pageSize: 50,
      pageSizeOptions: [50, 100, 200]
    }
  },
  computed: {
    paginatedData() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.tableData.slice(start, end)
    },
    totalPages() {
      return Math.ceil(this.tableData.length / this.pageSize)
    }
  },
  mounted() {
    this.checkLogin()
  },
  methods: {
    async checkLogin() {
      try {
        const res = await axios.get('/api/check-login')
        if (res.data.loggedIn) {
          this.isLoggedIn = true
          this.fetchWorkshops()
          this.handleSearch()
        }
      } catch (error) {
        console.error('检查登录状态失败:', error)
      }
    },

    async handleLogin() {
      this.loginLoading = true
      try {
        const res = await axios.post('/api/login', {
          username: this.loginForm.username,
          password: this.loginForm.password
        })
        if (res.data.status === 'success') {
          this.isLoggedIn = true
          this.$message.success('登录成功')
          this.fetchWorkshops()
          this.handleSearch()
        } else {
          this.$message.error(res.data.message || '登录失败')
        }
      } catch (error) {
        this.$message.error('登录失败，请检查网络')
      } finally {
        this.loginLoading = false
      }
    },

    async handleLogout() {
      try {
        await axios.post('/api/logout')
        this.isLoggedIn = false
        this.$message.success('已退出登录')
      } catch (error) {
        console.error('退出登录失败:', error)
      }
    },

    async fetchWorkshops() {
      try {
        const res = await axios.get('/api/assembly-production/workshops')
        if (res.data.status === 'success') {
          this.workshops = res.data.data || []
        }
      } catch (error) {
        console.error('获取生产车间列表失败:', error)
      }
    },

    async handleSearch() {
      this.loading = true
      try {
        const params = {}

        if (this.searchForm.生产车间) {
          params.生产车间 = this.searchForm.生产车间
        }
        if (this.searchForm.订单号) {
          params.订单号 = this.searchForm.订单号
        }
        if (this.searchForm.料品编码) {
          params.料品编码 = this.searchForm.料品编码
        }
        if (this.searchForm.料品名称) {
          params.料品名称 = this.searchForm.料品名称
        }
        if (this.searchForm.开始日期) {
          params.开始日期 = this.searchForm.开始日期
        }
        if (this.searchForm.结束日期) {
          params.结束日期 = this.searchForm.结束日期
        }

        const res = await axios.get('/api/assembly-production/query', { params })

        if (res.data.status === 'success') {
          this.tableData = res.data.data || []
          this.totalCount = res.data.total || this.tableData.length
          this.currentPage = 1
        } else {
          this.$message.error('查询失败')
        }
      } catch (error) {
        console.error('查询失败:', error)
        this.$message.error('查询失败，请检查网络')
      } finally {
        this.loading = false
      }
    },

    handleReset() {
      this.searchForm = {
        生产车间: '',
        订单号: '',
        料品编码: '',
        料品名称: '',
        开始日期: null,
        结束日期: null
      }
      this.handleSearch()
    },

    handleExport() {
      if (this.tableData.length === 0) {
        this.$message.warning('暂无数据可导出')
        return
      }

      import('xlsx').then(XLSX => {
        const worksheet = XLSX.utils.json_to_sheet(this.tableData)
        const workbook = XLSX.utils.book_new()

        const fileName = `装嵌生产进度查询_${new Date().toLocaleDateString()}.xlsx`

        XLSX.utils.book_append_sheet(workbook, worksheet, '装嵌生产进度')
        XLSX.writeFile(workbook, fileName)
        this.$message.success('导出成功')
      }).catch(() => {
        this.$message.error('导出失败，请安装 xlsx 库')
      })
    },

    handleCurrentChange(val) {
      this.currentPage = val
    },

    handleSizeChange(val) {
      this.pageSize = val
      this.currentPage = 1
    },

    indexMethod(index) {
      return (this.currentPage - 1) * this.pageSize + index + 1
    },

    getSummaries({ columns, data }) {
      const sums = []
      columns.forEach((column, index) => {
        if (index === 0) {
          sums[index] = '当前页合计'
          return
        }
        if (column.property === '计划数量' || column.property === '已完成数量' || 
            column.property === '进行中数量' || column.property === '未开始数量') {
          const total = data.reduce((acc, row) => {
            const value = Number(row[column.property])
            return acc + (Number.isNaN(value) ? 0 : value)
          }, 0)
          sums[index] = total.toLocaleString()
        } else {
          sums[index] = ''
        }
      })
      return sums
    },

    getCompletionRateColor(rate) {
      if (!rate) return '#606266'
      const value = parseFloat(rate)
      if (value >= 100) return '#67C23A'
      if (value >= 70) return '#409EFF'
      if (value >= 50) return '#E6A23C'
      return '#F56C6C'
    },

    getStatusType(status) {
      if (!status) return 'info'
      const statusMap = {
        '已完成': 'success',
        '进行中': 'primary',
        '未开始': 'info',
        '已逾期': 'danger',
        '即将逾期': 'warning'
      }
      return statusMap[status] || 'info'
    }
  }
}
</script>

<style scoped>
.assembly-progress-container {
  padding: 20px;
}

.login-card {
  max-width: 450px;
  margin: 100px auto;
  text-align: center;
}

.login-title {
  margin-bottom: 30px;
  color: #409EFF;
}

.login-hint {
  margin-top: 20px;
  color: #999;
  font-size: 12px;
}

.search-card {
  margin-bottom: 20px;
}

.table-card {
  margin-top: 20px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.header-left .title {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.header-right {
  display: flex;
  gap: 20px;
}

.stat-item {
  font-size: 14px;
  color: #606266;
}

.stat-item strong {
  color: #409EFF;
  font-size: 16px;
  margin: 0 4px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
