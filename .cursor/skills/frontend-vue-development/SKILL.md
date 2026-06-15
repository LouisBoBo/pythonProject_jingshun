---
name: frontend-vue-development
description: |
  Vue 3 + TypeScript + Element Plus + Tailwind CSS 前端开发通用技能，提供企业级中后台应用的标准工程规范与最佳实践。
  **触发场景**：使用 Vue 3 技术栈开发页面、组件、弹窗、表单、列表、路由、Store、Composable、API 调用等前端任务。
  **不触发**：纯后端、纯文档、非 Vue 技术栈（React/Svelte）任务。
---

# 前端开发规范（Vue 3 + TypeScript + Element Plus + Tailwind）

本 skill 为 Vue 3 企业级中后台应用提供通用开发规范。结合了 Vue 官方风格指南、TypeScript 严格模式、Element Plus / Tailwind 最佳实践。

---

## 0. 核心原则

1. **类型安全**：全量 TypeScript，禁用 `any`，所有 props / emits / state / API 参数/响应必须有类型
2. **UI 组件**：优先使用 UI 组件库（Element Plus / Ant Design Vue 等），不要重复造轮子
3. **样式方案**：优先使用原子化 CSS（Tailwind），避免手写大量 `<style>`
4. **API 调用**：优先使用工具（如 OpenAPI Generator / 项目自带生成命令）生成类型安全的接口代码，不手写 axios 请求
5. **响应式语法**：团队内选定一种写法（`<script setup>` 或 `defineComponent + setup`）后**保持一致**，不要混用
6. **组件职责单一**：一个组件只做一件事，超过 300 行应拆分
7. **数据向下、事件向上**：父子通信严格遵循 props down / emit up

---

## 1. 路由与文件结构

### 原则：路由 path 与视图目录一一对应

| 路由 Path | 视图文件 |
|----------|---------|
| `/user/list` | `views/user/list/index.vue` |
| `/user/detail/:id` | `views/user/detail/index.vue` |
| `/order/create` | `views/order/create/index.vue` |
| `/order/edit/:id` | `views/order/edit/index.vue` |

### 页面目录内部结构

```
views/业务模块/子模块/
├── index.vue            # 主页面
├── components/          # 该页面私有的子组件
├── composables/         # 该页面相关的业务逻辑 hook（可选）
├── store/               # 该页面级 Store（可选，跨组件共享时才用）
└── types.ts             # 该页面的局部类型定义（可选）
```

### 通用规则

- ✅ 文件夹/文件名与路由 path 保持一致（小写、kebab-case）
- ✅ 私有组件放对应页面的 `components/`，不要放全局 `components/`
- ✅ **全局组件**放在 `src/components/`（多页面复用）
- ❌ 不允许路由定义重复
- ❌ 不允许文件名随意（如 `MyTest.vue`、`temp.vue`）

---

## 2. 页面开发模板

### 推荐模板：Options-style setup（结构清晰，适合企业团队）

```vue
<template>
  <div class="page-container">
    <el-card>
      <!-- 页面内容 -->
    </el-card>
  </div>
</template>

<script lang="ts">
import { defineComponent, reactive, toRefs, onMounted } from 'vue';
import { userApi } from '@/apiService/user';
import type { UserListItem, QueryUserDto } from '@/apiService/user';

export default defineComponent({
  name: 'UserList',  // ✅ 必须定义 name（devtools + keep-alive 需要）
  setup() {
    // ① 响应式数据统一放在 _data
    const _data = reactive({
      query: { page: 1, pageSize: 10, keyword: '' } as QueryUserDto,
      list: [] as UserListItem[],
      total: 0,
      loading: false,
    });

    // ② 私有方法放在 _inner
    const _inner = {
      async fetchList() {
        _data.loading = true;
        try {
          const res = await userApi.getList(_data.query);
          _data.list = res.items;
          _data.total = res.total;
        } finally {
          _data.loading = false;
        }
      },
    };

    // ③ 对外方法放在 _methods，统一 handle 前缀 + JSDoc
    const _methods = {
      /** 搜索 */
      handleSearch() {
        _data.query.page = 1;
        _inner.fetchList();
      },
      /** 翻页 */
      handlePageChange(page: number) {
        _data.query.page = page;
        _inner.fetchList();
      },
    };

    onMounted(() => {
      _inner.fetchList();
    });

    return {
      ...toRefs(_data),
      ..._methods,
    };
  },
});
</script>
```

