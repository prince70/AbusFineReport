<template>
  <app-layout :title="pageTitle" :breadcrumb="pageBreadcrumb">
    <div v-if="loading" class="global-loading-mask">
      <i class="el-icon-loading"></i>
      <span>查询中...</span>
    </div>
    <el-card>
      <el-form :model="searchForm" inline>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="searchForm.开始日期"
            type="datetime"
            value-format="yyyy-MM-dd HH:mm:ss"
            placeholder="选择开始日期时间"
            style="width: 220px"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="searchForm.结束日期"
            type="datetime"
            value-format="yyyy-MM-dd HH:mm:ss"
            placeholder="选择结束日期时间"
            style="width: 220px"
          />
        </el-form-item>
        <el-form-item label="订单批号"><el-input v-model="searchForm.订单批号" placeholder="订单批号" /></el-form-item>
        <el-form-item label="外协件名称"><el-input v-model="searchForm.外协件名称" placeholder="外协件名称" /></el-form-item>
        <el-form-item label="型号规格"><el-input v-model="searchForm.规格型号" placeholder="型号规格" /></el-form-item>
        <el-form-item label="区域"><el-input v-model="searchForm.区域" placeholder="区域" /></el-form-item>
        <el-form-item v-if="workshopCode === 'body'" label="生产车间">
          <el-input v-model="searchForm.生产车间" placeholder="生产车间" />
        </el-form-item>
        <el-form-item v-if="workshopCode === 'body'" label="筛选条件">
          <el-checkbox v-model="searchForm.st">合金锁体</el-checkbox>
          <el-checkbox v-model="searchForm.st2" style="margin-left: 12px;">铜产品</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="loading">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="success" @click="handleExport" :disabled="!tableData.length">导出Excel</el-button>
          <el-button @click="handlePrint" :disabled="!tableData.length">打印</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top:12px;">
      <div class="sheet-title-block">
        <div class="sheet-company">万晖五金（深圳）有限公司</div>
        <div class="sheet-title">{{ pageTitle }}</div>
      </div>

      <div class="sheet-doc-head">
        <div class="sheet-doc-row">
          <div class="sheet-doc-cell">供方</div>
          <div class="sheet-doc-cell">外协日期</div>
          <div class="sheet-doc-cell">{{ displayDate }}</div>
          <div class="sheet-doc-cell">外协单号：{{ searchForm.订单批号 || '' }}</div>
        </div>
      </div>

      <div class="sheet-table-wrap">
        <el-table
          :data="tableData"
          border
          stripe
          fit
          highlight-current-row
          :header-cell-style="headerCellStyle"
          :cell-style="cellStyle"
          :span-method="objectSpanMethod"
          style="width: 100%; min-width: 2400px;"
          empty-text="暂无数据"
        >
          <el-table-column type="index" label="序号" width="60" align="center" fixed="left" />
          <el-table-column v-for="column in tableColumns" :key="column.prop" :prop="column.prop" :label="column.label" :width="column.width" :min-width="column.minWidth" :align="column.align || 'center'" show-overflow-tooltip>
            <template slot-scope="scope">
              <span :class="column.align === 'right' ? 'numeric-cell' : ''">{{ ['交货期限', '订单整货期'].includes(column.prop) ? formatMonthDay(scope.row[column.prop]) : formatCell(scope.row[column.prop], column.prop, scope.row) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="sheet-summary">
        <div>总记录数：<strong>{{ totalCount }}</strong></div>
        <div>当前展示：<strong>{{ tableData.length }}</strong></div>
        <div>
          全部统计：
          订单数量 <strong>{{ overallSummary.订单数量 }}</strong>，
          毛重 <strong>{{ overallSummary.毛重 }}</strong>，
          净重 <strong>{{ overallSummary.净重 }}</strong>，
          盆数 <strong>{{ overallSummary.盆数 }}</strong>
        </div>
        <div>来源：SQL Server / dbo.{{ sourceTable }}</div>
      </div>

      <div class="sheet-footer-note">
        <div>发货人：</div>
        <div>车间主任：</div>
        <div>物流部：</div>
        <div>采购部：</div>
        <div>经收人：</div>
      </div>
    </el-card>
  </app-layout>
</template>

<script>
import axios from 'axios'
import AppLayout from '@/components/AppLayout.vue'

export default {
  name: 'ChecklistPage',
  components: { AppLayout },
  data() {
    return {
      searchForm: { 开始日期: '', 结束日期: '', 订单批号: '', 外协件名称: '', 规格型号: '', 区域: '', 生产车间: '', st: false, st2: false },
      tableData: [],
      backendColumns: [],
      totalCount: 0,
      loading: false
    }
  },
  computed: {
    isKeyTemplateMode() {
      return this.workshopCode === 'key'
    },
    isBodyTemplateMode() {
      return this.workshopCode === 'body'
    },
    isCoreTemplateMode() {
      return this.workshopCode === 'core'
    },
    isRawSqlMode() {
      return this.workshopCode === 'beam'
    },
    workshopCode() {
      return (this.$route.meta && this.$route.meta.workshop) || 'grinding'
    },
    workshopLabel() {
      return (this.$route.meta && this.$route.meta.workshopLabel) || '打磨车间'
    },
    sourceTable() {
      return (this.$route.meta && this.$route.meta.sourceTable) || '昨日打磨数据_外协'
    },
    pageTitle() {
      return `外协加工清单 - ${this.workshopLabel}`
    },
    pageBreadcrumb() {
      return ['报表', '外协加工清单', this.workshopLabel]
    },
    displayDate() {
      const value = this.searchForm.结束日期 || this.searchForm.开始日期
      if (!value) return ''
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return value
      return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
    },
    tableColumns() {
      if (this.isKeyTemplateMode) {
        return [
          { prop: '订单号', label: '订单号', width: 160 },
          { prop: '外协件名称', label: '外协件名称', width: 120 },
          { prop: '型号规格', label: '型号/规格', minWidth: 200, align: 'left' },
          { prop: '数量', label: '数量', width: 95, align: 'right' },
          { prop: '单位', label: '单位', width: 70 },
          { prop: '备注', label: '备注', width: 90, align: 'right' },
          { prop: '外协项目', label: '外协项目', width: 120, align: 'left' },
          { prop: '品质要求', label: '品质要求', width: 170, align: 'left' },
          { prop: '交货期限', label: '交货期限', width: 100 },
          { prop: '料品编码', label: '料品编码', width: 130 },
          { prop: '订单落货期', label: '订单落货期', width: 110 }
        ]
      }
      if (this.isCoreTemplateMode) {
        return [
          { prop: '订单号', label: '订单号', width: 200 },
          { prop: '外协件名称', label: '外协件名称', width: 120 },
          { prop: '型号规格', label: '型号/规格', minWidth: 100, align: 'left' },
          { prop: '原料厂家', label: '原料厂家', width: 100 },
          { prop: '数量', label: '数量', width: 90, align: 'right' },
          { prop: '单位', label: '单位', width: 70 },
          { prop: '备注', label: '备注', width: 140, align: 'right' },
          { prop: '外协项目', label: '外协项目', width: 120, align: 'left' },
          { prop: '品质要求', label: '品质要求', width: 170, align: 'left' },
          { prop: '交货期限', label: '交货期限', width: 130 },
          { prop: '料品编码', label: '料品编码', width: 150 },
          { prop: '落货日期', label: '落货日期', width: 100 },
          { prop: '合计件', label: '合计：件', width: 90, align: 'right' },
          { prop: '净重', label: '净重', width: 90, align: 'right' },
          { prop: '毛重', label: '毛重', width: 90, align: 'right' }
        ]
      }
      if (this.isBodyTemplateMode) {
        return [
          { prop: '订单号', label: '订单号', width: 150 },
          { prop: '外协件名称', label: '外协件名称', width: 120 },
          { prop: '型号规格', label: '型号/规格', minWidth: 180, align: 'left' },
          { prop: '原料厂家', label: '原料/厂家', width: 100 },
          { prop: '数量', label: '数（重）量', width: 95, align: 'right' },
          { prop: '单位', label: '单位', width: 70 },
          { prop: '备注', label: '备注', minWidth: 120, align: 'left' },
          { prop: '外协项目', label: '外协项目', width: 110, align: 'left' },
          { prop: '品质要求', label: '品质要求', width: 160, align: 'left' },
          { prop: '交货期限', label: '交货期限', width: 110 },
          { prop: '料品编码', label: '料品编码', width: 100 },
          { prop: '订单整货期', label: '订单落货期', width: 110 },
          { prop: '合计件', label: '合计-件', width: 90, align: 'right' },
          { prop: '净重', label: '净重', width: 85, align: 'right' },
          { prop: '换算', label: '换算', width: 85, align: 'right' },
          { prop: '型号规格原料厂家', label: '型号/规格 原料/厂家', minWidth: 180, align: 'left' },
          { prop: '料品编码', label: '料品编码', width: 130 }
        ]
      }
      if (this.isRawSqlMode) {
        const first = this.tableData[0] || {}
        const orderedColumns = this.backendColumns.length ? this.backendColumns : Object.keys(first)
        return orderedColumns
          .filter((key) => this.hasColumnData(key))
          .map((key) => ({
          prop: key,
          label: key,
          minWidth: 140,
          align: this.isNumericColumn(key) ? 'right' : 'center'
          }))
      }
      return [
        { prop: '订单号', label: '订单号', width: 170 },
        { prop: '外协件名称', label: '外协件名称', width: 120 },
        { prop: '规格型号', label: '型号/规格', minWidth: 180, align: 'left' },
        { prop: '订单数量', label: '数（重）量', width: 110, align: 'right' },
        { prop: '单位', label: '单位', width: 80 },
        { prop: '备注', label: '备注', width: 130, align: 'left' },
        { prop: '外协项目', label: '外协项目', width: 120, align: 'left' },
        { prop: '品质要求', label: '品质要求', width: 220, align: 'left' },
        { prop: '交货期限', label: '交货期限', width: 110 },
        { prop: '料品编码', label: '料品编码', width: 110 },
        { prop: '订单整货期', label: '订单落货期', width: 110 },
        { prop: '责任车间', label: '责任车间', width: 110 },
        { prop: '毛重', label: '毛重', width: 90, align: 'right' },
        { prop: '净重', label: '净重', width: 90, align: 'right' },
        { prop: '盆数', label: '盆数', width: 100, align: 'right' }
      ]
    },
    overallSummary() {
      const formatNum = (value) => {
        if (!Number.isFinite(value)) return '0'
        if (Math.abs(value - Math.round(value)) < 1e-9) return String(Math.round(value))
        return value.toFixed(2)
      }
      const firstRow = this.tableData[0] || {}
      const quantityProp = ['合计件', '数量', '订单数量', 'EachFinishedQty', 'FinishedQty'].find(k => Object.prototype.hasOwnProperty.call(firstRow, k)) || '订单数量'
      const sum = prop => this.tableData.reduce((acc, row) => acc + (Number(row[prop]) || 0), 0)
      return {
        订单数量: formatNum(sum(quantityProp)),
        毛重: formatNum(sum('毛重')),
        净重: formatNum(sum('净重')),
        盆数: formatNum(sum('盆数'))
      }
    },
  },
  methods: {
    hasColumnData(prop) {
      return this.tableData.some((row) => {
        const value = row ? row[prop] : undefined
        if (value === null || value === undefined) return false
        if (typeof value === 'string') return value.trim() !== ''
        return true
      })
    },
    isNumericColumn(prop) {
      const lowered = String(prop || '').toLowerCase()
      return ['qty', 'count', 'num', 'weight', '重量', '数量', '毛重', '净重', '盆数', '单重'].some(token => lowered.includes(token))
    },
    formatCell(value, prop, row) {
      if (this.isKeyTemplateMode) {
        if (['交货期限', '订单落货期'].includes(prop)) {
          return this.formatMonthDay(value)
        }
        if (['数量', '备注'].includes(prop)) {
          const num = Number(value)
          if (!Number.isFinite(num)) return ''
          if (Math.abs(num - Math.round(num)) < 1e-9) return String(Math.round(num))
          return num.toFixed(2)
        }
        if (value === null || value === undefined) return ''
        return String(value)
      }
      if (this.isCoreTemplateMode) {
        if (['交货期限', '落货日期'].includes(prop)) {
          return this.formatMonthDay(value)
        }
        if (['数量', '合计件', '净重', '毛重'].includes(prop)) {
          const num = Number(value)
          if (!Number.isFinite(num)) return ''
          if (Math.abs(num - Math.round(num)) < 1e-9) return String(Math.round(num))
          return num.toFixed(2)
        }
        if (value === null || value === undefined) return ''
        return String(value)
      }
      if (this.isBodyTemplateMode) {
        if (['交货期限', '料品编码', '订单整货期'].includes(prop)) {
          return this.formatMonthDay(value)
        }
        if (prop === '净重') {
          const num = Number(value)
          if (!Number.isFinite(num)) return ''
          return num.toFixed(2)
        }
        if (['数量', '合计件', '净重', '换算'].includes(prop)) {
          const num = Number(value)
          if (!Number.isFinite(num)) return ''
          if (Math.abs(num - Math.round(num)) < 1e-9) return String(Math.round(num))
          return num.toFixed(2)
        }
        if (value === null || value === undefined) return ''
        return String(value)
      }
      if (this.isRawSqlMode) {
        if (this.workshopCode === 'key' && ['确定交期', 'FinishedDate'].includes(prop)) {
          return this.formatShortDateTime(value)
        }
        if (value === null || value === undefined) return ''
        return String(value)
      }
      if (prop === '责任车间' && (value === null || value === undefined || String(value).trim() === '')) {
        const fallback = (row && (row.分区 || row.锁类分区)) || ''
        return String(fallback)
      }
      if (prop === '毛重' && (value === null || value === undefined || String(value).trim() === '')) {
        const fallbackWeight = row && (row.净重 !== null && row.净重 !== undefined && String(row.净重).trim() !== '') ? row.净重 : 0
        return String(fallbackWeight)
      }
      if (prop === '盆数') {
        const num = Number(value)
        if (!Number.isFinite(num)) return '0'
        if (Math.abs(num - Math.round(num)) < 1e-9) return String(Math.round(num))
        return num.toFixed(2)
      }
      if (value === null || value === undefined) return ''
      return String(value)
    },
    resolveCellValue(row, column) {
      if (this.isKeyTemplateMode) {
        return this.formatCell(row[column.prop], column.prop, row)
      }
      if (this.isCoreTemplateMode) {
        return this.formatCell(row[column.prop], column.prop, row)
      }
      if (this.isBodyTemplateMode) {
        return this.formatCell(row[column.prop], column.prop, row)
      }
      if (this.isRawSqlMode) {
        return this.formatCell(row[column.prop], column.prop, row)
      }
      if (['交货期限', '订单整货期'].includes(column.prop)) {
        return this.formatMonthDay(row[column.prop])
      }
      return this.formatCell(row[column.prop], column.prop, row)
    },
    async ensureXlsx() {
      const mod = await import('xlsx-js-style')
      return mod.default || mod
    },
    formatMonthDay(value) {
      if (!value) return ''
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return String(value)
      return `${d.getMonth() + 1}月${d.getDate()}日`
    },
    formatShortDateTime(value) {
      if (!value) return ''
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return String(value)
      const pad = n => String(n).padStart(2, '0')
      return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
    },
    headerCellStyle({ columnIndex }) {
      return {
        background: columnIndex === 0 ? '#fafafa' : '#ffffff',
        color: '#303133',
        fontWeight: '600',
        borderColor: '#dcdfe6',
        textAlign: 'center'
      }
    },
    cellStyle() {
      return {
        borderColor: '#dcdfe6',
        whiteSpace: 'nowrap'
      }
    },
    async handleSearch() {
      this.loading = true
      const params = { 车间类型: this.workshopCode }
      Object.keys(this.searchForm).forEach(k => {
        const raw = this.searchForm[k]
        if (raw === null || raw === undefined) return
        if (typeof raw === 'boolean') {
          if (raw) params[k] = true
          return
        }
        const value = typeof raw === 'string' ? raw.trim() : raw
        if (value === '') return
        params[k] = value
      })

      try {
        const res = await axios.get('/api/checklist/query', { params })
        if (res.data && res.data.status === 'success') {
          const rawData = res.data.data || []
          if (this.isKeyTemplateMode) {
            this.tableData = rawData.map(row => this.normalizeKeyRow(row))
          } else if (this.isCoreTemplateMode) {
            this.tableData = this.buildCoreGroupedRows(rawData.map(row => this.normalizeCoreRow(row)))
          } else if (this.isBodyTemplateMode) {
            this.tableData = rawData.map(row => this.normalizeBodyRow(row))
          } else {
            this.tableData = rawData
          }
          this.backendColumns = Array.isArray(res.data.columns) ? res.data.columns : []
          this.totalCount = res.data.total || this.tableData.length
        } else {
          this.$message.error((res.data && res.data.message) || '查询失败')
        }
      } catch (err) {
        const msg = err && err.response && err.response.data && err.response.data.message
        this.$message.error(msg || '查询失败，请查看后端日志')
      } finally {
        this.loading = false
      }
    },
    handleReset() {
      this.searchForm = { 开始日期: '', 结束日期: '', 订单批号: '', 外协件名称: '', 规格型号: '', 区域: '', 生产车间: '', st: false, st2: false }
      this.backendColumns = []
      this.handleSearch()
    },
    async handleExport() {
      if (!this.tableData.length) {
        this.$message.warning('暂无数据')
        return
      }
      try {
        const XLSX = await this.ensureXlsx()
        const colCount = this.tableColumns.length
        const titleRow = new Array(colCount).fill('')
        const subTitleRow = new Array(colCount).fill('')
        const blankRow = new Array(colCount).fill('')
        const infoRow = new Array(colCount).fill('')

        titleRow[0] = '万晖五金（深圳）有限公司'
        subTitleRow[0] = '外协加工清单'
        infoRow[0] = '供方'
        if (colCount >= 4) {
          infoRow[1] = '外协日期'
          infoRow[2] = this.displayDate || ''
          infoRow[3] = `外协单号：${this.searchForm.订单批号 || ''}`
        }

        const columns = this.tableColumns.map(c => c.label)
        const numericColumns = ['数量', '订单数量', '合计件', '净重', '毛重', '盆数', '单重', '换算', 'EachFinishedQty', 'FinishedQty']
        const numericColIndexes = this.tableColumns
          .map((c, idx) => numericColumns.includes(c.prop) ? idx : -1)
          .filter(idx => idx >= 0)
        
        const data = this.tableData.map(r => this.tableColumns.map((c, cIdx) => {
          const value = this.resolveCellValue(r, c)
          if (numericColIndexes.includes(cIdx)) {
            const num = Number(value)
            return Number.isFinite(num) ? num : value
          }
          return value
        }))
        const aoa = [titleRow, subTitleRow, blankRow, infoRow, columns].concat(data)
        const ws = XLSX.utils.aoa_to_sheet(aoa)

        const merges = [
          { s: { r: 0, c: 0 }, e: { r: 0, c: colCount - 1 } },
          { s: { r: 1, c: 0 }, e: { r: 1, c: colCount - 1 } }
        ]
        if (colCount >= 4) {
          merges.push({ s: { r: 3, c: 0 }, e: { r: 3, c: 0 } })
          merges.push({ s: { r: 3, c: 1 }, e: { r: 3, c: 1 } })
          merges.push({ s: { r: 3, c: 2 }, e: { r: 3, c: 2 } })
          merges.push({ s: { r: 3, c: 3 }, e: { r: 3, c: colCount - 1 } })
        }

        const mergeTargetProps = ['备注', '合计件', '毛重', '净重', '盆数']
        const headerOffset = 5
        const getSpecKey = row => (row.规格型号分组 || row.规格型号 || '').toString()

        mergeTargetProps.forEach(prop => {
          const colIndex = this.tableColumns.findIndex(c => c.prop === prop)
          if (colIndex < 0) return

          let start = 0
          while (start < this.tableData.length) {
            const currentKey = getSpecKey(this.tableData[start])
            let end = start
            while (end + 1 < this.tableData.length && getSpecKey(this.tableData[end + 1]) === currentKey) {
              end++
            }
            if (end > start) {
              merges.push({ s: { r: headerOffset + start, c: colIndex }, e: { r: headerOffset + end, c: colIndex } })
            }
            start = end + 1
          }
        })

        ws['!merges'] = merges
        ws['!cols'] = this.tableColumns.map(c => ({ wch: Math.max(12, Math.ceil((c.width || c.minWidth || 120) / 10)) }))
        ws['!rows'] = [{ hpt: 26 }, { hpt: 22 }, { hpt: 8 }, { hpt: 20 }, { hpt: 20 }]

        const centerStyle = { alignment: { horizontal: 'center', vertical: 'center', wrapText: true } }
        const headerStyle = { alignment: { horizontal: 'center', vertical: 'center', wrapText: true }, font: { bold: true } }

        const setStyle = (r, c, style) => {
          const ref = XLSX.utils.encode_cell({ r, c })
          if (!ws[ref]) ws[ref] = { t: 's', v: '' }
          ws[ref].s = Object.assign({}, ws[ref].s || {}, style)
        }

        for (let c = 0; c < colCount; c++) setStyle(4, c, headerStyle)

        setStyle(0, 0, { alignment: { horizontal: 'center', vertical: 'center' }, font: { bold: true, sz: 14 } })
        setStyle(1, 0, { alignment: { horizontal: 'center', vertical: 'center' }, font: { bold: true, sz: 12 } })
        setStyle(3, 0, centerStyle)
        setStyle(3, 1, centerStyle)
        setStyle(3, 2, centerStyle)
        setStyle(3, 3, centerStyle)

        merges.forEach(range => {
          if (range.s.r >= headerOffset) setStyle(range.s.r, range.s.c, centerStyle)
        })

        const mergeTargetColIndexes = mergeTargetProps.map(prop => this.tableColumns.findIndex(c => c.prop === prop)).filter(idx => idx >= 0)
        for (let r = headerOffset; r < headerOffset + this.tableData.length; r++) {
          mergeTargetColIndexes.forEach(c => setStyle(r, c, centerStyle))
        }

        const wb = XLSX.utils.book_new()
        XLSX.utils.book_append_sheet(wb, ws, '清单')

        const now = new Date()
        const pad = n => String(n).padStart(2, '0')
        const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
        XLSX.writeFile(wb, `外协加工清单_${stamp}.xlsx`)
        this.$message.success('导出成功')
      } catch (e) {
        this.$message.error('导出失败，请检查网络后重试')
      }
    },
    objectSpanMethod({ row, columnIndex, rowIndex }) {
      if (this.isKeyTemplateMode) return
      if (this.isCoreTemplateMode) {
        if (columnIndex < 1) return
        const colIndex = columnIndex - 1
        if (colIndex >= this.tableColumns.length) return
        const colProp = this.tableColumns[colIndex].prop
        const coreMergeColumns = ['备注', '合计件', '净重', '毛重']
        if (!coreMergeColumns.includes(colProp)) return

        const currentSpec = row.规格型号分组 || row.型号规格
        if (rowIndex > 0) {
          const prevRow = this.tableData[rowIndex - 1]
          const prevSpec = prevRow ? (prevRow.规格型号分组 || prevRow.型号规格) : ''
          if (prevSpec === currentSpec) return [0, 0]
        }

        let spanRow = 1
        for (let i = rowIndex + 1; i < this.tableData.length; i++) {
          const nextSpec = this.tableData[i].规格型号分组 || this.tableData[i].型号规格
          if (nextSpec === currentSpec) spanRow++
          else break
        }
        return [spanRow, 1]
      }
      if (this.isBodyTemplateMode) return
      if (this.isRawSqlMode) return
      const mergeColumns = ['备注', '毛重', '净重', '盆数']
      if (columnIndex < 1) return

      const colIndex = columnIndex - 1
      if (colIndex >= this.tableColumns.length) return

      const colProp = this.tableColumns[colIndex].prop
      if (!mergeColumns.includes(colProp)) return

      const currentSpec = row.规格型号分组 || row.规格型号
      if (rowIndex > 0) {
        const prevRow = this.tableData[rowIndex - 1]
        const prevSpec = prevRow ? (prevRow.规格型号分组 || prevRow.规格型号) : ''
        if (prevSpec === currentSpec) return [0, 0]
      }

      let spanRow = 1
      for (let i = rowIndex + 1; i < this.tableData.length; i++) {
        const nextSpec = this.tableData[i].规格型号分组 || this.tableData[i].规格型号
        if (nextSpec === currentSpec) spanRow++
        else break
      }
      return [spanRow, 1]
    },
    handlePrint() {
      const w = window.open('', '_blank')
      const style = `
        <style>
          body{font-family: Arial, "Microsoft YaHei", sans-serif;padding:20px;color:#222;}
          .print-title{text-align:center;margin-bottom:12px;}
          .print-title h2{margin:0;font-size:24px;font-weight:700;}
          .print-title .sub{margin-top:6px;font-size:16px;}
          table{border-collapse:collapse;width:100%;min-width:2100px;}
          th,td{border:1px solid #333;padding:6px;font-size:12px;white-space:nowrap;}
          thead th{background:#f5f7fa;text-align:center;}
          .footer{margin-top:16px;display:flex;justify-content:space-between;font-size:13px;}
        </style>`
      const cols = this.tableColumns.map(c => `<th>${c.label}</th>`).join('')
      const rows = this.tableData.map(r => '<tr>' + this.tableColumns.map(c => `<td>${this.resolveCellValue(r, c)}</td>`).join('') + '</tr>').join('')
      const tableHtml = `<table border="1" style="border-collapse:collapse;width:100%"><thead><tr>${cols}</tr></thead><tbody>${rows}</tbody></table>`
      const html = `<div class="print-title"><h2>万晖五金（深圳）有限公司</h2><div class="sub">外协加工清单</div></div>${tableHtml}<div class="footer"><span>发货人：__________</span><span>经收人：__________</span></div>`
      w.document.write(style + html)
      w.document.close()
      w.print()
    },
    pickValue(row, keys) {
      for (const key of keys) {
        if (row && Object.prototype.hasOwnProperty.call(row, key)) {
          return row[key]
        }
      }
      return ''
    },
    normalizeBodyRow(row) {
      const quantity = Number(this.pickValue(row, ['EachFinishedQty', '数量', '订单数量'])) || 0
      const unitWeight = Number(this.pickValue(row, ['物料单重_克', '单重_克'])) || 0
      const netWeight = Number((quantity * unitWeight).toFixed(2))
      const unit = this.pickValue(row, ['unit', '单位']) || ''
      const vendor = this.pickValue(row, ['原料厂家', '生产车间']) || ''
      const spec = this.pickValue(row, ['半成品规格', '规格型号']) || ''

      return {
        订单号: this.pickValue(row, ['OrderNumber', '订单号']),
        外协件名称: this.pickValue(row, ['半成品名称', '外协件名称']),
        型号规格: spec,
        原料厂家: vendor,
        数量: quantity,
        单位: unit,
        备注: this.pickValue(row, ['备注', '算好盆数', '盆数']),
        外协项目: this.pickValue(row, ['外协项目1', '外协项目']),
        品质要求: this.pickValue(row, ['品质要求1', '品质要求']),
        交货期限: this.pickValue(row, ['FinishedDate', '交货期限']),
        料品编码: '',
        订单整货期: this.pickValue(row, ['确定交期', '订单整货期']),
        合计件: quantity,
        净重: netWeight,
        换算: netWeight,
        型号规格原料厂家: `${spec} ${vendor}`.trim(),
        料品编码: this.pickValue(row, ['ItemExternalId', '料品编码'])
      }
    },
    normalizeKeyRow(row) {
      return {
        订单号: this.pickValue(row, ['OrderNumber', '订单号']),
        外协件名称: this.pickValue(row, ['半成品名称', '外协件名称']),
        型号规格: this.pickValue(row, ['半成品规格', '规格型号']),
        数量: Number(this.pickValue(row, ['EachFinishedQty', '数量', '订单数量'])) || 0,
        单位: 'KG',
        备注: this.pickValue(row, ['pot', '盆数', '备注']) || 0,
        外协项目: this.pickValue(row, ['外协项目1', '外协项目']),
        品质要求: this.pickValue(row, ['品质要求1', '品质要求']),
        交货期限: this.pickValue(row, ['FinishedDate', '交货期限']),
        料品编码: this.pickValue(row, ['ItemExternalId', '料品编码']),
        订单落货期: this.pickValue(row, ['确定交期', '订单整货期'])
      }
    },
    normalizeCoreRow(row) {
      const quantity = Number(this.pickValue(row, ['EachFinishedQty'])) || 0
      const unitWeight = Number(this.pickValue(row, ['物料单重_克', '单重_克'])) || 0
      const netWeight = Number((quantity * unitWeight).toFixed(2))
      const grossWeight = Number(this.pickValue(row, ['盆的重量_千克', '毛重'])) || 0
      const originalRemark = Number(this.pickValue(row, ['每盆重量或只数', '备注', '盆数'])) || 0

      return {
        订单号: this.pickValue(row, ['OrderNumber', '订单号']),
        外协件名称: this.pickValue(row, ['半成品名称', '外协件名称']),
        型号规格: this.pickValue(row, ['半成品规格', '规格型号']),
        原料厂家: this.pickValue(row, ['原料厂家', '生产车间']),
        数量: quantity,
        单位: this.pickValue(row, ['单位']),
        备注: originalRemark,
        原备注: originalRemark,
        外协项目: this.pickValue(row, ['外协项目1', '外协项目']),
        品质要求: this.pickValue(row, ['品质要求1', '品质要求']),
        交货期限: this.pickValue(row, ['FinishedDate', '交货期限']),
        料品编码: this.pickValue(row, ['ItemExternalId', '料品编码']),
        落货日期: this.pickValue(row, ['确定交期', '订单整货期', '落货日期']),
        合计件: quantity,
        净重: netWeight,
        毛重: grossWeight
      }
    },
    buildCoreGroupedRows(rows) {
      const formatNum = (num) => {
        const n = Number(num)
        if (!Number.isFinite(n)) return '0'
        if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n))
        return String(Number(n.toFixed(2)))
      }

      const groups = new Map()
      rows.forEach((row) => {
        const spec = (row.型号规格 || '').toString().trim()
        const key = spec || '未填写规格'
        if (!groups.has(key)) groups.set(key, [])
        groups.get(key).push(row)
      })

      const orderedKeys = Array.from(groups.keys()).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))
      const result = []

      orderedKeys.forEach((key) => {
        const groupRows = groups.get(key)
        const totalQty = groupRows.reduce((sum, item) => sum + (Number(item.数量) || 0), 0)
        const totalNetWeight = Number(groupRows.reduce((sum, item) => sum + (Number(item.净重) || 0), 0).toFixed(2))
        const totalGrossWeight = Number(groupRows.reduce((sum, item) => sum + (Number(item.毛重) || 0), 0).toFixed(2))
        const unit = (groupRows[0].单位 || '').toString().toUpperCase()
        const divisor = unit === 'KG' ? 25 : 342
        const quotient = Math.floor(totalQty / divisor)
        const tailValue = totalQty - quotient * divisor
        const mergedRemarkExpr = `${quotient}*${divisor}+${formatNum(tailValue)}`
        const totalPieces = quotient + 1

        groupRows.forEach((item, index) => {
          item.规格型号分组 = key
          item.备注 = index === 0 ? mergedRemarkExpr : ''
          item.合计件 = index === 0 ? totalPieces : ''
          item.净重 = index === 0 ? totalNetWeight : ''
          item.毛重 = index === 0 ? totalGrossWeight : ''
          result.push(item)
        })
      })

      return result
    }
  },
  mounted() {
    this.handleSearch()
  },
  watch: {
    '$route.path'() {
      this.handleSearch()
    }
  }
}
</script>
