<template>
  <div class="home-view">
    <div class="page-container">
      <el-row :gutter="16" class="home-view__stats">
        <el-col
          v-for="item in statCards"
          :key="item.key"
          :xs="24"
          :sm="12"
          :md="6"
        >
          <el-card shadow="hover" class="home-view__stat-card">
            <div class="home-view__stat-label">{{ item.label }}</div>
            <div class="home-view__stat-value">{{ item.value }}</div>
            <div class="home-view__stat-trend" :class="`home-view__stat-trend--${item.trend}`">
              {{ item.trendText }}
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-card shadow="never" class="home-view__recent">
        <template #header>
          <span>最近查询记录</span>
        </template>
        <el-table :data="recentQueries" stripe>
          <el-table-column prop="time" label="时间" width="170" />
          <el-table-column prop="keyword" label="查询条件" min-width="200" />
          <el-table-column prop="factory" label="工厂" width="120" />
          <el-table-column prop="resultCount" label="结果条数" width="100" align="right" />
          <el-table-column prop="operator" label="操作人" width="100" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

defineOptions({ name: 'HomeView' })

interface StatCard {
  key: string
  label: string
  value: string
  trend: 'up' | 'down' | 'flat'
  trendText: string
}

interface RecentQuery {
  time: string
  keyword: string
  factory: string
  resultCount: number
  operator: string
}

const statCards = reactive<StatCard[]>([
  { key: 'workorder', label: '进行中工单', value: '32', trend: 'up', trendText: '今日新增 6 单' },
  { key: 'equipment', label: '设备故障', value: '2', trend: 'down', trendText: '较昨日 -1 台' },
  { key: 'supplier', label: '合作供应商', value: '48', trend: 'flat', trendText: '试合作 3 家' },
  { key: 'alert', label: '库存预警', value: '7', trend: 'down', trendText: '较昨日 -2 条' },
])

const recentQueries = reactive<RecentQuery[]>([
  { time: '2026-05-21 14:32', keyword: 'FR-4 / 1.6MM 覆铜板', factory: '一厂', resultCount: 12, operator: '张三' },
  { time: '2026-05-21 11:08', keyword: '阻焊油墨 绿色', factory: '二厂', resultCount: 5, operator: '李四' },
  { time: '2026-05-20 16:45', keyword: '铜箔 35um', factory: '一厂', resultCount: 28, operator: '王五' },
  { time: '2026-05-20 09:20', keyword: '2025年各月领用统计', factory: '全公司', resultCount: 12, operator: '张三' },
  { time: '2026-05-19 15:10', keyword: '干膜 感光型', factory: '三厂', resultCount: 8, operator: '赵六' },
])
</script>

<style scoped lang="scss">
.home-view {
  &__stats {
    margin-bottom: 16px;
  }

  &__stat-card {
    margin-bottom: 16px;
  }

  &__stat-label {
    font-size: 14px;
    color: #909399;
    margin-bottom: 8px;
  }

  &__stat-value {
    font-size: 28px;
    font-weight: 600;
    color: #303133;
    line-height: 1.2;
  }

  &__stat-trend {
    margin-top: 8px;
    font-size: 12px;

    &--up {
      color: #67c23a;
    }

    &--down {
      color: #e6a23c;
    }

    &--flat {
      color: #909399;
    }
  }

  &__recent {
    margin-top: 0;
  }
}
</style>
