<template>
  <div class="work-order-list">
    <div class="page-container">
      <el-card shadow="never" class="work-order-list__toolbar">
        <el-form :model="queryForm" inline label-width="80px">
          <el-form-item label="工单号">
            <el-input v-model="queryForm.orderNo" placeholder="WO-" clearable class="work-order-list__input" />
          </el-form-item>
          <el-form-item label="工单类型">
            <el-select v-model="queryForm.type" placeholder="全部" clearable class="work-order-list__select">
              <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="queryForm.status" placeholder="全部" clearable class="work-order-list__select">
              <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="工厂">
            <el-select v-model="queryForm.factory" placeholder="全部" clearable class="work-order-list__select">
              <el-option v-for="f in factoryOptions" :key="f" :label="f" :value="f" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button type="primary" plain @click="openDialog()">新建工单</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <el-table :data="tableData" stripe border>
          <el-table-column prop="orderNo" label="工单号" width="140" />
          <el-table-column prop="type" label="类型" width="100" />
          <el-table-column prop="title" label="工单标题" min-width="180" show-overflow-tooltip />
          <el-table-column prop="material" label="关联物料" min-width="160" show-overflow-tooltip />
          <el-table-column prop="qty" label="数量" width="90" align="right" />
          <el-table-column prop="factory" label="工厂" width="80" />
          <el-table-column prop="assignee" label="负责人" width="90" />
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="deadline" label="要求完成" width="120" />
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
              <el-button
                v-if="row.status === 'pending'"
                link
                type="success"
                @click="handleStart(row)"
              >
                开工
              </el-button>
              <el-button
                v-if="row.status === 'processing'"
                link
                type="warning"
                @click="handleComplete(row)"
              >
                完工
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog
        v-model="dialogVisible"
        :title="editId ? '编辑工单' : '新建工单'"
        width="560px"
        destroy-on-close
      >
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
          <el-form-item label="工单类型" prop="type">
            <el-select v-model="form.type" placeholder="请选择" class="work-order-list__full">
              <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="工单标题" prop="title">
            <el-input v-model="form.title" placeholder="简要描述工单内容" />
          </el-form-item>
          <el-form-item label="关联物料" prop="material">
            <el-input v-model="form.material" placeholder="物料代码或描述" />
          </el-form-item>
          <el-form-item label="数量" prop="qty">
            <el-input-number v-model="form.qty" :min="1" class="work-order-list__full" />
          </el-form-item>
          <el-form-item label="工厂" prop="factory">
            <el-select v-model="form.factory" class="work-order-list__full">
              <el-option v-for="f in factoryOptions" :key="f" :label="f" :value="f" />
            </el-select>
          </el-form-item>
          <el-form-item label="负责人" prop="assignee">
            <el-input v-model="form.assignee" />
          </el-form-item>
          <el-form-item label="要求完成" prop="deadline">
            <el-date-picker
              v-model="form.deadline"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              class="work-order-list__full"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSave">保存</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

defineOptions({ name: 'WorkOrderList' })

type OrderStatus = 'pending' | 'processing' | 'completed' | 'closed'

interface WorkOrderRow {
  id: number
  orderNo: string
  type: string
  title: string
  material: string
  qty: number
  factory: string
  assignee: string
  status: OrderStatus
  deadline: string
}

const typeOptions = ['领料工单', '补料工单', '退料工单', '盘点工单']
const factoryOptions = ['一厂', '二厂', '三厂']
const statusOptions = [
  { value: 'pending', label: '待开工' },
  { value: 'processing', label: '进行中' },
  { value: 'completed', label: '已完工' },
  { value: 'closed', label: '已关闭' },
]

const queryForm = reactive({
  orderNo: '',
  type: '',
  status: '' as '' | OrderStatus,
  factory: '',
})

