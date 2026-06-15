<template>
  <div class="main-layout">
    <el-container class="main-layout__container">
      <el-header class="main-layout__header">
        <div class="main-layout__header-left">
          <span class="main-layout__title">{{ systemTitle }}</span>
        </div>
        <div class="main-layout__header-right">
          <el-button type="primary" link @click="handleLogout">
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-container class="main-layout__body">
        <el-aside class="main-layout__aside" width="220px">
          <el-menu
            class="main-layout__menu"
            :default-active="activeMenu"
            background-color="#ffffff"
            text-color="#303133"
            active-text-color="#409eff"
            router
          >
            <template v-for="item in menuConfig" :key="item.index">
              <el-sub-menu
                v-if="item.children?.length"
                :index="item.index"
              >
                <template #title>
                  <el-icon v-if="item.icon">
                    <component :is="item.icon" />
                  </el-icon>
                  <span>{{ item.title }}</span>
                </template>
                <el-menu-item
                  v-for="child in item.children"
                  :key="child.index"
                  :index="child.path!"
                >
                  <el-icon v-if="child.icon">
                    <component :is="child.icon" />
                  </el-icon>
                  <span>{{ child.title }}</span>
                </el-menu-item>
              </el-sub-menu>

              <el-menu-item
                v-else
                :index="item.path!"
              >
                <el-icon v-if="item.icon">
                  <component :is="item.icon" />
                </el-icon>
                <span>{{ item.title }}</span>
              </el-menu-item>
            </template>
          </el-menu>
        </el-aside>

        <el-main class="main-layout__main">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { menuConfig } from '@/config/menu'

defineOptions({ name: 'MainLayout' })

const systemTitle = '锦顺物料管理系统'

const route = useRoute()
const router = useRouter()

const activeMenu = computed(() => route.path)

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    localStorage.removeItem('token')
    ElMessage.success('已退出登录')
    await router.push('/home')
  } catch {
    /* 用户取消 */
  }
}
</script>

<style scoped lang="scss">
@use '@/styles/variables.scss' as *;

.main-layout {
  height: 100%;
  background: $color-content-bg;

  &__container {
    height: 100%;
    flex-direction: column;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: $header-height;
    padding: 0 24px;
    background: $color-header-bg;
    color: $color-header-text;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }

  &__title {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }

  &__header-right {
    :deep(.el-button.is-link) {
      color: $color-header-text;
      font-size: 14px;

      &:hover {
        color: rgba(255, 255, 255, 0.85);
      }
    }
  }

  &__body {
    flex: 1;
    overflow: hidden;
  }

  &__aside {
    background: $color-sidebar-bg;
    border-right: 1px solid $color-border;
    overflow-x: hidden;
    overflow-y: auto;
  }

  &__menu {
    border-right: none;
    height: 100%;
  }

  &__main {
    padding: 16px;
    overflow: auto;
    background: $color-content-bg;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
