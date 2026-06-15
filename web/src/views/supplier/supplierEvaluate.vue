<template>
  <div class="supplier-evaluate">
    <div class="page-container">
      <el-card shadow="never" class="supplier-evaluate__filter">
        <el-form :model="filterForm" inline label-width="90px">
          <el-form-item label="评价周期">
            <el-select v-model="filterForm.period" class="supplier-evaluate__select">
              <el-option label="2026 Q1" value="2026-Q1" />
              <el-option label="2025 Q4" value="2025-Q4" />
            </el-select>
          </el-form-item>
          <el-form-item label="供应类别">
            <el-select v-model="filterForm.category" clearable placeholder="全部" class="supplier-evaluate__select">
              <el-option v-for="c in categoryOptions" :key="c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleLoad">加载评价</el-button>
            <el-button type="primary" plain @click="openEvaluateDialog()">录入评价</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-table :data="displayList" stripe border>
        <el-table-column prop="supplierName" label="供应商" min-width="160" />
        <el-table-column prop="category" label="类别" width="90" />
        <el-table-column prop="deliveryScore" label="交货准时" width="100" align="center">
          <template #default="{ row }">
            <el-rate v-model="row.deliveryScore" disabled />
          </template>
        </el-table-column>
        <el-table-column prop="qualityScore" label="质量合格" width="100" align="center">
          <template #default="{ row }">
            <el-rate v-model="row.qualityScore" disabled />
          </template>
        </el-table-column>
        <el-table-column prop="priceScore" label="价格竞争力" width="110" align="center">
          <template #default="{ row }">
            <el-rate v-model="row.priceScore" disabled />
          </template>
        </el-table-column>
        <el-table-column prop="totalScore" label="综合得分" width="100" align="right">
          <template #default="{ row }">
            <span :class="scoreClass(row.totalScore)">{{ row.totalScore.toFixed(1) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="grade" label="等级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="gradeTag(row.grade)" size="small">{{ row.grade }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="poCount" label="本季采购单" width="110" align="right" />
        <el-table-column prop="defectRate" label="不良率" width="90" align="right">
          <template #default="{ row }">{{ row.defectRate }}%</template>
        </el-table-column>
        <el-table-column prop="remark" label="评语" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEvaluateDialog(row)">调整</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-dialog v-model="dialogVisible" title="供货评价录入" width="520px" destroy-on-close>
        <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
          <el-form-item label="供应商" prop="supplierName">
            <el-select v-model="form.supplierName" class="supplier-evaluate__full">
              <el-option v-for="s in supplierNames" :key="s" :label="s" :value="s" />
            </el-select>
          </el-form-item>
          <el-form-item label="交货准时" prop="deliveryScore">
            <el-rate v-model="form.deliveryScore" />
          </el-form-item>
          <el-form-item label="质量合格" prop="qualityScore">
            <el-rate v-model="form.qualityScore" />
          </el-form-item>
          <el-form-item label="价格竞争力" prop="priceScore">
            <el-rate v-model="form.priceScore" />
          </el-form-item>
          <el-form-item label="评语">
            <el-input v-model="form.remark" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSave">提交评价</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

defineOptions({ name: 'SupplierEvaluate' })

interface EvaluateRow {
  id: number
  supplierName: string
  category: string
  deliveryScore: number
  qualityScore: number
  priceScore: number
  totalScore: number
  grade: string
  poCount: number
  defectRate: number
  remark: string
}

const categoryOptions = ['覆铜板', '化学品', '油墨', '铜箔', '五金配件']
const supplierNames = [
  '华南覆铜板有限公司',
  '精工化学材料（苏州）',
  '日研感光材料贸易',
  '江铜电解铜箔事业部',
]

const filterForm = reactive({ period: '2026-Q1', category: '' })

const evaluateList = ref<EvaluateRow[]>([
  { id: 1, supplierName: '华南覆铜板有限公司', category: '覆铜板', deliveryScore: 5, qualityScore: 4, priceScore: 4, totalScore: 4.3, grade: 'A', poCount: 28, defectRate: 0.2, remark: '交货稳定，覆铜板批次一致性好' },
  { id: 2, supplierName: '精工化学材料（苏州）', category: '化学品', deliveryScore: 4, qualityScore: 5, priceScore: 3, totalScore: 4.0, grade: 'A', poCount: 15, defectRate: 0.1, remark: '质量优异，价格略高' },
  { id: 3, supplierName: '日研感光材料贸易', category: '油墨', deliveryScore: 3, qualityScore: 4, priceScore: 3, totalScore: 3.3, grade: 'B', poCount: 8, defectRate: 0.8, remark: '试合作阶段，交期偶有延误' },
  { id: 4, supplierName: '江铜电解铜箔事业部', category: '铜箔', deliveryScore: 5, qualityScore: 5, priceScore: 4, totalScore: 4.7, grade: 'A', poCount: 22, defectRate: 0.05, remark: '核心供应商，优先排产' },
])

const dialogVisible = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  supplierName: '',
  deliveryScore: 4,
  qualityScore: 4,
  priceScore: 4,
  remark: '',
})

