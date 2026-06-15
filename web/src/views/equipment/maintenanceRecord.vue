<template>
  <div class="maintenance-record">
    <div class="page-container">
      <el-card shadow="never" class="maintenance-record__toolbar">
        <el-form :model="queryForm" inline label-width="80px">
          <el-form-item label="维保单号">
            <el-input v-model="queryForm.recordNo" placeholder="MR-" clearable class="maintenance-record__input" />
          </el-form-item>
          <el-form-item label="维保类型">
            <el-select v-model="queryForm.maintainType" placeholder="全部" clearable class="maintenance-record__select">
              <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="queryForm.status" placeholder="全部" clearable class="maintenance-record__select">
              <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button type="primary" plain @click="openDialog()">新建维保</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <el-table :data="tableData" stripe border>
          <el-table-column prop="recordNo" label="维保单号" width="130" />
          <el-table-column prop="equipmentCode" label="设备编号" width="110" />
          <el-table-column prop="equipmentName" label="设备名称" min-width="130" />
          <el-table-column prop="maintainType" label="类型" width="90" />
          <el-table-column prop="faultDesc" label="故障/保养描述" min-width="180" show-overflow-tooltip />
          <el-table-column prop="technician" label="维修人" width="90" />
          <el-table-column prop="startTime" label="开始时间" width="160" />
          <el-table-column prop="endTime" label="完成时间" width="160" />
          <el-table-column prop="cost" label="费用(元)" width="100" align="right" />
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'processing'"
                link
                type="success"
                @click="handleFinish(row)"
              >
                完成
              </el-button>
              <el-button link type="primary" @click="openDialog(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog v-model="dialogVisible" title="维保登记" width="560px" destroy-on-close>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
          <el-form-item label="设备编号" prop="equipmentCode">
            <el-select v-model="form.equipmentCode" class="maintenance-record__full" @change="onEquipmentChange">
              <el-option
                v-for="eq in equipmentOptions"
                :key="eq.code"
                :label="`${eq.code} - ${eq.name}`"
                :value="eq.code"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="维保类型" prop="maintainType">
            <el-radio-group v-model="form.maintainType">
              <el-radio label="保养">定期保养</el-radio>
              <el-radio label="维修">故障维修</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="描述" prop="faultDesc">
            <el-input v-model="form.faultDesc" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="维修人" prop="technician">
            <el-input v-model="form.technician" />
          </el-form-item>
          <el-form-item label="预估费用">
            <el-input-number v-model="form.cost" :min="0" :precision="2" class="maintenance-record__full" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSave">提交</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

defineOptions({ name: 'MaintenanceRecord' })

type MaintainStatus = 'processing' | 'completed' | 'cancelled'

interface MaintainRow {
  id: number
  recordNo: string
  equipmentCode: string
  equipmentName: string
  maintainType: string
  faultDesc: string
  technician: string
  startTime: string
  endTime: string
  cost: number
  status: MaintainStatus
}

