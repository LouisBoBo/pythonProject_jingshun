import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/home',
    children: [
      {
        path: 'home',
        name: 'Home',
        component: () => import('@/views/home/homeView.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'material/query',
        name: 'MaterialQuery',
        component: () => import('@/views/materialQuery/materialQuery.vue'),
        meta: { title: '物料查询' },
      },
      {
        path: 'material/analysis',
        name: 'MaterialAnalysis',
        component: () => import('@/views/materialAnalysis/materialAnalysis.vue'),
        meta: { title: '物料分析' },
      },
      {
        path: 'work-order/list',
        name: 'WorkOrderList',
        component: () => import('@/views/workOrder/workOrderList.vue'),
        meta: { title: '工单列表' },
      },
      {
        path: 'work-order/stats',
        name: 'WorkOrderStats',
        component: () => import('@/views/workOrder/workOrderStats.vue'),
        meta: { title: '工单统计' },
      },
      {
        path: 'equipment/ledger',
        name: 'EquipmentLedger',
        component: () => import('@/views/equipment/equipmentLedger.vue'),
        meta: { title: '设备台账' },
      },
      {
        path: 'equipment/maintenance',
        name: 'EquipmentMaintenance',
        component: () => import('@/views/equipment/maintenanceRecord.vue'),
        meta: { title: '维保记录' },
      },
      {
        path: 'supplier/archive',
        name: 'SupplierArchive',
        component: () => import('@/views/supplier/supplierArchive.vue'),
        meta: { title: '供应商档案' },
      },
      {
        path: 'supplier/evaluate',
        name: 'SupplierEvaluate',
        component: () => import('@/views/supplier/supplierEvaluate.vue'),
        meta: { title: '供货评价' },
      },
      {
        path: 'system/user',
        name: 'UserMgmt',
        component: () => import('@/views/userMgmt/userMgmt.vue'),
        meta: { title: '用户管理' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/home',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