### 替代模板：`<script setup>`（代码更简洁，适合小型项目）

```vue
<script setup lang="ts">
import { reactive, onMounted } from 'vue';

defineOptions({ name: 'UserList' });  // 显式定义 name

const state = reactive({
  list: [] as UserListItem[],
  loading: false,
});

const fetchList = async () => { /* ... */ };

const handleSearch = () => { /* ... */ };

onMounted(fetchList);
</script>
```

> **重要**：团队内统一一种写法，**不要混用**。本文后续示例以 Options-style 为主。

### 页面开发规范

| 规则 | 说明 |
|------|------|
| 必须定义 `name` | devtools 定位、`keep-alive` include/exclude |
| 响应式数据集中管理 | 用 `reactive` 而非散落的 `ref`（便于心智管理） |
| 异步操作必须有 `loading` | 防止用户重复提交 |
| API 调用放 `_inner`（Options-style） | 避免"按钮处理函数里写一堆逻辑" |
| 对外方法 `handle` 前缀 + JSDoc | 事件处理语义明确 |
| `try/finally` 管理 loading | 保证异常时也能关闭 loading |

---

## 3. 组件封装规范

### 标准可复用组件模板

```vue
<template>
  <el-select
    v-bind="$attrs"
    :model-value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    @update:model-value="handleChange"
  >
    <el-option
      v-for="item in options"
      :key="item.value"
      :label="item.label"
      :value="item.value"
    />
  </el-select>
</template>

<script lang="ts">
import { defineComponent, type PropType } from 'vue';

interface Option {
  label: string;
  value: string | number;
}

export default defineComponent({
  name: 'EnumSelect',
  // v-bind="$attrs" 会带入未声明 props，禁用自动绑定避免重复绑到根元素
  inheritAttrs: false,
  props: {
    modelValue: {
      type: [String, Number] as PropType<string | number>,
      default: '',
    },
    options: {
      type: Array as PropType<Option[]>,
      required: true,
    },
    placeholder: {
      type: String,
      default: '请选择',
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  emits: {
    // 带校验的 emits 定义，获得完整类型提示
    'update:modelValue': (val: string | number) => true,
    change: (val: string | number) => true,
  },
  setup(_props, { emit }) {
    const handleChange = (val: string | number) => {
      emit('update:modelValue', val);
      emit('change', val);
    };
    return { handleChange };
  },
});
</script>
```

### 组件封装强约束

| 规则 | 说明 |
|------|------|
| 必须定义 `name` | devtools、递归组件需要 |
| 复杂 props 类型用 `PropType<T>` | `Object as PropType<XxxType>`、`Array as PropType<T[]>` |
| 每个 props 必须设置 `default` 或 `required: true` | 避免 undefined 错误 |
| 使用 `v-bind="$attrs"` 透传未声明属性 | 增强组件扩展性，必须配合 `inheritAttrs: false` |
| 事件统一用对象形式 `emits: {...}` | 获得运行时校验 + 类型提示 |
| 标准事件命名 | `update:modelValue`（v-model）、`change`、`update:visible` |
| 双向绑定用 `v-model` | 优先 `modelValue` / `update:modelValue`，多个绑定用 `v-model:xxx` |

### 组件 Props vs 全局状态的取舍

| 场景 | 方案 |
|------|------|
| 父子传值（1-2 层） | `props` + `emit` |
| 跨 3+ 层 | 考虑 `provide/inject` |
| 跨路由/全局共享 | Pinia Store |

