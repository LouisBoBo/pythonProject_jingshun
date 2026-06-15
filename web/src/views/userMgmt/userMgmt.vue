<template>
  <div class="user-mgmt">
    <div class="page-container">
      <el-card shadow="never" class="user-mgmt__toolbar">
        <el-form :model="queryForm" inline>
          <el-form-item label="用户名">
            <el-input
              v-model="queryForm.username"
              placeholder="请输入"
              clearable
              class="user-mgmt__input"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="queryForm.status"
              placeholder="全部"
              clearable
              class="user-mgmt__select"
            >
              <el-option label="启用" value="enabled" />
              <el-option label="禁用" value="disabled" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button type="primary" plain @click="handleCreate">新建用户</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <el-table :data="pagedList" stripe border>
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column prop="nickname" label="姓名" width="100" />
          <el-table-column prop="role" label="角色" width="120" />
          <el-table-column prop="factory" label="所属工厂" width="100" />
          <el-table-column prop="phone" label="手机号" width="130" />
          <el-table-column prop="status" label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small">
                {{ row.status === 'enabled' ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="lastLogin" label="最后登录" width="170" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-button
                link
                :type="row.status === 'enabled' ? 'warning' : 'success'"
                @click="handleToggleStatus(row)"
              >
                {{ row.status === 'enabled' ? '禁用' : '启用' }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="user-mgmt__pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :total="filteredList.length"
            :page-sizes="[5, 10, 20]"
            layout="total, sizes, prev, pager, next"
            background
          />
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

defineOptions({ name: 'UserMgmt' })

type UserStatus = 'enabled' | 'disabled'

interface UserRow {
  id: number
  username: string
  nickname: string
  role: string
  factory: string
  phone: string
  status: UserStatus
  lastLogin: string
}

const queryForm = reactive({
  username: '',
  status: '' as '' | UserStatus,
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
})

const allUsers = ref<UserRow[]>([
  { id: 1, username: 'zhangsan', nickname: '张三', role: '物料查询员', factory: '一厂', phone: '138****1001', status: 'enabled', lastLogin: '2026-05-21 14:30' },
  { id: 2, username: 'lisi', nickname: '李四', role: '物料查询员', factory: '二厂', phone: '139****2002', status: 'enabled', lastLogin: '2026-05-21 09:15' },
  { id: 3, username: 'wangwu', nickname: '王五', role: '数据分析师', factory: '一厂', phone: '137****3003', status: 'enabled', lastLogin: '2026-05-20 17:42' },
  { id: 4, username: 'zhaoliu', nickname: '赵六', role: '系统管理员', factory: '全公司', phone: '136****4004', status: 'enabled', lastLogin: '2026-05-19 11:00' },
  { id: 5, username: 'sunqi', nickname: '孙七', role: '物料查询员', factory: '三厂', phone: '135****5005', status: 'disabled', lastLogin: '2026-04-28 08:20' },
  { id: 6, username: 'zhouba', nickname: '周八', role: '只读用户', factory: '二厂', phone: '134****6006', status: 'enabled', lastLogin: '2026-05-18 16:55' },
])

const filteredList = ref<UserRow[]>([...allUsers.value])

const pagedList = computed(() => {
  const start = (pagination.page - 1) * pagination.pageSize
  return filteredList.value.slice(start, start + pagination.pageSize)
})

function applyFilter() {
  filteredList.value = allUsers.value.filter((u) => {
    const matchName =
      !queryForm.username ||
      u.username.includes(queryForm.username) ||
      u.nickname.includes(queryForm.username)
    const matchStatus = !queryForm.status || u.status === queryForm.status
    return matchName && matchStatus
  })
  pagination.page = 1
}

function handleSearch() {
  applyFilter()
  ElMessage.success(`共 ${filteredList.value.length} 条`)
}

function handleCreate() {
  ElMessage.info('新建用户（模拟）')
}

function handleEdit(row: UserRow) {
  ElMessage.info(`编辑用户：${row.nickname}`)
}

function handleToggleStatus(row: UserRow) {
  row.status = row.status === 'enabled' ? 'disabled' : 'enabled'
  ElMessage.success(`已${row.status === 'enabled' ? '启用' : '禁用'} ${row.nickname}`)
}
</script>

<style scoped lang="scss">
.user-mgmt {
  &__toolbar {
    margin-bottom: 16px;
  }

  &__input {
    width: 160px;
  }

  &__select {
    width: 120px;
  }

  &__pagination {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}
</style>
