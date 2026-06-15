<template>
  <div class="supplier-archive">
    <div class="page-container">
      <el-card shadow="never" class="supplier-archive__toolbar">
        <el-form :model="queryForm" inline label-width="90px">
          <el-form-item label="供应商编码">
            <el-input v-model="queryForm.code" placeholder="SUP-" clearable class="supplier-archive__input" />
          </el-form-item>
          <el-form-item label="供应商名称">
            <el-input v-model="queryForm.name" placeholder="关键词" clearable class="supplier-archive__input" />
          </el-form-item>
          <el-form-item label="供应类别">
            <el-select v-model="queryForm.category" placeholder="全部" clearable class="supplier-archive__select">
              <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item label="合作状态">
            <el-select v-model="queryForm.coopStatus" placeholder="全部" clearable class="supplier-archive__select">
              <el-option v-for="s in coopOptions" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button type="primary" plain @click="openDialog()">新增供应商</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <el-table :data="tableData" stripe border>
          <el-table-column prop="code" label="编码" width="110" />
          <el-table-column prop="name" label="供应商名称" min-width="160" />
          <el-table-column prop="category" label="供应类别" width="100" />
          <el-table-column prop="contact" label="联系人" width="90" />
          <el-table-column prop="phone" label="联系电话" width="130" />
          <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
          <el-table-column prop="rating" label="评级" width="80" align="center">
            <template #default="{ row }">
              <el-rate v-model="row.rating" disabled show-score score-template="{value}" />
            </template>
          </el-table-column>
          <el-table-column prop="coopStatus" label="合作状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="coopTag(row.coopStatus)" size="small">{{ coopLabel(row.coopStatus) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="contractEnd" label="合同到期" width="110" />
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
              <el-button link type="primary" @click="showMaterials(row)">供应物料</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-dialog v-model="dialogVisible" :title="editId ? '编辑供应商' : '新增供应商'" width="560px" destroy-on-close>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
          <el-form-item label="供应商名称" prop="name">
            <el-input v-model="form.name" />
          </el-form-item>
          <el-form-item label="供应类别" prop="category">
            <el-select v-model="form.category" class="supplier-archive__full">
              <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item label="联系人" prop="contact">
            <el-input v-model="form.contact" />
          </el-form-item>
          <el-form-item label="联系电话" prop="phone">
            <el-input v-model="form.phone" />
          </el-form-item>
          <el-form-item label="地址" prop="address">
            <el-input v-model="form.address" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSave">保存</el-button>
        </template>
      </el-dialog>

      <el-drawer v-model="drawerVisible" :title="`供应物料 - ${currentSupplier?.name}`" size="480px">
        <el-table :data="materialList" stripe size="small">
          <el-table-column prop="materialCode" label="物料代码" width="120" />
          <el-table-column prop="materialName" label="物料名称" min-width="160" />
          <el-table-column prop="unit" label="单位" width="60" />
          <el-table-column prop="leadDays" label="交货周期(天)" width="110" align="right" />
        </el-table>
      </el-drawer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

defineOptions({ name: 'SupplierArchive' })

type CoopStatus = 'active' | 'suspended' | 'trial'

interface SupplierRow {
  id: number
  code: string
  name: string
  category: string
  contact: string
  phone: string
  address: string
  rating: number
  coopStatus: CoopStatus
  contractEnd: string
}

interface SupplyMaterial {
  materialCode: string
  materialName: string
  unit: string
  leadDays: number
}

const categoryOptions = ['覆铜板', '化学品', '油墨', '铜箔', '五金配件']
const coopOptions = [
  { value: 'active', label: '合作中' },
  { value: 'trial', label: '试合作' },
  { value: 'suspended', label: '已暂停' },
]

const queryForm = reactive({
  code: '',
  name: '',
  category: '',
  coopStatus: '' as '' | CoopStatus,
})

