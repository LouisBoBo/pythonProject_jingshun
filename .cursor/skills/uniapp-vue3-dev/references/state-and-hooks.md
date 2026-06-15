# 状态管理（Pinia / globalData）& Hooks 规范

本文档覆盖 uni-app 工程中的三类"状态载体"：**Pinia**、**globalData**、**自定义 hook**。核心是**按用途选择正确的载体**。

---

## 一、三种状态载体的选择

| 载体 | 响应式 | 跨页面 | 持久化 | 典型场景 |
|---|---|---|---|---|
| 组件 `ref`/`reactive` | ✅ | ❌ | ❌ | 单页面 UI 状态 |
| 自定义 hook | ✅（内部） | ✅（逻辑复用） | ❌ | 复用的业务逻辑（请求、倒计时、表单） |
| Pinia store | ✅ | ✅ | 可选 | 全局响应式状态（用户、购物车、主题） |
| globalData | ❌ | ✅ | ❌ | 非响应式全局单例（设备信息、启动参数） |
| uni Storage | ❌ | ✅ | ✅ | 需要跨启动存活（token、设置） |

### 决策树

```
需要 UI 跟随变化吗？
├─ 否 → globalData 或 Storage
└─ 是：跨页面使用吗？
        ├─ 否 → 组件内 ref
        └─ 是：是"状态数据"还是"可复用逻辑"？
                ├─ 状态 → Pinia
                └─ 逻辑 → 自定义 hook
```

---

## 二、Pinia 规范

### 2.1 基本结构

推荐 **Setup Store**（更接近 Composition API）：

```ts
// pinia/modules/user.ts
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import * as api from '@/apiService';

export const useUserStore = defineStore('user', () => {
  // state
  const token = ref<string>('');
  const profile = ref<UserProfile | null>(null);

  // getter
  const isLogin = computed(() => !!token.value);
  const nickname = computed(() => profile.value?.nickname ?? '游客');

  // action
  async function login(payload: LoginReq) {
    const res = await api.login(payload);
    token.value = res.token;
    uni.setStorageSync('token', res.token);
    await fetchProfile();
  }

  async function fetchProfile() {
    profile.value = await api.getUserProfile();
  }

  function logout() {
    token.value = '';
    profile.value = null;
    uni.removeStorageSync('token');
  }

  return { token, profile, isLogin, nickname, login, fetchProfile, logout };
});
```

### 2.2 命名与文件

- 文件名：`pinia/modules/<业务域>.ts`
- id 与文件名一致：`defineStore('user', ...)`
- 导出名：`useXxxStore`
- 每个 store 文件聚焦一个业务域，超过 300 行考虑拆分

### 2.3 持久化

```ts
// pinia/index.ts
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);
export default pinia;

// 在 store 里启用
export const useUserStore = defineStore('user', () => { /* ... */ }, {
  persist: {
    key: 'user',
    storage: {
      getItem: (k) => uni.getStorageSync(k),
      setItem: (k, v) => uni.setStorageSync(k, v),
    },
    paths: ['token'],  // 只持久化 token
  },
});
```

**注意**：uni-app 环境的 localStorage 需要适配为 `uni.getStorageSync`。

### 2.4 反模式

- ❌ 一个巨型 `useAppStore` 塞所有全局状态
- ❌ 在 store 里调 `uni.navigateTo`（副作用应在页面/hook 层）
- ❌ store 里放大量非响应式字段（应放 globalData）
- ❌ 组件内 `const store = useUserStore()` 然后 `const token = store.token`（解构丢响应式）→ 用 `storeToRefs`

```ts
import { storeToRefs } from 'pinia';
const { token, isLogin } = storeToRefs(useUserStore());
const { login, logout } = useUserStore();  // 方法可以直接解构
```

---

## 三、globalData 规范

### 3.1 适用场景

**非响应式** 的全局单例数据：
- 启动参数（scene、渠道来源）
- 系统信息（机型、屏幕、状态栏高度）
- 应用配置（env、baseUrl）
- 跨页面中转的大对象（URL 无法传递）

### 3.2 实现