const typeOptions = ['保养', '维修']
const statusOptions = [
  { value: 'processing', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
]

const equipmentOptions = [
  { code: 'EQ-A001', name: '数控钻孔机' },
  { code: 'EQ-A008', name: 'LDI 曝光机' },
  { code: 'EQ-B012', name: '垂直电镀线' },
  { code: 'EQ-B020', name: '螺杆空压机' },
]

const queryForm = reactive({
  recordNo: '',
  maintainType: '',
  status: '' as '' | MaintainStatus,
})

const allData = ref<MaintainRow[]>([
  { id: 1, recordNo: 'MR-202605010', equipmentCode: 'EQ-A008', equipmentName: 'LDI 曝光机', maintainType: '维修', faultDesc: '光源强度衰减，需更换 UV 模块', technician: '设备科-陈工', startTime: '2026-05-20 08:30', endTime: '', cost: 0, status: 'processing' },
  { id: 2, recordNo: 'MR-202605008', equipmentCode: 'EQ-B020', equipmentName: '螺杆空压机', maintainType: '保养', faultDesc: '季度保养：更换机油、空滤', technician: '动力班-刘师傅', startTime: '2026-05-19 14:00', endTime: '2026-05-19 17:30', cost: 1280, status: 'completed' },
  { id: 3, recordNo: 'MR-202605005', equipmentCode: 'EQ-A001', equipmentName: '数控钻孔机', maintainType: '保养', faultDesc: '主轴润滑、导轨清洁', technician: '设备科-周工', startTime: '2026-05-18 09:00', endTime: '2026-05-18 11:20', cost: 450, status: 'completed' },
  { id: 4, recordNo: 'MR-202604099', equipmentCode: 'EQ-B012', equipmentName: '垂直电镀线', maintainType: '维修', faultDesc: '槽体温度传感器异常', technician: '电镀班-吴工', startTime: '2026-05-15 10:00', endTime: '2026-05-16 16:00', cost: 3200, status: 'completed' },
])

const tableData = ref([...allData.value])
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  equipmentCode: '',
  equipmentName: '',
  maintainType: '维修',
  faultDesc: '',
  technician: '',
  cost: 0,
})

const rules: FormRules = {
  equipmentCode: [{ required: true, message: '请选择设备', trigger: 'change' }],
  faultDesc: [{ required: true, message: '请输入描述', trigger: 'blur' }],
  technician: [{ required: true, message: '请输入维修人', trigger: 'blur' }],
}

function statusLabel(s: MaintainStatus) {
  return statusOptions.find((o) => o.value === s)?.label ?? s
}

function statusTag(s: MaintainStatus): 'warning' | 'success' | 'info' {
  return s === 'processing' ? 'warning' : s === 'completed' ? 'success' : 'info'
}

function onEquipmentChange(code: string) {
  const eq = equipmentOptions.find((e) => e.code === code)
  form.equipmentName = eq?.name ?? ''
}

function applyFilter() {
  tableData.value = allData.value.filter((r) => {
    const m1 = !queryForm.recordNo || r.recordNo.includes(queryForm.recordNo)
    const m2 = !queryForm.maintainType || r.maintainType === queryForm.maintainType
    const m3 = !queryForm.status || r.status === queryForm.status
    return m1 && m2 && m3
  })
}

function handleSearch() {
  applyFilter()
  ElMessage.success(`共 ${tableData.value.length} 条维保记录`)
}

function openDialog(row?: MaintainRow) {
  if (row) {
    Object.assign(form, {
      equipmentCode: row.equipmentCode,
      equipmentName: row.equipmentName,
      maintainType: row.maintainType,
      faultDesc: row.faultDesc,
      technician: row.technician,
      cost: row.cost,
    })
    dialogVisible.value = true
    return
  }
  Object.assign(form, {
    equipmentCode: '',
    equipmentName: '',
    maintainType: '维修',
    faultDesc: '',
    technician: '',
    cost: 0,
  })
  dialogVisible.value = true
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  const maxId = Math.max(0, ...allData.value.map((r) => r.id))
  const now = new Date().toISOString().slice(0, 16).replace('T', ' ')
  allData.value.unshift({
    id: maxId + 1,
    recordNo: `MR-202605${String(maxId + 1).padStart(3, '0')}`,
    equipmentName: form.equipmentName,
    startTime: now,
    endTime: '',
    status: 'processing',
    equipmentCode: form.equipmentCode,
    maintainType: form.maintainType,
    faultDesc: form.faultDesc,
    technician: form.technician,
    cost: form.cost,
  })
  dialogVisible.value = false
  applyFilter()
  ElMessage.success('维保单已提交')
}

function handleFinish(row: MaintainRow) {
  row.status = 'completed'
  row.endTime = new Date().toISOString().slice(0, 16).replace('T', ' ')
  if (!row.cost) row.cost = 500
  ElMessage.success(`${row.recordNo} 已完成`)
}
</script>

<style scoped lang="scss">
.maintenance-record {
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