const allData = ref<WorkOrderRow[]>([
  { id: 1, orderNo: 'WO-202605001', type: '领料工单', title: 'HDI线急单领用覆铜板', material: 'FR-4 覆铜板 1.6MM', qty: 200, factory: '一厂', assignee: '张三', status: 'processing', deadline: '2026-05-22' },
  { id: 2, orderNo: 'WO-202605002', type: '补料工单', title: '二厂阻焊油墨补库', material: '阻焊油墨 绿色', qty: 50, factory: '二厂', assignee: '李四', status: 'pending', deadline: '2026-05-23' },
  { id: 3, orderNo: 'WO-202605003', type: '盘点工单', title: '三厂化学品月度盘点', material: '显影液等', qty: 1, factory: '三厂', assignee: '王五', status: 'completed', deadline: '2026-05-20' },
  { id: 4, orderNo: 'WO-202604088', type: '退料工单', title: '一厂多余铜箔退库', material: '电解铜箔 35um', qty: 120, factory: '一厂', assignee: '赵六', status: 'closed', deadline: '2026-05-15' },
])

const tableData = ref<WorkOrderRow[]>([...allData.value])
const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  type: '',
  title: '',
  material: '',
  qty: 1,
  factory: '一厂',
  assignee: '',
  deadline: '',
})

const rules: FormRules = {
  type: [{ required: true, message: '请选择工单类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  material: [{ required: true, message: '请输入关联物料', trigger: 'blur' }],
  assignee: [{ required: true, message: '请输入负责人', trigger: 'blur' }],
  deadline: [{ required: true, message: '请选择完成日期', trigger: 'change' }],
}

function statusLabel(s: OrderStatus) {
  return statusOptions.find((o) => o.value === s)?.label ?? s
}

function statusTagType(s: OrderStatus): 'info' | 'warning' | 'success' {
  const map: Record<OrderStatus, 'info' | 'warning' | 'success'> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    closed: 'info',
  }
  return map[s]
}

function applyFilter() {
  tableData.value = allData.value.filter((row) => {
    const m1 = !queryForm.orderNo || row.orderNo.includes(queryForm.orderNo)
    const m2 = !queryForm.type || row.type === queryForm.type
    const m3 = !queryForm.status || row.status === queryForm.status
    const m4 = !queryForm.factory || row.factory === queryForm.factory
    return m1 && m2 && m3 && m4
  })
}

function handleSearch() {
  applyFilter()
  ElMessage.success(`共 ${tableData.value.length} 条`)
}

function openDialog(row?: WorkOrderRow) {
  editId.value = row?.id ?? null
  if (row) {
    Object.assign(form, {
      type: row.type,
      title: row.title,
      material: row.material,
      qty: row.qty,
      factory: row.factory,
      assignee: row.assignee,
      deadline: row.deadline,
    })
  } else {
    Object.assign(form, {
      type: '',
      title: '',
      material: '',
      qty: 1,
      factory: '一厂',
      assignee: '',
      deadline: '',
    })
  }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  if (editId.value) {
    const row = allData.value.find((r) => r.id === editId.value)
    if (row) Object.assign(row, form)
    ElMessage.success('工单已更新')
  } else {
    const maxId = Math.max(0, ...allData.value.map((r) => r.id))
    allData.value.unshift({
      id: maxId + 1,
      orderNo: `WO-202605${String(maxId + 1).padStart(3, '0')}`,
      status: 'pending',
      ...form,
    })
    ElMessage.success('工单已创建')
  }
  dialogVisible.value = false
  applyFilter()
}

function handleStart(row: WorkOrderRow) {
  row.status = 'processing'
  ElMessage.success(`${row.orderNo} 已开工`)
}

function handleComplete(row: WorkOrderRow) {
  row.status = 'completed'
  ElMessage.success(`${row.orderNo} 已完工`)
}
</script>

<style scoped lang="scss">
.work-order-list {
  &__toolbar {
    margin-bottom: 16px;
  }

  &__input {
    width: 140px;
  }

  &__select {
    width: 120px;
  }

  &__full {
    width: 100%;
  }
}
</style>
