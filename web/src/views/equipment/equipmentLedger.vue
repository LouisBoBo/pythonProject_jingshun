<template>
  <div class="equipment-ledger">
    <div class="page-container">
      <el-card shadow="never" class="equipment-ledger__toolbar">
        <el-form :model="queryForm" inline label-width="80px">
          <el-form-item label="设备编号">
            <el-input v-model="queryForm.code" placeholder="EQ-" clearable class="equipment-ledger__input" />
          </el-form-item>
          <el-form-item label="设备名称">
            <el-input v-model="queryForm.name" placeholder="关键词" clearable class="equipment-ledger__input" />
          </el-form-item>
          <el-form-item label="运行状态">
            <el-select v-model="queryForm.runStatus" placeholder="全部" clearable class="equipment-ledger__select">
              <el-option v-for="s in runStatusOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button type="primary" plain @click="openDialog()">登记设备</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <el-table :data="tableData" stripe border>
          <el-table-column prop="code" label="设备编号" width="120" />
          <el-table-column prop="name" label="设备名称" min-width="140" />
          <el-table-column prop="model" label="型号规格" width="140" />
          <el-table-column prop="category" label="设备类别" width="100" />
          <el-table-column prop="factory" label="所在工厂" width="90" />
          <el-table-column prop="location" label="安装位置" width="120" />
          <el-table-column prop="runStatus" label="运行状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="runTagType(row.runStatus)" size="small">
                {{ runLabel(row.runStatus) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="purchaseDate" label="购置日期" width="110" />
          <el-table-column prop="nextMaintain" label="下次保养" width="110" />
          <el-table-column label="操作" width="140" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
              <el-button link type="warning" @click="handleMaintain(row)">报修</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog v-model="dialogVisible" :title="editId ? '编辑设备' : '登记设备'" width="520px" destroy-on-close>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
          <el-form-item label="设备名称" prop="name">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="型号规格" prop="model">
            <el-input v-model="form.model" />
          </el-form-item>
          <el-form-item label="设备类别" prop="category">
            <el-select v-model="form.category" class="equipment-ledger__full">
              <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item label="所在工厂" prop="factory">
            <el-select v-model="form.factory" class="equipment-ledger__full">
              <el-option label="一厂" value="一厂" />
              <el-option label="二厂" value="二厂" />
              <el-option label="三厂" value="三厂" />
            </el-select>
          </el-form-item>
          <el-form-item label="安装位置" prop="location">
            <el-input v-model="form.location" />
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
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'

defineOptions({ name: 'EquipmentLedger' })

type RunStatus = 'running' | 'idle' | 'fault' | 'maintain'

interface EquipmentRow {
  id: number
  code: string
  name: string
  model: string
  category: string
  factory: string
  location: string
  runStatus: RunStatus
  purchaseDate: string
  nextMaintain: string
}

const categoryOptions = ['钻孔设备', '电镀设备', '曝光设备', '检测仪器', '空压机']
const runStatusOptions = [
  { value: 'running', label: '运行中' },
  { value: 'idle', label: '待机' },
  { value: 'fault', label: '故障' },
  { value: 'maintain', label: '保养中' },
]

const queryForm = reactive({ code: '', name: '', runStatus: '' as '' | RunStatus })

const allData = ref<EquipmentRow[]>([
  { id: 1, code: 'EQ-A001', name: '数控钻孔机', model: 'DX-8800', category: '钻孔设备', factory: '一厂', location: '钻孔车间 A 线', runStatus: 'running', purchaseDate: '2022-03-15', nextMaintain: '2026-06-01' },
  { id: 2, code: 'EQ-B012', name: '垂直电镀线', model: 'VPL-200', category: '电镀设备', factory: '二厂', location: '电镀车间 2#', runStatus: 'running', purchaseDate: '2021-08-20', nextMaintain: '2026-05-28' },
  { id: 3, code: 'EQ-A008', name: 'LDI 曝光机', model: 'LDI-Pro', category: '曝光设备', factory: '一厂', location: '图形转移区', runStatus: 'fault', purchaseDate: '2023-01-10', nextMaintain: '2026-05-25' },
  { id: 4, code: 'EQ-C003', name: 'AOI 光学检测仪', model: 'AOI-X5', category: '检测仪器', factory: '三厂', location: '终检工位', runStatus: 'idle', purchaseDate: '2023-06-01', nextMaintain: '2026-07-10' },
  { id: 5, code: 'EQ-B020', name: '螺杆空压机', model: 'AC-75KW', category: '空压机', factory: '二厂', location: '动力站房', runStatus: 'maintain', purchaseDate: '2020-11-05', nextMaintain: '2026-05-21' },
])

const tableData = ref([...allData.value])
const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  model: '',
  category: '',
  factory: '一厂',
  location: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  model: [{ required: true, message: '请输入型号', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类别', trigger: 'change' }],
  location: [{ required: true, message: '请输入安装位置', trigger: 'blur' }],
}

function runLabel(s: RunStatus) {
  return runStatusOptions.find((o) => o.value === s)?.label ?? s
}

function runTagType(s: RunStatus): 'success' | 'info' | 'danger' | 'warning' {
  const map: Record<RunStatus, 'success' | 'info' | 'danger' | 'warning'> = {
    running: 'success',
    idle: 'info',
    fault: 'danger',
    maintain: 'warning',
  }
  return map[s]
}

function applyFilter() {
  tableData.value = allData.value.filter((r) => {
    const m1 = !queryForm.code || r.code.includes(queryForm.code)
    const m2 = !queryForm.name || r.name.includes(queryForm.name)
    const m3 = !queryForm.runStatus || r.runStatus === queryForm.runStatus
    return m1 && m2 && m3
  })
}

function handleSearch() {
  applyFilter()
  ElMessage.success(`共 ${tableData.value.length} 台设备`)
}

function openDialog(row?: EquipmentRow) {
  editId.value = row?.id ?? null
  if (row) {
    Object.assign(form, {
      name: row.name,
      model: row.model,
      category: row.category,
      factory: row.factory,
      location: row.location,
    })
  } else {
    Object.assign(form, { name: '', model: '', category: '', factory: '一厂', location: '' })
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
    ElMessage.success('设备信息已更新')
  } else {
    const maxId = Math.max(0, ...allData.value.map((r) => r.id))
    allData.value.push({
      id: maxId + 1,
      code: `EQ-X${String(maxId + 1).padStart(3, '0')}`,
      runStatus: 'idle',
      purchaseDate: '2026-05-21',
      nextMaintain: '2026-08-21',
      ...form,
    })
    ElMessage.success('设备已登记')
  }
  dialogVisible.value = false
  applyFilter()
}

async function handleMaintain(row: EquipmentRow) {
  try {
    await ElMessageBox.confirm(`确认为设备「${row.name}」创建维保工单？`, '报修')
    row.runStatus = 'fault'
    ElMessage.success('已生成维保申请')
  } catch {
    /* cancel */
  }
}
</script>

<style scoped lang="scss">
.equipment-ledger {
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