---

## 4. 新增/编辑场景：弹窗优先原则

### 决策树

```
简单的新增/编辑（字段 < 20 个，无复杂依赖）
  → 弹窗组件 (XxxEditDialog.vue)

复杂场景（多步骤表单、富文本、大量附件、流程图编辑）
  → 独立全屏路由页面
```

### 标准弹窗模板

```vue
<template>
  <el-dialog
    v-model="dialogVisible"
    :title="isEdit ? '编辑' : '新建'"
    width="800px"
    :close-on-click-modal="false"
    :before-close="handleBeforeClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
    >
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入名称" />
      </el-form-item>
      <!-- 其他字段 -->
    </el-form>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts">
import { defineComponent, reactive, ref, watch, computed, toRefs } from 'vue';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { userApi } from '@/apiService/user';

export default defineComponent({
  name: 'UserEditDialog',
  props: {
    visible: { type: Boolean, default: false },
    id: { type: Number, default: undefined },  // 有 id 为编辑模式
  },
  emits: {
    'update:visible': (val: boolean) => true,
    success: () => true,
  },
  setup(props, { emit }) {
    const formRef = ref<FormInstance>();

    const _data = reactive({
      dialogVisible: false,
      saving: false,
      form: { name: '', email: '' },
    });

    const isEdit = computed(() => !!props.id);

    const rules: FormRules = {
      name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
      email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
    };

    // 监听 visible 变化，初始化表单
    watch(() => props.visible, async (val) => {
      _data.dialogVisible = val;
      if (!val) return;
      if (isEdit.value) {
        const detail = await userApi.getDetail({ id: props.id! });
        Object.assign(_data.form, detail);
      } else {
        _data.form = { name: '', email: '' };
      }
    });

    const _methods = {
      /** 关闭前确认（有变更时） */
      async handleBeforeClose(done: () => void) {
        try {
          await ElMessageBox.confirm('确定关闭？未保存的内容将丢失', '提示');
          done();
        } catch { /* 取消关闭 */ }
      },
      /** 取消 */
      handleCancel() {
        emit('update:visible', false);
      },
      /** 保存 */
      async handleSave() {
        try {
          await formRef.value?.validate();
        } catch { return; }

        _data.saving = true;
        try {
          if (isEdit.value) {
            await userApi.update({ id: props.id!, ..._data.form });
          } else {
            await userApi.create(_data.form);
          }
          ElMessage.success('保存成功');
          emit('success');
          emit('update:visible', false);
        } finally {
          _data.saving = false;
        }
      },
    };

    return { formRef, isEdit, rules, ...toRefs(_data), ..._methods };
  },
});
</script>
```

### 列表页调用弹窗

```vue
<template>
  <div class="page-container">
    <el-button type="primary" @click="handleCreate">新建</el-button>
    <el-table :data="list">
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <UserEditDialog
      v-model:visible="editVisible"
      :id="editId"
      @success="fetchList"
    />
  </div>
</template>
```

---

## 5. API 调用规范

### 原则：自动生成 > 手写

| 方案 | 推荐度 |
|------|-------|
| 根据后端 OpenAPI/Swagger 生成 API + 类型 | ⭐⭐⭐⭐⭐ |
| 封装统一的 axios 实例 + 手写接口 | ⭐⭐⭐ |
| 各处散写 `axios.get(...)` | ❌ |

### 自动生成的优点

- ✅ 类型安全（请求参数、响应数据有完整类型）
- ✅ 与后端同步（后端变更后重跑生成即可）
- ✅ 减少手写错误（URL、HTTP method 不会写错）

### axios 统一封装最佳实践

