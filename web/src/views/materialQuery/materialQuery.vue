<template>
  <div class="material-query">
    <div class="page-container">
      <el-card shadow="never" class="material-query__search">
        <el-form :model="queryForm" inline label-width="80px">
          <el-form-item label="物料名称">
            <el-input
              v-model="queryForm.keyword"
              placeholder="原材料代码 / 描述"
              clearable
              class="material-query__input"
            />
          </el-form-item>
          <el-form-item label="工厂">
            <el-select
              v-model="queryForm.factory"
              placeholder="请选择"
              clearable
              class="material-query__select"
            >
              <el-option
                v-for="f in factoryOptions"
                :key="f"
                :label="f"
                :value="f"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="物料类别">
            <el-select
              v-model="queryForm.category"
              placeholder="请选择"
              clearable
              class="material-query__select"
            >
              <el-option
                v-for="c in categoryOptions"
                :key="c"
                :label="c"
                :value="c"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">查询</el-button>
            <el-button @click="handleReset">重置</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never" class="material-query__table">
        <template #header>
          <span>查询结果（共 {{ tableData.length }} 条）</span>
        </template>
        <el-table v-loading="loading" :data="tableData" stripe border>
          <el-table-column prop="code" label="原材料代码" width="140" />
          <el-table-column prop="description" label="原材料描述" min-width="220" show-overflow-tooltip />
          <el-table-column prop="category" label="类别" width="100" />
          <el-table-column prop="factory" label="工厂" width="90" />
          <el-table-column prop="stockQty" label="库存数量" width="110" align="right" />
          <el-table-column prop="unit" label="单位" width="70" />
          <el-table-column prop="lastInDate" label="最近入库" width="120" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

defineOptions({ name: 'MaterialQuery' })

interface MaterialRow {
  code: string
  description: string
  category: string
  factory: string
  stockQty: number
  unit: string
  lastInDate: string
}

const factoryOptions = ['一厂', '二厂', '三厂', '全公司']
const categoryOptions = ['覆铜板', '油墨', '铜箔', '干膜', '化学品']

const queryForm = reactive({
  keyword: '',
  factory: '',
  category: '',
})

const loading = ref(false)

const allMockData: MaterialRow[] = [
  { code: 'RM-2024001', description: 'FR-4 覆铜板 1.6MM/1OZ', category: '覆铜板', factory: '一厂', stockQty: 1250, unit: '张', lastInDate: '2026-05-18' },
  { code: 'RM-2024012', description: '阻焊油墨 绿色 HDI专用', category: '油墨', factory: '二厂', stockQty: 86.5, unit: 'KG', lastInDate: '2026-05-20' },
  { code: 'RM-2024033', description: '电解铜箔 35um 12um', category: '铜箔', factory: '一厂', stockQty: 3200, unit: 'KG', lastInDate: '2026-05-15' },
  { code: 'RM-2024056', description: '干膜 感光型 0.075MM', category: '干膜', factory: '三厂', stockQty: 420, unit: '卷', lastInDate: '2026-05-19' },
  { code: 'RM-2024078', description: '显影液 弱碱性', category: '化学品', factory: '二厂', stockQty: 180, unit: 'L', lastInDate: '2026-05-12' },
  { code: 'RM-2024091', description: 'FR-4 覆铜板 0.8MM/0.5OZ', category: '覆铜板', factory: '一厂', stockQty: 890, unit: '张', lastInDate: '2026-05-21' },
]

const tableData = ref<MaterialRow[]>([...allMockData])

function filterData() {
  return allMockData.filter((row) => {
    const matchKeyword =
      !queryForm.keyword ||
      row.code.includes(queryForm.keyword) ||
      row.description.includes(queryForm.keyword)
    const matchFactory = !queryForm.factory || row.factory === queryForm.factory
    const matchCategory = !queryForm.category || row.category === queryForm.category
    return matchKeyword && matchFactory && matchCategory
  })
}

async function handleSearch() {
  loading.value = true
  await new Promise((r) => setTimeout(r, 400))
  tableData.value = filterData()
  loading.value = false
  ElMessage.success(`查询完成，共 ${tableData.value.length} 条`)
}

function handleReset() {
  queryForm.keyword = ''
  queryForm.factory = ''
  queryForm.category = ''
  tableData.value = [...allMockData]
}
</script>

<style scoped lang="scss">
.material-query {
  &__search {
    margin-bottom: 16px;
  }

  &__input {
    width: 220px;
  }

  &__select {
    width: 140px;
  }

  &__table {
    margin-top: 0;
  }
}
</style>