```ts
// store/globalData.ts
interface GlobalData {
  systemInfo: UniApp.GetSystemInfoResult | null;
  launchOptions: UniApp.OnLaunchOptions | null;
  tempPayloads: Record<string, unknown>;
}

const data: GlobalData = {
  systemInfo: null,
  launchOptions: null,
  tempPayloads: {},
};

export const globalData = {
  get<K extends keyof GlobalData>(key: K): GlobalData[K] {
    return data[key];
  },
  set<K extends keyof GlobalData>(key: K, value: GlobalData[K]) {
    data[key] = value;
  },
  setPayload(key: string, value: unknown) {
    data.tempPayloads[key] = value;
  },
  getPayload<T>(key: string): T | undefined {
    return data.tempPayloads[key] as T;
  },
  clearPayload(key: string) {
    delete data.tempPayloads[key];
  },
};
```

### 3.3 初始化时机

`App.vue` 的 `onLaunch` 里：

```ts
// App.vue
import { globalData } from '@/store/globalData';

onLaunch((options) => {
  globalData.set('launchOptions', options);
  globalData.set('systemInfo', uni.getSystemInfoSync());
});
```

---

## 四、自定义 Hook 规范

### 4.1 分类

- **通用型** `hooks/common/`：`useDebounce`、`useThrottle`、`useRequest`、`useCountdown`
- **业务型** `hooks/business/`：`useLoginCheck`、`useShareConfig`、`useTabbarHeight`
- **页面型**：写在页面内，不抽离

### 4.2 编写规范

```ts
// hooks/common/useRequest.ts
import { ref, Ref } from 'vue';

interface UseRequestReturn<T> {
  data: Ref<T | null>;
  loading: Ref<boolean>;
  error: Ref<Error | null>;
  run: (...args: unknown[]) => Promise<T>;
  refresh: () => Promise<T>;
}

export function useRequest<T>(
  fn: (...args: unknown[]) => Promise<T>,
  options: { immediate?: boolean; defaultParams?: unknown[] } = {},
): UseRequestReturn<T> {
  const data = ref<T | null>(null) as Ref<T | null>;
  const loading = ref(false);
  const error = ref<Error | null>(null);
  let lastParams: unknown[] = options.defaultParams ?? [];

  const run = async (...args: unknown[]) => {
    loading.value = true;
    error.value = null;
    lastParams = args.length ? args : lastParams;
    try {
      const res = await fn(...lastParams);
      data.value = res;
      return res;
    } catch (e) {
      error.value = e as Error;
      throw e;
    } finally {
      loading.value = false;
    }
  };

  const refresh = () => run(...lastParams);

  if (options.immediate) run(...lastParams);

  return { data, loading, error, run, refresh };
}
```

### 4.3 规范要点

- **`use` 前缀**：识别度，遵守 Vue Composition API 约定
- **返回对象而非数组**：具名属性比 `[0]/[1]` 可读性高
- **副作用在内部管理**：内部的 `watch`、`setTimeout` 需要在卸载时清理（`onUnmounted`）
- **不依赖 DOM**：uni-app 多端无 DOM，避免 `document.querySelector`
- **类型清晰**：所有入参、返回值显式标类型
- **无副作用的纯逻辑** 考虑放 `utils/`，不要无脑抽 hook

### 4.4 uni-app 专属 hook 示例

```ts
// hooks/common/useTabbarHeight.ts
export function useTabbarHeight() {
  const systemInfo = uni.getSystemInfoSync();
  // 安全区 + tabbar 原生高度
  // #ifdef MP-WEIXIN
  const tabbarHeight = 50;
  // #endif
  // #ifdef H5
  const tabbarHeight = 50;
  // #endif
  return {
    tabbarHeight,
    safeAreaBottom: systemInfo.safeAreaInsets?.bottom ?? 0,
    totalBottom: tabbarHeight + (systemInfo.safeAreaInsets?.bottom ?? 0),
  };
}
```

---

## 五、组合：Pinia + Hook 的协作

典型模式：**store 管状态，hook 管逻辑编排**。

```ts
// hooks/business/useLoginCheck.ts
import { useUserStore } from '@/pinia/modules/user';
import { appUtils } from '@/router/utils';

export function useLoginCheck() {
  const userStore = useUserStore();

  async function ensureLogin(): Promise<boolean> {
    if (userStore.isLogin) return true;
    await appUtils.goto({ url: '/pages/login/index', type: 'push' });
    return false;
  }

  return { ensureLogin, isLogin: userStore.isLogin };
}
```

业务页面：

```ts
const { ensureLogin } = useLoginCheck();

async function onBuy() {
  if (!(await ensureLogin())) return;
  // ... 真正的购买逻辑
}
```

这样既保持了 Pinia 的单一数据源，又把"检查 + 跳转"的编排逻辑内聚到 hook 里，避免业务页面重复 `if (!isLogin) ...`。