```typescript
// src/utils/request.ts
import axios, { type AxiosRequestConfig } from 'axios';
import { ElMessage } from 'element-plus';

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
});

// 请求拦截器：自动加 token
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (res) => {
    const { code, message, data } = res.data;
    if (code !== 200) {
      ElMessage.error(message || '请求失败');
      return Promise.reject(res.data);
    }
    return data;
  },
  (err) => {
    if (err.response?.status === 401) {
      // 跳登录
    }
    ElMessage.error(err.response?.data?.message || err.message);
    return Promise.reject(err);
  },
);

export default request;
```

---

## 6. 样式规范

### 优先级（从高到低）

1. **Tailwind 原子化类名**（首选）
2. **UI 库内置样式/主题变量**
3. **组件 `<style scoped>`**（少量独立样式）
4. **全局样式文件**（跨页面通用样式）

### 正确示例

```vue
<template>
  <!-- ✅ 优先 Tailwind -->
  <div class="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm">
    <h2 class="text-lg font-semibold text-gray-900">标题</h2>
    <el-button type="primary" class="ml-auto">操作</el-button>
  </div>
</template>
```

### 样式禁止项

- ❌ 大量手写 `<style>` 自定义 CSS（首选 Tailwind）
- ❌ 使用 `!important` 覆盖 UI 库（应该用 CSS 变量或主题配置）
- ❌ 在组件内定义全局样式（应放全局样式文件）
- ❌ 内联 `style="..."` 写复杂样式

### 项目级全局样式

约定一个根容器 class（如 `page-container`）在全局样式中定义统一内边距、背景色、最小高度。页面根元素统一使用：

```vue
<template>
  <div class="page-container">
    <!-- 内容 -->
  </div>
</template>
```

---

## 7. Store 规范（Pinia）

### 何时使用 Store

- ✅ 用户信息、权限、Token 等全局状态
- ✅ 跨路由共享的状态（如多步骤表单的中间数据）
- ✅ 复杂页面的跨组件状态
- ❌ 单一页面的局部状态（用 `reactive` 即可）

### 标准 Store 模板（Composition API 风格）

```typescript
// src/store/modules/user.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authApi } from '@/apiService/auth';
import type { UserInfo } from '@/apiService/auth';

export const useUserStore = defineStore('user', () => {
  // ① State
  const token = ref<string>(localStorage.getItem('token') || '');
  const userInfo = ref<UserInfo | null>(null);

  // ② Getters
  const isLoggedIn = computed(() => !!token.value);
  const nickname = computed(() => userInfo.value?.nickname ?? '未登录');

  // ③ Actions
  async function login(params: { username: string; password: string }) {
    const res = await authApi.login(params);
    token.value = res.token;
    userInfo.value = res.user;
    localStorage.setItem('token', res.token);
  }

  function logout() {
    token.value = '';
    userInfo.value = null;
    localStorage.removeItem('token');
  }

  async function fetchUserInfo() {
    userInfo.value = await authApi.getUserInfo();
  }

  return { token, userInfo, isLoggedIn, nickname, login, logout, fetchUserInfo };
});
```

### Store 使用原则

- ✅ 每个 Store 职责单一（`user` / `permission` / `app`）
- ✅ Actions 处理业务逻辑（可以 async）
- ✅ Getters 是派生状态，不能有副作用
- ❌ 不要在 Store 中调用另一个 Store 的 mutation（可以读 state）
- ❌ 不要在 Store 中做 UI 操作（如 ElMessage）

---

## 8. 表单与校验规范

### 定义 rules

```typescript
import type { FormRules } from 'element-plus';

const rules: FormRules = {
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2~50 个字符', trigger: 'blur' },
  ],
  email: [
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  age: [
    {
      validator: (_rule, value, cb) => {
        if (value > 0) cb();
        else cb(new Error('年龄必须大于 0'));
      },
      trigger: 'blur',
    },
  ],
};
```

### 提交前必须 validate

```typescript
async handleSubmit() {
  try {
    await formRef.value?.validate();  // ✅ 校验通过才继续
  } catch {
    return;  // 校验失败直接返回
  }
  // 业务逻辑...
}
```

