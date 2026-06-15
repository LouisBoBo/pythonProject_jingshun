<template>
  <div class="material-analysis">
    <div class="page-container">
      <el-card shadow="never" class="material-analysis__filter">
        <el-form :model="filterForm" inline label-width="80px">
          <el-form-item label="统计年度">
            <el-select v-model="filterForm.year" class="material-analysis__select">
              <el-option label="2026年" value="2026" />
              <el-option label="2025年" value="2025" />
            </el-select>
          </el-form-item>
          <el-form-item label="工厂">
            <el-select
              v-model="filterForm.factory"
              clearable
              placeholder="全部"
              class="material-analysis__select"
            >
              <el-option label="一厂" value="一厂" />
              <el-option label="二厂" value="二厂" />
              <el-option label="三厂" value="三厂" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleAnalyze">统计分析</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-row :gutter="16" class="material-analysis__summary">
        <el-col :span="8">
          <el-statistic title="年度领用合计" :value="summary.totalUsage" suffix="KG" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="涉及物料大类" :value="summary.categoryCount" suffix="类" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="领用金额合计" :value="summary.totalAmount" prefix="¥" :precision="2" />
        </el-col>
      </el-row>

      <el-card shadow="never">
        <template #header>
          <span>各月领用汇总（{{ filterForm.year }}年 · {{ displayFactory }}）</span>
        </template>
        <el-table :data="monthlyData" stripe border show-summary :summary-method="getSummaries">
          <el-table-column prop="month" label="月份" width="100" />
          <el-table-column prop="usageQty" label="领用数量" width="120" align="right" />
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="amount" label="金额(元)" width="140" align="right">
            <template #default="{ row }">
              {{ row.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}
            </template>
          </el-table-column>
          <el-table-column prop="mom" label="环比" width="100" align="center">
            <template #default="{ row }">
              <el-tag
                v-if="row.mom !== null"
                :type="row.mom >= 0 ? 'success' : 'warning'"
                size="small"
              >
                {{ row.mom >= 0 ? '+' : '' }}{{ row.mom }}%
              </el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
        </el-table>
      </el-card>

      <el-card shadow="never" class="material-analysis__rank">
        <template #header>
          <span>物料大类领用 TOP5</span>
        </template>
        <el-table :data="topCategories" stripe>
          <el-table-column type="index" label="排名" width="70" />
          <el-table-column prop="category" label="物料大类" width="120" />
          <el-table-column prop="usageQty" label="领用数量" width="120" align="right" />
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="share" label="占比" width="100" align="right">
            <template #default="{ row }">
              {{ row.share }}%
            </template>
          </el-table-column>
          <el-table-column label="占比条" min-width="200">
            <template #default="{ row }">
              <el-progress :percentage="row.share" :stroke-width="14" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { TableColumnCtx } from 'element-plus'

defineOptions({ name: 'MaterialAnalysis' })

interface MonthlyRow {
  month: string
  usageQty: number
  unit: string
  amount: number
  mom: number | null
  remark: string
}

interface CategoryRank {
  category: string
  usageQty: number
  unit: string
  share: number
}

const filterForm = reactive({
  year: '2026',
  factory: '一厂',
})

const summary = reactive({
  totalUsage: 128560,
  categoryCount: 12,
  totalAmount: 3856200.5,
})

const monthlyData = ref<MonthlyRow[]>([
  { month: '1月', usageQty: 9850, unit: 'KG', amount: 285600, mom: null, remark: '春节后复工' },
  { month: '2月', usageQty: 10200, unit: 'KG', amount: 298400, mom: 3.6, remark: '' },
  { month: '3月', usageQty: 11580, unit: 'KG', amount: 342100, mom: 13.5, remark: '订单旺季' },
  { month: '4月', usageQty: 10890, unit: 'KG', amount: 318500, mom: -6.0, remark: '' },
  { month: '5月', usageQty: 11240, unit: 'KG', amount: 331200, mom: 3.2, remark: '截至5月20日' },
])

const topCategories = ref<CategoryRank[]>([
  { category: '覆铜板', usageQty: 45200, unit: 'KG', share: 35.2 },
  { category: '铜箔', usageQty: 28600, unit: 'KG', share: 22.3 },
  { category: '油墨', usageQty: 18500, unit: 'KG', share: 14.4 },
  { category: '干膜', usageQty: 15200, unit: 'KG', share: 11.8 },
  { category: '化学品', usageQty: 12800, unit: 'KG', share: 10.0 },
])

const displayFactory = computed(() => filterForm.factory || '全部工厂')

function getSummaries(param: { columns: TableColumnCtx<MonthlyRow>[]; data: MonthlyRow[] }) {
  const { columns, data } = param
  const sums: string[] = []
  columns.forEach((column, index) => {
    if (index === 0) {
      sums[index] = '合计'
      return
    }
    if (column.property === 'usageQty') {
      const total = data.reduce((acc, row) => acc + row.usageQty, 0)
      sums[index] = String(total)
      return
    }
    if (column.property === 'amount') {
      const total = data.reduce((acc, row) => acc + row.amount, 0)
      sums[index] = total.toLocaleString('zh-CN', { minimumFractionDigits: 2 })
      return
    }
    sums[index] = ''
  })
  return sums
}

function handleAnalyze() {
  ElMessage.success(`已加载 ${filterForm.year} 年 ${displayFactory.value} 模拟统计数据`)
}
</script>

<style scoped lang="scss">
.material-analysis {
  &__filter {
    margin-bottom: 16px;
  }

  &__select {
    width: 140px;
  }

  &__summary {
    margin-bottom: 16px;
    padding: 16px;
    background: #fff;
    border-radius: 4px;
  }

  &__rank {
    margin-top: 16px;
  }
}
</style>