const rules: FormRules = {
  supplierName: [{ required: true, message: '请选择供应商', trigger: 'change' }],
}

const displayList = computed(() => {
  if (!filterForm.category) return evaluateList.value
  return evaluateList.value.filter((r) => r.category === filterForm.category)
})

function calcGrade(score: number): string {
  if (score >= 4.5) return 'A'
  if (score >= 3.5) return 'B'
  if (score >= 2.5) return 'C'
  return 'D'
}

function scoreClass(score: number): string {
  if (score >= 4.5) return 'supplier-evaluate__score--high'
  if (score >= 3.5) return 'supplier-evaluate__score--mid'
  return 'supplier-evaluate__score--low'
}

function gradeTag(grade: string): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    A: 'success',
    B: 'warning',
    C: 'info',
    D: 'danger',
  }
  return map[grade] ?? 'info'
}

function handleLoad() {
  ElMessage.success(`已加载 ${filterForm.period} 评价，共 ${displayList.value.length} 条`)
}

function openEvaluateDialog(row?: EvaluateRow) {
  editId.value = row?.id ?? null
  if (row) {
    Object.assign(form, {
      supplierName: row.supplierName,
      deliveryScore: row.deliveryScore,
      qualityScore: row.qualityScore,
      priceScore: row.priceScore,
      remark: row.remark,
    })
  } else {
    Object.assign(form, {
      supplierName: '',
      deliveryScore: 4,
      qualityScore: 4,
      priceScore: 4,
      remark: '',
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
  const total = (form.deliveryScore + form.qualityScore + form.priceScore) / 3
  const grade = calcGrade(total)
  if (editId.value) {
    const row = evaluateList.value.find((r) => r.id === editId.value)
    if (row) {
      Object.assign(row, {
        deliveryScore: form.deliveryScore,
        qualityScore: form.qualityScore,
        priceScore: form.priceScore,
        totalScore: total,
        grade,
        remark: form.remark,
      })
    }
  } else {
    evaluateList.value.push({
      id: Date.now(),
      supplierName: form.supplierName,
      category: '—',
      deliveryScore: form.deliveryScore,
      qualityScore: form.qualityScore,
      priceScore: form.priceScore,
      totalScore: total,
      grade,
      poCount: 0,
      defectRate: 0,
      remark: form.remark,
    })
  }
  dialogVisible.value = false
  ElMessage.success('评价已保存')
}
</script>

<style scoped lang="scss">
.supplier-evaluate {
  &__filter {
    margin-bottom: 16px;
  }

  &__select {
    width: 140px;
  }

  &__full {
    width: 100%;
  }

  &__score--high {
    color: #67c23a;
    font-weight: 600;
  }

  &__score--mid {
    color: #e6a23c;
    font-weight: 600;
  }

  &__score--low {
    color: #f56c6c;
    font-weight: 600;
  }
}
</style>
