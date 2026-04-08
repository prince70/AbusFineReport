<template>
  <app-layout title="角色管理" :breadcrumb="['系统管理', '角色管理']">
    <el-card>
      <el-form inline>
        <el-form-item><el-button type="primary" v-if="hasPermission('role:add')" @click="handleAdd">新增角色</el-button></el-form-item>
      </el-form>
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="角色名" align="center" />
        <el-table-column prop="description" label="描述" align="center" />
        <el-table-column prop="permissions" label="权限" align="center">
          <template slot-scope="scope">
            <el-tag v-for="p in scope.row.permissions" :key="p" style="margin: 2px" size="small">{{ p }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="可访问页面" min-width="220" align="center">
          <template slot-scope="scope">
            <el-tag v-for="page in getRolePagesByCodes(scope.row.permissions)" :key="scope.row.id + '-page-' + page" size="mini" style="margin:2px">{{ page }}</el-tag>
            <span v-if="!getRolePagesByCodes(scope.row.permissions).length" style="color:#909399">无</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" align="center" v-if="hasPermission('role:edit') || hasPermission('role:delete')">
          <template slot-scope="scope">
            <el-button size="small" v-if="hasPermission('role:edit')" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" v-if="hasPermission('role:delete')" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog :title="dialogTitle" :visible.sync="dialogVisible" width="620px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="form.permissions">
            <el-checkbox v-for="perm in allPermissions" :key="perm.id" :label="perm.id">{{ perm.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="可访问页面">
          <el-tag v-for="page in currentRolePages" :key="'role-form-' + page" size="small" style="margin:2px">{{ page }}</el-tag>
          <span v-if="!currentRolePages.length" style="color:#909399">请选择权限后查看</span>
        </el-form-item>
      </el-form>
      <span slot="footer"><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="handleSave">保存</el-button></span>
    </el-dialog>
  </app-layout>
</template>

<script>
import axios from 'axios'
import authStore from '@/services/auth'
import AppLayout from '@/components/AppLayout.vue'

export default {
  name: 'RoleManagementPage',
  components: { AppLayout },
  data() {
    return {
      tableData: [],
      allPermissions: [],
      loading: false,
      dialogVisible: false,
      dialogTitle: '新增角色',
      form: { id: null, name: '', description: '', permissions: [] }
    }
  },
  mounted() {
    this.fetchData()
    this.fetchPermissions()
  },
  computed: {
    currentRolePages() {
      const selectedCodes = (this.form.permissions || []).map(id => {
        const perm = this.allPermissions.find(item => item.id === id)
        return perm ? perm.code : ''
      }).filter(Boolean)
      return this.getRolePagesByCodes(selectedCodes)
    }
  },
  methods: {
    hasPermission(code) {
      return authStore.getPermissions().includes(code)
    },
    getRolePagesByCodes(codes) {
      const pages = new Set(['首页'])
      const map = {
        'assembly:query': ['装嵌生产进度'],
        'checklist:query': ['外协加工清单'],
        'user:view': ['用户管理'],
        'role:view': ['角色管理']
      }
      ;(codes || []).forEach(code => {
        (map[code] || []).forEach(page => pages.add(page))
      })
      return Array.from(pages)
    },
    async fetchData() {
      this.loading = true
      try {
        const res = await axios.get('/api/roles')
        if (res.data.status === 'success') this.tableData = res.data.data || []
      } catch (error) {
        this.$message.error('获取角色列表失败')
      } finally {
        this.loading = false
      }
    },
    async fetchPermissions() {
      try {
        const res = await axios.get('/api/permissions')
        if (res.data.status === 'success') this.allPermissions = res.data.data || []
      } catch (error) {
        // Keep silent.
      }
    },
    handleAdd() {
      this.form = { id: null, name: '', description: '', permissions: [] }
      this.dialogTitle = '新增角色'
      this.dialogVisible = true
    },
    handleEdit(row) {
      const map = {}
      this.allPermissions.forEach(item => { map[item.code] = item.id })
      this.form = {
        id: row.id,
        name: row.name,
        description: row.description,
        permissions: (row.permissions || []).map(code => map[code]).filter(Boolean)
      }
      this.dialogTitle = '编辑角色'
      this.dialogVisible = true
    },
    async handleSave() {
      try {
        if (!this.form.name) {
          this.$message.warning('请输入角色名')
          return
        }
        let res
        if (this.form.id) {
          res = await axios.put('/api/roles/' + this.form.id, this.form)
        } else {
          res = await axios.post('/api/roles', this.form)
        }
        if (res.data.status !== 'success') {
          this.$message.error(res.data.message || '保存失败')
          return
        }
        this.$message.success('保存成功')
        this.dialogVisible = false
        this.fetchData()
      } catch (error) {
        this.$message.error('保存失败')
      }
    },
    async handleDelete(row) {
      try {
        await this.$confirm('确认删除角色 ' + row.name + ' ?', '提示', { type: 'warning' })
        const res = await axios.delete('/api/roles/' + row.id)
        if (res.data.status === 'success') {
          this.$message.success('删除成功')
          this.fetchData()
        } else {
          this.$message.error(res.data.message || '删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') this.$message.error('删除失败')
      }
    }
  }
}
</script>