### 表单重置

```typescript
// 重置校验状态 + 数据
formRef.value?.resetFields();
```

---

## 9. 消息反馈规范

| 场景 | 方式 |
|------|------|
| 成功提示 | `ElMessage.success('保存成功')` |
| 失败提示 | `ElMessage.error('保存失败')` |
| 警告 | `ElMessage.warning('xxx')` |
| 删除/危险操作确认 | `ElMessageBox.confirm(...)` |
| 需要用户输入 | `ElMessageBox.prompt(...)` |
| 加载中（长时操作） | `ElLoading.service({ lock: true })` |

### 删除确认示例

```typescript
async handleDelete(row: Item) {
  try {
    await ElMessageBox.confirm(
      `确定删除 ${row.name}？删除后不可恢复`,
      '提示',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    );
  } catch { return; }

  await userApi.delete({ id: row.id });
  ElMessage.success('删除成功');
  fetchList();
}
```

---

## 10. 性能与最佳实践

### 列表渲染

- ✅ `:key` 必须稳定唯一（用 `id`，不用 `index`）
- ✅ 大列表（>500 条）使用虚拟滚动（`el-table-v2` / `vue-virtual-scroller`）
- ✅ 条件渲染用 `v-if`（彻底销毁），切换显示用 `v-show`（仅 CSS）
- ❌ `v-for` 与 `v-if` 不要在同一元素（Vue 3 中 `v-if` 优先级高于 `v-for`）

### 防抖/节流

```typescript
import { useDebounceFn, useThrottleFn } from '@vueuse/core';

// 搜索输入防抖
const handleSearchInput = useDebounceFn((val: string) => {
  fetchList({ keyword: val });
}, 300);

// 滚动节流
const handleScroll = useThrottleFn(() => { /* ... */ }, 200);
```

### 异步组件与懒加载

```typescript
// 路由懒加载
const routes = [
  {
    path: '/user/list',
    component: () => import('@/views/user/list/index.vue'),
  },
];

// 异步大组件
import { defineAsyncComponent } from 'vue';
const HeavyEditor = defineAsyncComponent(() => import('./HeavyEditor.vue'));
```

### 图片与静态资源

- ✅ 业务图片放 `src/assets/`（Vite 会 hash 处理，有缓存）
- ✅ 图片用 `import logo from '@/assets/logo.svg'`
- ✅ 只有不需处理的固定文件（如 favicon、robots.txt）放 `public/`
- ✅ 大图片考虑 WebP / 懒加载（`v-lazy`）

### 内存泄漏防护

```typescript
// ✅ 监听器在 unmount 时清理
onMounted(() => {
  window.addEventListener('resize', handleResize);
});
onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});

// ✅ 定时器清理
const timer = setInterval(fn, 1000);
onUnmounted(() => clearInterval(timer));
```

---

## 11. TypeScript 规范

### 基础要求

- ✅ `tsconfig.json` 开启 `strict: true`
- ✅ 所有函数参数和返回值有类型（编译器可推导的可省略）
- ✅ 共享类型定义到 `src/types/` 或 `types.ts`
- ❌ 禁用 `any`，必要时用 `unknown` + 类型守卫

### 常用技巧

```typescript
// 工具类型
type UserUpdate = Partial<User>;       // 所有字段可选
type UserKeys = keyof User;            // 字段名联合类型
type UserWithId = Pick<User, 'id'>;    // 选字段
type UserNoId = Omit<User, 'id'>;      // 排除字段

// 联合类型 + 字面量
type Status = 'pending' | 'success' | 'error';

// 泛型组件 props
interface Props<T> {
  items: T[];
  renderItem: (item: T) => string;
}

// as const 保证字面量
const STATUSES = ['pending', 'success'] as const;
type Status = typeof STATUSES[number];  // 'pending' | 'success'
```

---

## 12. 国际化（i18n）规范（可选）

