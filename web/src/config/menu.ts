import type { Component } from 'vue'
import {
  DataAnalysis,
  Document,
  HomeFilled,
  List,
  Monitor,
  OfficeBuilding,
  Search,
  Setting,
  Tickets,
  Tools,
  TrendCharts,
  User,
  Van,
} from '@element-plus/icons-vue'

export interface MenuItem {
  index: string
  title: string
  icon?: Component
  /** 对应路由 path，叶子节点必填 */
  path?: string
  children?: MenuItem[]
}

/** 侧边栏菜单配置（与路由 path 对应） */
export const menuConfig: MenuItem[] = [
  {
    index: 'home',
    title: '首页',
    icon: HomeFilled,
    path: '/home',
  },
  {
    index: 'material',
    title: '物料管理',
    icon: Document,
    children: [
      {
        index: 'material-query',
        title: '物料查询',
        icon: Search,
        path: '/material/query',
      },
      {
        index: 'material-analysis',
        title: '物料分析',
        icon: DataAnalysis,
        path: '/material/analysis',
      },
    ],
  },
  {
    index: 'work-order',
    title: '工单管理',
    icon: Tickets,
    children: [
      {
        index: 'work-order-list',
        title: '工单列表',
        icon: List,
        path: '/work-order/list',
      },
      {
        index: 'work-order-stats',
        title: '工单统计',
        icon: TrendCharts,
        path: '/work-order/stats',
      },
    ],
  },
  {
    index: 'equipment',
    title: '设备管理',
    icon: Monitor,
    children: [
      {
        index: 'equipment-ledger',
        title: '设备台账',
        icon: Monitor,
        path: '/equipment/ledger',
      },
      {
        index: 'equipment-maintenance',
        title: '维保记录',
        icon: Tools,
        path: '/equipment/maintenance',
      },
    ],
  },
  {
    index: 'supplier',
    title: '供应商管理',
    icon: OfficeBuilding,
    children: [
      {
        index: 'supplier-archive',
        title: '供应商档案',
        icon: Van,
        path: '/supplier/archive',
      },
      {
        index: 'supplier-evaluate',
        title: '供货评价',
        icon: DataAnalysis,
        path: '/supplier/evaluate',
      },
    ],
  },
  {
    index: 'system',
    title: '系统设置',
    icon: Setting,
    children: [
      {
        index: 'user-mgmt',
        title: '用户管理',
        icon: User,
        path: '/system/user',
      },
    ],
  },
]
