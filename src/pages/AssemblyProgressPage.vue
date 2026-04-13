<template>
  <app-layout title="装嵌生产进度" :breadcrumb="['All Process 全流程', '装嵌生产进度查询']">
    <div v-if="loading" class="global-loading-mask">
      <i class="el-icon-loading"></i>
      <span>查询中...</span>
    </div>
    <el-card>
      <el-form :model="searchForm" inline>
        <el-form-item label="区域">
          <el-select v-model="searchForm.区域" placeholder="请选择区域" clearable filterable style="width: 190px">
            <el-option v-for="item in workshops" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="订单批号"><el-input v-model="searchForm.订单批号" clearable style="width: 190px" /></el-form-item>
        <el-form-item label="客户"><el-input v-model="searchForm.客户" clearable style="width: 190px" /></el-form-item>
        <el-form-item label="料品编码"><el-input v-model="searchForm.料品编码" clearable style="width: 190px" /></el-form-item>
        <el-form-item label="料品名称"><el-input v-model="searchForm.料品名称" clearable style="width: 190px" /></el-form-item>
        <el-form-item label="开始日期"><el-date-picker v-model="searchForm.开始日期" type="date" value-format="yyyy-MM-dd" style="width: 190px" /></el-form-item>
        <el-form-item label="结束日期"><el-date-picker v-model="searchForm.结束日期" type="date" value-format="yyyy-MM-dd" style="width: 190px" /></el-form-item>
        <el-form-item label="完成状态">
          <el-select v-model="searchForm.进度状态" placeholder="请选择状态" clearable multiple collapse-tags style="width: 190px">
            <el-option label="已完成" value="已完成" />
            <el-option label="进行中" value="进行中" />
            <el-option label="未开始" value="未开始" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="loading">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="success" @click="handleExport" v-if="hasPermission('assembly:export')">导出Excel</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    <el-card>
      <div class="table-head">
        <div class="title">装嵌生产进度查询结果</div>
        <div class="meta">总数据条数：<strong>{{ totalCount }}</strong>，当前页：<strong>{{ currentPage }}</strong>/{{ totalPages }}</div>
      </div>
      <el-table ref="assemblyTable" :data="paginatedData" v-loading="loading" border stripe max-height="600" show-summary :summary-method="getSummaries" highlight-current-row @row-click="handleRowClick">
        <el-table-column type="index" label="序号" width="60" align="center" :index="indexMethod" />
        <el-table-column prop="客户" label="客户" width="140" align="center" />
        <el-table-column prop="订单批号" label="订单批号" width="170" align="center" />
        <el-table-column prop="分区" label="分区" width="100" align="center" />
        <el-table-column prop="确定交期" label="确定交期" width="120" align="center"><template slot-scope="scope">{{ formatDate(scope.row.确定交期) }}</template></el-table-column>
        <el-table-column prop="料品编码" label="料品编码" width="130" align="center" />
        <el-table-column prop="料品名称" label="料品名称" width="150" />
        <el-table-column prop="规格型号" label="规格型号" min-width="220" />
        <el-table-column prop="订单数量" label="订单数量" width="100" align="center" />
        <el-table-column prop="完成数量" label="完成数量" width="100" align="center" />
        <el-table-column prop="未完成数量" label="未完成数量" width="110" align="center" />
        <el-table-column prop="最早完成日期" label="最早完成日期" width="120" align="center"><template slot-scope="scope">{{ formatDate(scope.row.最早完成日期) }}</template></el-table-column>
        <el-table-column prop="最晚完成日期" label="最晚完成日期" width="120" align="center"><template slot-scope="scope">{{ formatDate(scope.row.最晚完成日期) }}</template></el-table-column>
        <el-table-column prop="进度状态" label="进度状态" width="100" align="center"><template slot-scope="scope"><el-tag :type="getStatusType(scope.row.进度状态)" size="small">{{ scope.row.进度状态 }}</el-tag></template></el-table-column>
        <el-table-column prop="备注" label="备注" min-width="180" />
        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template slot-scope="scope">
            <el-button size="mini" type="warning" @click="handleViewAllFinishedQty(scope.row)">查看全部报工数据</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="overall-summary-row">
        <span class="label">全部数据合计：</span>
        <span>订单数量 <strong>{{ overallSummary.订单数量.toLocaleString() }}</strong></span>
        <span>完成数量 <strong>{{ overallSummary.完成数量.toLocaleString() }}</strong></span>
        <span>未完成数量 <strong>{{ overallSummary.未完成数量.toLocaleString() }}</strong></span>
      </div>
      <div class="pagination-wrap">
        <el-pagination @size-change="handleSizeChange" @current-change="handleCurrentChange" :current-page="currentPage" :page-size="pageSize" :page-sizes="[50,100,200,2000,5000]" layout="total, sizes, prev, pager, next, jumper" :total="tableData.length" background />
      </div>
    </el-card>

    <el-dialog
      title="全部报工数据"
      :visible.sync="finishedQtyDialogVisible"
      width="98%"
      top="1vh"
      append-to-body
      destroy-on-close
      custom-class="finished-qty-dialog"
    >
      <div v-loading="finishedQtyLoading" style="min-height: 120px;">
        <div style="margin-bottom: 12px; color: #606266;">
          订单批号：<strong>{{ finishedQtyOrderNumber || '-' }}</strong>，
          记录数：<strong>{{ finishedQtyData.length }}</strong>
        </div>
        <div class="finished-qty-table-wrap">
          <el-table
            :data="finishedQtyData"
            border
            stripe
            empty-text="暂无数据"
            style="width: 100%"
          >
            <el-table-column
              v-for="column in finishedQtyColumns"
              :key="column"
              :prop="column"
              :label="column"
              min-width="140"
              show-overflow-tooltip
            >
              <template slot-scope="scope">
                {{ formatRawValue(scope.row[column]) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
  </app-layout>
</template>

<script>
import axios from 'axios'
import AppLayout from '@/components/AppLayout.vue'
import authStore from '@/services/auth'

export default {
  name: 'AssemblyProgressPage',
  components: { AppLayout },
  data() {
    return {
      searchForm: { 区域: '', 订单批号: '', 客户: '', 料品编码: '', 料品名称: '', 开始日期: '', 结束日期: '', 进度状态: [] },
      workshops: [],
      tableData: [],
      totalCount: 0,
      loading: false,
      currentPage: 1,
      pageSize: 50,
      finishedQtyDialogVisible: false,
      finishedQtyLoading: false,
      finishedQtyData: [],
      finishedQtyOrderNumber: ''
    }
  },
  computed: {
    paginatedData() {
      const start = (this.currentPage - 1) * this.pageSize
      return this.tableData.slice(start, start + this.pageSize)
    },
    totalPages() {
      return this.tableData.length ? Math.ceil(this.tableData.length / this.pageSize) : 1
    },
    overallSummary() {
      return {
        订单数量: this.sumField(this.tableData, '订单数量'),
        完成数量: this.sumField(this.tableData, '完成数量'),
        未完成数量: this.sumField(this.tableData, '未完成数量')
      }
    },
    finishedQtyColumns() {
      if (!this.finishedQtyData.length) return []
      return Object.keys(this.finishedQtyData[0])
    }
  },
  mounted() {
    this.fetchWorkshops()
    this.handleSearch()
  },
  methods: {
    hasPermission(code) {
      return authStore.getPermissions().includes(code)
    },
    async fetchWorkshops() {
      try {
        const res = await axios.get('/api/assembly-production/workshops')
        if (res.data.status === 'success') this.workshops = res.data.data || []
      } catch (error) {
        this.$message.error('获取车间列表失败')
      }
    },
    async handleSearch() {
      this.loading = true
      try {
        const params = {}
        Object.keys(this.searchForm).forEach(key => {
          if (this.searchForm[key]) params[key] = this.searchForm[key]
        })
        const res = await axios.get('/api/assembly-production/query', { params })
        if (res.data.status === 'success') {
          this.tableData = res.data.data || []
          this.totalCount = res.data.total || this.tableData.length
          this.currentPage = 1
        }
      } catch (error) {
        this.$message.error('查询失败')
      } finally {
        this.loading = false
      }
    },
    handleReset() {
      this.searchForm = { 区域: '', 订单批号: '', 客户: '', 料品编码: '', 料品名称: '', 开始日期: '', 结束日期: '', 进度状态: [] }
      this.handleSearch()
    },
    formatRawValue(value) {
      if (value === null || value === undefined) return ''
      if (value instanceof Date) {
        const y = value.getFullYear()
        const m = String(value.getMonth() + 1).padStart(2, '0')
        const d = String(value.getDate()).padStart(2, '0')
        const hh = String(value.getHours()).padStart(2, '0')
        const mm = String(value.getMinutes()).padStart(2, '0')
        const ss = String(value.getSeconds()).padStart(2, '0')
        return `${y}-${m}-${d} ${hh}:${mm}:${ss}`
      }
      return String(value)
    },
    async handleViewAllFinishedQty(row) {
      const orderNumber = row && (row.订单批号 || row.订单号 || '')
      if (!orderNumber) {
        this.$message.warning('没有可用的订单批号')
        return
      }

      this.finishedQtyLoading = true
      try {
        const res = await axios.get('/api/checklist/finished-qty-all', {
          params: { OrderNumber: orderNumber }
        })
        if (res.data && res.data.status === 'success') {
          this.finishedQtyOrderNumber = orderNumber
          this.finishedQtyData = this.sortFinishedQtyRows(res.data.data || [])
          this.finishedQtyDialogVisible = true
        } else {
          this.$message.error((res.data && res.data.message) || '查询失败')
        }
      } catch (error) {
        const msg = error && error.response && error.response.data && error.response.data.message
        this.$message.error(msg || '查询失败，请查看后端日志')
      } finally {
        this.finishedQtyLoading = false
      }
    },
    async handleExport() {
      try {
        const params = {}
        Object.keys(this.searchForm).forEach(key => {
          const value = this.searchForm[key]
          if (Array.isArray(value)) {
            if (value.length > 0) params[key] = value
            return
          }
          if (value) params[key] = value
        })

        const res = await axios.get('/api/assembly-production/export', {
          params,
          responseType: 'blob'
        })

        const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        const now = new Date()
        const ts = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`
        link.href = url
        link.download = `装嵌生产进度_${ts}.xlsx`
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(url)
        this.$message.success('导出成功')
      } catch (error) {
        const msg = error && error.response && error.response.status === 403 ? '没有导出权限' : '导出失败'
        this.$message.error(msg)
      }
    },
    handleCurrentChange(val) {
      this.currentPage = val
    },
    handleSizeChange(val) {
      this.pageSize = val
      this.currentPage = 1
    },
    sortFinishedQtyRows(rows) {
      const timeKeys = ['FinishedDate', 'finished_date', '完成时间', '报工时间', '时间', 'CreateDate', 'CreatedAt', 'CreateTime', 'UpdateTime', '修改时间', '录入时间']
      const parseTime = (value) => {
        if (value === null || value === undefined || value === '') return 0
        if (value instanceof Date) return value.getTime()
        const date = new Date(value)
        if (!Number.isNaN(date.getTime())) return date.getTime()
        const text = String(value).trim()
        if (!text) return 0
        const normalized = text.replace(/\//g, '-')
        const fallback = new Date(normalized)
        return Number.isNaN(fallback.getTime()) ? 0 : fallback.getTime()
      }

      const getRowTime = (row) => {
        for (const key of timeKeys) {
          if (row && row[key] !== undefined && row[key] !== null && String(row[key]).trim() !== '') {
            return parseTime(row[key])
          }
        }
        return 0
      }

      return [...rows].sort((left, right) => getRowTime(right) - getRowTime(left))
    },
    indexMethod(index) {
      return (this.currentPage - 1) * this.pageSize + index + 1
    },
    formatDate(value) {
      if (!value) return ''
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return String(value)
      const y = d.getFullYear()
      const m = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${y}-${m}-${day}`
    },
    sumField(rows, field) {
      return rows.reduce((acc, row) => acc + (Number(row[field]) || 0), 0)
    },
    getSummaries({ columns, data }) {
      const sums = []
      columns.forEach((column, index) => {
        if (index === 0) {
          sums[index] = '当前页合计'
          return
        }
        if (['订单数量', '完成数量', '未完成数量'].includes(column.property)) {
          sums[index] = this.sumField(data, column.property).toLocaleString()
        } else {
          sums[index] = ''
        }
      })
      return sums
    },
    getStatusType(status) {
      const map = { '已完成': 'success', '进行中': 'primary', '未开始': 'info', '已逾期': 'danger', '即将逾期': 'warning' }
      return map[status] || 'info'
    }
  }
}
</script>

<style scoped>
.finished-qty-table-wrap {
  max-height: 60vh;
  overflow: auto;
}

.finished-qty-dialog ::v-deep .el-dialog {
  margin: 0 auto !important;
  height: 96vh;
  display: flex;
  flex-direction: column;
}

.finished-qty-dialog ::v-deep .el-dialog__body {
  flex: 1;
  overflow: hidden;
  padding: 16px 20px 20px;
}
</style>
