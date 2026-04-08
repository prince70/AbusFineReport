<template>
  <app-layout title="外协加工清单" :breadcrumb="['报表', '外协加工清单']">
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
        <div class="sheet-title">外协加工清单</div>
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
        <div>来源：SQL Server / dbo.昨日打磨数据_外协</div>
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
      searchForm: { 开始日期: '', 结束日期: '', 订单批号: '', 外协件名称: '', 规格型号: '', 区域: '' },
      tableData: [],
      totalCount: 0,
      loading: false
    }
  },
  computed: {
    displayDate() {
      const value = this.searchForm.结束日期 || this.searchForm.开始日期
      if (!value) return ''
      const d = new Date(value)
      if (Number.isNaN(d.getTime())) return value
      return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
    },
    tableColumns() {
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
        { prop: '上线日期', label: '上线日期', width: 110 },
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
      const sum = prop => this.tableData.reduce((acc, row) => acc + (Number(row[prop]) || 0), 0)
      return {
        订单数量: formatNum(sum('订单数量')),
        毛重: formatNum(sum('毛重')),
        净重: formatNum(sum('净重')),
        盆数: formatNum(sum('盆数'))
      }
    }
  },
  methods: {
    formatCell(value, prop, row) {
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
      const params = {}
      Object.keys(this.searchForm).forEach(k => {
        const raw = this.searchForm[k]
        if (raw === null || raw === undefined) return
        const value = typeof raw === 'string' ? raw.trim() : raw
        if (value === '') return
        params[k] = value
      })

      try {
        const res = await axios.get('/api/checklist/query', { params })
        if (res.data && res.data.status === 'success') {
          this.tableData = res.data.data || []
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
      this.searchForm = { 开始日期: '', 结束日期: '', 订单批号: '', 外协件名称: '', 规格型号: '', 区域: '' }
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
        const data = this.tableData.map(r => this.tableColumns.map(c => this.resolveCellValue(r, c)))
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

        const mergeTargetProps = ['备注', '毛重', '净重', '盆数']
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
    }
  },
  mounted() {
    this.handleSearch()
  }
}
</script>
