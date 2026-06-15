<template>
  <div class="work-order-stats">
    <div class="page-container">
      <el-card shadow="never" class="work-order-stats__filter">
        <el-form :model="filterForm" inline label-width="80px">
          <el-form-item label="统计月份">
            <el-date-picker
              v-model="filterForm.month"
              type="month"
              value-format="YYYY-MM"
              placeholder="选择月份"
            />
          </el-form-item>
          <el-form-item label="工厂">
            <el-select v-model="filterForm.factory" clearable placeholder="全部" class="work-order-stats__select">
              <el-option v-for="f in ['一厂', '二厂', '三厂']" :key="f" :label="f" :value="f" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleRefresh">刷新统计</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-row :gutter="16" class="work-order-stats__cards">
        <el-col v-for="item in overviewCards" :key="item.key" :span="6">
          <el-card shadow="hover">
            <div class="work-order-stats__card-label">{{ item.label }}</div>
            <div class="work-order-stats__card-value">{{ item.value }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>按工单类型分布</template>
            <el-table :data="typeStats" stripe size="small">
              <el-table-column prop="type" label="类型" />
              <el-table-column prop="count" label="数量" width="80" align="right" />
              <el-table-column prop="rate" label="占比" width="80" align="right">
                <template #default="{ row }">{{ row.rate }}%</template>
              </el-table-column>
              <el-table-column label="占比" min-width="120">
                <template #default="{ row }">
                  <el-progress :percentage="row.rate" :stroke-width="10" />
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never">
            <template #header>按工厂完工率</template>
            <el-table :data="factoryStats" stripe size="small">
              <el-table-column prop="factory" label="工厂" width="80" />
              <el-table-column prop="total" label="工单总数" width="90" align="right" />
              <el-table-column prop="completed" label="已完工" width="90" align="right" />
              <el-table-column prop="completeRate" label="完工率" width="90" align="right">
                <template #default="{ row }">{{ row.completeRate }}%</template>
              </el-table-column>
              <el-table-column prop="avgHours" label="平均耗时(h)" width="110" align="right" />
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="work-order-stats__overdue">
        <template #header>
          <span>超期未完工工单</span>
          <el-tag type="danger" size="small" class="work-order-stats__badge">{{ overdueList.length }} 条</el-tag>
        </template>
        <el-table :data="overdueList" stripe border>
          <el-table-column prop="orderNo" label="工单号" width="140" />
          <el-table-column prop="title" label="标题" min-width="180" />
          <el-table-column prop="assignee" label="负责人" width="90" />
          <el-table-column prop="deadline" label="要求完成" width="120" />
          <el-table-column prop="overdueDays" label="超期天数" width="100" align="right">
            <template #default="{ row }">
              <span class="work-order-stats__overdue-days">{{ row.overdueDays }} 天</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'

defineOptions({ name: 'WorkOrderStats' })

const filterForm = reactive({
  month: '2026-05',
  factory: '',
})

const overviewCards = reactive([
  { key: 'total', label: '本月工单总数', value: 186 },
  { key: 'done', label: '已完工', value: 142 },
  { key: 'processing', label: '进行中', value: 32 },
  { key: 'overdue', label: '超期未完工', value: 5 },
])

const typeStats = reactive([
  { type: '领料工单', count: 78, rate: 41.9 },
  { type: '补料工单', count: 52, rate: 28.0 },
  { type: '盘点工单', count: 34, rate: 18.3 },
  { type: '退料工单', count: 22, rate: 11.8 },
])

const factoryStats = reactive([
  { factory: '一厂', total: 72, completed: 58, completeRate: 80.6, avgHours: 18.2 },
  { factory: '二厂', total: 58, completed: 45, completeRate: 77.6, avgHours: 21.5 },
  { factory: '三厂', total: 56, completed: 39, completeRate: 69.6, avgHours: 24.8 },
])

const overdueList = reactive([
  { orderNo: 'WO-202605002', title: '二厂阻焊油墨补库', assignee: '李四', deadline: '2026-05-18', overdueDays: 3 },
  { orderNo: 'WO-202604091', title: '一厂干膜紧急领用', assignee: '张三', deadline: '2026-05-17', overdueDays: 4 },
  { orderNo: 'WO-202604075', title: '三厂显影液补料', assignee: '孙七', deadline: '2026-05-16', overdueDays: 5 },
])

function handleRefresh() {
  ElMessage.success(`已刷新 ${filterForm.month} 工单统计数据`)
}
</script>

<style scoped lang="scss">
.work-order-stats {
  &__filter {
    margin-bottom: 16px;
  }

  &__select {
    width: 120px;
  }

  &__cards {
    margin-bottom: 16px;
  }

  &__card-label {
    font-size: 14px;
    color: #909399;
  }

  &__card-value {
    margin-top: 8px;
    font-size: 26px;
    font-weight: 600;
    color: #303133;
  }

  &__overdue {
    margin-top: 16px;
  }

  &__badge {
    margin-left: 8px;
  }

  &__overdue-days {
    color: #f56c6c;
    font-weight: 500;
  }
}
</style>
