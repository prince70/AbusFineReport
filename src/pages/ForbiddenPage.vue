<template>
  <app-layout title="无权限访问" :breadcrumb="['系统', '无权限']">
    <el-result icon="warning" title="无访问权限" sub-title="当前账号没有访问该模块的权限，请联系管理员分配权限。">
      <template slot="extra">
        <el-button type="primary" @click="$router.push('/dashboard')">返回首页</el-button>
      </template>
    </el-result>
  </app-layout>
</template>

<script>
import AppLayout from '@/components/AppLayout.vue'

export default {
  name: 'ForbiddenPage',
  components: { AppLayout }
}
</script>