```vue
<template>
  <div>
    <h2>{{ $t('user.list.title') }}</h2>
    <el-button>{{ $t('common.submit') }}</el-button>
  </div>
</template>

<script lang="ts">
import { useI18n } from 'vue-i18n';

export default defineComponent({
  setup() {
    const { t } = useI18n();
    const message = t('user.list.greeting', { name: 'Alice' });
    return { message };
  },
});
</script>
```

### 原则

- ✅ 所有面向用户的文字走 i18n
- ✅ key 用层级结构（`模块.子模块.词条`）
- ❌ 不要直接写中文/英文在 template 中

---

## 13. 完整 Checklist（新建页面/组件时逐项检查）

### 新建页面

- [ ] 文件路径与路由 path 对应
- [ ] 根容器使用统一的 `page-container` 类
- [ ] 组件定义 `name` 属性
- [ ] 响应式数据集中管理（reactive）
- [ ] API 调用统一走生成的 API 或统一封装的 axios
- [ ] 样式优先使用 Tailwind
- [ ] 新增/编辑优先用弹窗
- [ ] 异步操作有 loading
- [ ] 提交前调用 `formRef.validate()`
- [ ] 操作反馈用 `ElMessage` / `ElMessageBox`
- [ ] 类型安全（不使用 `any`）

### 新建组件

- [ ] 命名 PascalCase（`UserCard.vue`）
- [ ] 定义 `name` 属性
- [ ] props 使用 `PropType<T>` + `required`/`default`
- [ ] emits 使用对象形式声明（含类型）
- [ ] 使用 `v-bind="$attrs"` + `inheritAttrs: false` 透传
- [ ] 标准事件命名（`update:modelValue`）
- [ ] 超过 300 行考虑拆分
- [ ] 私有组件放对应页面 `components/`，通用组件放 `src/components/`

---

## 14. 反例速查

| 错误写法 | 正确写法 |
|---------|---------|
| 同文件混用 `<script setup>` 和 `defineComponent` | 团队选定一种 |
| 页面/组件无 `name` | 必须定义 `name` |
| 散落的 `const x = ref(...)` | 集中放 `reactive({...})` |
| 方法无前缀：`submit()` | `handleSubmit()` 事件处理语义清晰 |
| 手写 `axios.get(...)` 散落各处 | 统一封装 + 自动生成 |
| `<style>` 大量自定义 CSS | 使用 Tailwind |
| `:key="index"` | `:key="row.id"` |
| 跳过 `validate()` 直接提交 | `await formRef.value?.validate()` |
| 独立路由页做简单新增/编辑 | 改用弹窗组件 |
| `props: ['modelValue']` | `{ modelValue: { type: String, default: '' } }` |
| `v-for` + `v-if` 同元素 | 外层包一层 `template` 做 `v-if` |
| `any` 类型 | 具体类型 / `unknown` + 类型守卫 |
| `localStorage.getItem` 散落各处 | 封装到 Store 或 utils |
| 直接在组件内监听全局事件不清理 | `onMounted` 注册 + `onUnmounted` 清理 |
| 大组件一次性加载 | `defineAsyncComponent` 懒加载 |
| 复杂业务组件超过 500 行 | 按职责拆分成多个子组件 |

---

## 15. 推荐的工具生态

| 类别 | 推荐 |
|------|------|
| 构建工具 | Vite |
| 状态管理 | Pinia |
| 路由 | Vue Router 4 |
| HTTP | axios + 拦截器封装 |
| UI 库 | Element Plus / Ant Design Vue |
| 样式 | Tailwind CSS + 原子化 |
| 工具函数 | VueUse (`@vueuse/core`) |
| 日期 | dayjs |
| 表单 | Element Plus Form / VeeValidate |
| 图标 | Element Plus Icons / Iconify |
| API 生成 | openapi-typescript-codegen / 自建脚本 |
| Lint | ESLint + Prettier + `eslint-plugin-vue` |
| 测试 | Vitest + Vue Test Utils |