const allData = ref<SupplierRow[]>([
  { id: 1, code: 'SUP-001', name: '华南覆铜板有限公司', category: '覆铜板', contact: '陈经理', phone: '0755-88881001', address: '深圳市宝安区工业园 A 区', rating: 4.5, coopStatus: 'active', contractEnd: '2026-12-31' },
  { id: 2, code: 'SUP-012', name: '精工化学材料（苏州）', category: '化学品', contact: '王小姐', phone: '0512-66662002', address: '苏州市吴中区化工园', rating: 4, coopStatus: 'active', contractEnd: '2027-03-15' },
  { id: 3, code: 'SUP-018', name: '日研感光材料贸易', category: '油墨', contact: '田中', phone: '021-58883003', address: '上海市浦东新区张江', rating: 3.5, coopStatus: 'trial', contractEnd: '2026-08-30' },
  { id: 4, code: 'SUP-025', name: '江铜电解铜箔事业部', category: '铜箔', contact: '李总', phone: '0791-77774004', address: '南昌市高新区', rating: 5, coopStatus: 'active', contractEnd: '2027-06-30' },
  { id: 5, code: 'SUP-033', name: '东莞五金配件厂', category: '五金配件', contact: '张厂长', phone: '0769-22225005', address: '东莞市长安镇', rating: 3, coopStatus: 'suspended', contractEnd: '2025-12-31' },
])

const materialMap: Record<string, SupplyMaterial[]> = {
  'SUP-001': [
    { materialCode: 'RM-2024001', materialName: 'FR-4 覆铜板 1.6MM', unit: '张', leadDays: 7 },
    { materialCode: 'RM-2024091', materialName: 'FR-4 覆铜板 0.8MM', unit: '张', leadDays: 10 },
  ],
  'SUP-012': [
    { materialCode: 'RM-2024078', materialName: '显影液 弱碱性', unit: 'L', leadDays: 5 },
  ],
  'SUP-018': [
    { materialCode: 'RM-2024012', materialName: '阻焊油墨 绿色', unit: 'KG', leadDays: 14 },
  ],
  'SUP-025': [
    { materialCode: 'RM-2024033', materialName: '电解铜箔 35um', unit: 'KG', leadDays: 12 },
  ],
  'SUP-033': [],
}

const tableData = ref([...allData.value])
const dialogVisible = ref(false)
const drawerVisible = ref(false)
const editId = ref<number | null>(null)
const currentSupplier = ref<SupplierRow | null>(null)
const materialList = ref<SupplyMaterial[]>([])
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  category: '',
  contact: '',
  phone: '',
  address: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择类别', trigger: 'change' }],
  contact: [{ required: true, message: '请输入联系人', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入电话', trigger: 'blur' }],
}

function coopLabel(s: CoopStatus) {
  return coopOptions.find((o) => o.value === s)?.label ?? s
}

function coopTag(s: CoopStatus): 'success' | 'warning' | 'info' {
  const map: Record<CoopStatus, 'success' | 'warning' | 'info'> = {
    active: 'success',
    trial: 'warning',
    suspended: 'info',
  }
  return map[s]
}

function applyFilter() {
  tableData.value = allData.value.filter((r) => {
    const m1 = !queryForm.code || r.code.includes(queryForm.code)
    const m2 = !queryForm.name || r.name.includes(queryForm.name)
    const m3 = !queryForm.category || r.category === queryForm.category
    const m4 = !queryForm.coopStatus || r.coopStatus === queryForm.coopStatus
    return m1 && m2 && m3 && m4
  })
}

function handleSearch() {
  applyFilter()
  ElMessage.success(`共 ${tableData.value.length} 家供应商`)
}

function openDialog(row?: SupplierRow) {
  editId.value = row?.id ?? null
  if (row) {
    Object.assign(form, {
      name: row.name,
      category: row.category,
      contact: row.contact,
      phone: row.phone,
      address: row.address,
    })
  } else {
    Object.assign(form, { name: '', category: '', contact: '', phone: '', address: '' })
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
    ElMessage.success('供应商已更新')
  } else {
    const maxId = Math.max(0, ...allData.value.map((r) => r.id))
    const code = `SUP-${String(maxId + 1).padStart(3, '0')}`
    allData.value.push({
      id: maxId + 1,
      code,
      rating: 3,
      coopStatus: 'trial',
      contractEnd: '2027-12-31',
      ...form,
    })
    materialMap[code] = []
    ElMessage.success('供应商已新增')
  }
  dialogVisible.value = false
  applyFilter()
}

function showMaterials(row: SupplierRow) {
  currentSupplier.value = row
  materialList.value = materialMap[row.code] ?? []
  drawerVisible.value = true
}
</script>

<style scoped lang="scss">
.supplier-archive {
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
