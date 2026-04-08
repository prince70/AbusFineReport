<template>
  <app-layout title="用户管理" :breadcrumb="['系统管理', '用户管理']">
    <el-card>
      <el-form inline>
        <el-form-item><el-button type="primary" v-if="hasPermission('user:add')" @click="handleAdd">新增用户</el-button></el-form-item>
      </el-form>
      <el-table :data="tableData" v-loading="loading" border stripe>
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="username" label="用户名" align="center" />
        <el-table-column prop="nickname" label="昵称" align="center" />
        <el-table-column prop="email" label="邮箱" align="center" />
        <el-table-column prop="roles" label="角色" align="center" />
        <el-table-column label="可访问页面" min-width="240" align="center">
          <template slot-scope="scope">
            <el-tag v-for="page in getUserPageAccess(scope.row)" :key="scope.row.id + '-' + page" size="mini" style="margin:2px">{{ page }}</el-tag>
            <span v-if="!getUserPageAccess(scope.row).length" style="color:#909399">无</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" align="center">
          <template slot-scope="scope"><el-tag :type="scope.row.status === 1 ? 'success' : 'danger'" size="small">{{ scope.row.status === 1 ? '启用' : '禁用' }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" align="center" width="170" />
        <el-table-column label="操作" width="180" align="center" v-if="hasPermission('user:edit') || hasPermission('user:delete')">
          <template slot-scope="scope">
            <el-button size="small" v-if="hasPermission('user:edit')" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" v-if="hasPermission('user:delete')" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog :title="dialogTitle" :visible.sync="dialogVisible" width="520px">
      <el-form :model="form" label-width="84px">
        <el-form-item label="用户名"><el-input v-model="form.username" :disabled="!!form.id" /></el-form-item>
        <el-form-item label="密码" v-if="!form.id"><el-input v-model="form.password" type="password" /></el-form-item>
        <el-form-item label="昵称"><el-input v-model="form.nickname" /></el-form-item>
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item label="状态"><el-radio-group v-model="form.status"><el-radio :label="1">启用</el-radio><el-radio :label="0">禁用</el-radio></el-radio-group></el-form-item>
        <el-form-item label="角色">
          <el-checkbox-group v-model="form.roles">
            <el-checkbox v-for="role in allRoles" :key="role.id" :label="role.id">{{ role.name }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="可访问页面">
          <el-tag v-for="page in currentUserPageAccess" :key="'user-form-' + page" size="small" style="margin:2px">{{ page }}</el-tag>
          <span v-if="!currentUserPageAccess.length" style="color:#909399">请选择角色后查看</span>
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
  name: 'UserManagementPage',
  components: { AppLayout },
  data() {
    return {
      tableData: [],
      allRoles: [],
      loading: false,
      dialogVisible: false,
      dialogTitle: '新增用户',
      form: { id: null, username: '', password: '', nickname: '', email: '', status: 1, roles: [] }
    }
  },
  mounted() {
    this.fetchData()
    this.fetchRoles()
  },
  computed: {
    currentUserPageAccess() {
      const pages = new Set(['首页'])
      const permissionCodes = new Set()
      this.allRoles.forEach(role => {
        if (this.form.roles.includes(role.id)) {
          (role.permissions || []).forEach(code => permissionCodes.add(code))
        }
      })
      this.mapPermissionsToPages(Array.from(permissionCodes)).forEach(page => pages.add(page))
      return Array.from(pages)
    }
  },
  methods: {
    hasPermission(code) {
      return authStore.getPermissions().includes(code)
    },
    mapPermissionsToPages(permissionCodes) {
      const pages = new Set()
      const map = {
        'assembly:query': ['装嵌生产进度'],
        'checklist:query': ['外协加工清单'],
        'user:view': ['用户管理'],
        'role:view': ['角色管理']
      }
      ;(permissionCodes || []).forEach(code => {
        (map[code] || []).forEach(page => pages.add(page))
      })
      return Array.from(pages)
    },
    getUserPageAccess(row) {
      const names = String((row && row.roles) || '').split(',').map(v => v.trim()).filter(Boolean)
      const permissionCodes = new Set()
      this.allRoles.forEach(role => {
        if (names.includes(role.name)) {
          (role.permissions || []).forEach(code => permissionCodes.add(code))
        }
      })
      const pages = new Set(['首页'])
      this.mapPermissionsToPages(Array.from(permissionCodes)).forEach(page => pages.add(page))
      return Array.from(pages)
    },
    async fetchData() {
      this.loading = true
      try {
        const res = await axios.get('/api/users')
        if (res.data.status === 'success') this.tableData = res.data.data || []
      } catch (error) {
        this.$message.error('获取用户列表失败')
      } finally {
        this.loading = false
      }
    },
    async fetchRoles() {
      try {
        const res = await axios.get('/api/roles')
        if (res.data.status === 'success') this.allRoles = res.data.data || []
      } catch (error) {
        // Keep silent.
      }
    },
    handleAdd() {
      this.form = { id: null, username: '', password: '', nickname: '', email: '', status: 1, roles: [] }
      this.dialogTitle = '新增用户'
      this.dialogVisible = true
    },
    handleEdit(row) {
      const roleIds = []
      if (row.roles) {
        row.roles.split(',').forEach(name => {
          const role = this.allRoles.find(item => item.name === name)
          if (role) roleIds.push(role.id)
        })
      }
      this.form = { id: row.id, username: row.username, password: '', nickname: row.nickname, email: row.email, status: row.status, roles: roleIds }
      this.dialogTitle = '编辑用户'
      this.dialogVisible = true
    },
    async handleSave() {
      try {
        if (!this.form.id && (!this.form.username || !this.form.password)) {
          this.$message.warning('请输入用户名和密码')
          return
        }
        const data = { nickname: this.form.nickname, email: this.form.email, status: this.form.status, roles: this.form.roles }
        let res
        if (this.form.id) {
          res = await axios.put('/api/users/' + this.form.id, data)
        } else {
          res = await axios.post('/api/users', Object.assign(data, { username: this.form.username, password: this.form.password }))
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
        await this.$confirm('确认删除用户 ' + row.username + ' ?', '提示', { type: 'warning' })
        const res = await axios.delete('/api/users/' + row.id)
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
