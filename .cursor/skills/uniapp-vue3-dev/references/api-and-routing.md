# API 请求层 & 路由规范

本文档覆盖两块强相关的基建：**HTTP 请求封装** 与 **页面路由/跳转封装**。

---

## 一、API 请求三层架构

### 分层图

```
业务代码（页面/hook/store）
         ↓ 只能调这层
   apiService/*.ts        ← 业务语义层（getOrderList、submitForm）
         ↓
   request/index.ts       ← 基建层（拦截器、错误码、loading、重试）
         ↓
   uni.request / fetch    ← 平台原生
```

### 三层各自职责

#### 1. 基建层 `request/`
封装通用能力，**不感知业务**：
- 请求/响应拦截器（加 token、加 traceId、统一解包 `{code, data, msg}`）
- 业务错误码统一处理（401 跳登录、500 弹提示）
- loading / 防重复提交
- 超时、重试
- 统一日志打点

示例骨架：

```ts
// request/types.ts
export interface ApiResponse<T = unknown> {
  code: number;
  data: T;
  msg: string;
}

export interface RequestOptions extends UniApp.RequestOptions {
  loading?: boolean;        // 是否显示 loading
  silent?: boolean;         // 是否吞掉错误不提示
  retry?: number;           // 重试次数
}

// request/index.ts
export function request<T>(options: RequestOptions): Promise<T> {
  // 1. 请求前：加 token / loading
  // 2. 调 uni.request
  // 3. 响应后：统一解包 + 错误码分发
  // 4. 失败：重试 / 上报 / toast
}

export const get = <T>(url: string, data?: object, opts?: Partial<RequestOptions>) =>
  request<T>({ url, method: 'GET', data, ...opts });

export const post = <T>(url: string, data?: object, opts?: Partial<RequestOptions>) =>
  request<T>({ url, method: 'POST', data, ...opts });
```

#### 2. 业务语义层 `apiService/`
按**业务域**一个文件，暴露语义化函数：

```ts
// apiService/order.ts
import { get, post } from '@/request';
import type { OrderItem, OrderListReq } from '@/types';

export function getOrderList(params: OrderListReq) {
  return get<OrderItem[]>('/api/order/list', params);
}

export function submitOrder(payload: Pick<OrderItem, 'skuId' | 'count'>) {
  return post<{ orderId: string }>('/api/order/submit', payload, { loading: true });
}
```

**关键点**：
- 每个函数**有明确返回类型**，业务方靠 TS 感知响应结构。
- 请求/响应类型放 `types/api.d.ts`，避免重复定义。
- 函数名用"动词 + 业务名词"，如 `getXxx` / `submitXxx` / `cancelXxx`。

#### 3. 业务调用层
```ts
// 页面里
import { getOrderList } from '@/apiService';

const list = await getOrderList({ page: 1 });
// list 已经是 OrderItem[]，不需要再 .data.data
```

### 反模式

- ❌ 组件里 `uni.request({ url: '/api/xxx' })`
- ❌ 在 `apiService/` 里处理 loading / toast / 跳登录（这些是基建层的事）
- ❌ 在 `request/` 里写业务特定错误码（如"优惠券已过期"）
- ❌ 响应结构 `ApiResponse<T>` 直接泄漏到页面（应在 request 层解包）

---

## 二、路由与页面规范

### 2.1 页面文件组织

- 主包页面：`src/pages/<业务>/<页面>.vue`
- 分包页面：`src/page_xxx/pages/<页面>.vue`
- 入口文件**统一命名** `index.vue`，避免 `home.vue` 与 `Home.vue` 等差异。

### 2.2 路由模块化（推荐）

**问题**：`pages.json` 随项目膨胀到几千行，冲突高发。

**方案**：按业务域拆 `router/modules/*.ts`，脚本合并生成 `pages.json`。

```ts
// router/modules/order.ts
export default {
  root: 'page_order',
  pages: [
    { path: 'pages/list', style: { navigationBarTitleText: '订单列表' } },
    { path: 'pages/detail', style: { navigationBarTitleText: '订单详情' } },
  ],
};
```

```js
// router/generate.js（构建前执行）
const fs = require('fs');
const path = require('path');

const modulesDir = path.join(__dirname, 'modules');
const subPackages = fs.readdirSync(modulesDir)
  .filter(f => f.endsWith('.ts') || f.endsWith('.js'))
  .map(f => require(path.join(modulesDir, f)).default);

const pagesJson = {
  pages: [/* 主包页面 */],
  subPackages,
  globalStyle: { /* ... */ },
  tabBar: { /* ... */ },
};

fs.writeFileSync(
  path.join(__dirname, '../pages.json'),
  JSON.stringify(pagesJson, null, 2),
);
```

在 `package.json` 里：
```json
{
  "scripts": {
    "prebuild": "node src/router/generate.js",
    "predev:h5": "node src/router/generate.js"
  }
}
```

### 2.3 路由工具封装（必做）

**禁止**业务代码直接 `uni.navigateTo`。封装一个全局 `appUtils`：

```ts
// router/utils.ts
interface GotoOptions {
  url: string;
  params?: Record<string, unknown>;
  type?: 'push' | 'replace' | 'reLaunch' | 'switchTab';
  needLogin?: boolean;
}

export const appUtils = {
  async goto(opts: GotoOptions) {
    // 1. 登录拦截
    if (opts.needLogin && !useUserStore().isLogin) {
      return this.goto({ url: '/pages/login/index', type: 'push' });
    }
    // 2. 拼接 query
    const url = buildUrl(opts.url, opts.params);
    // 3. 页面层级降级（微信小程序最多 10 层，超过用 redirectTo）
    const pageCount = getCurrentPages().length;
    const method = pageCount >= 9 && opts.type === 'push'
      ? 'redirectTo'
      : mapType(opts.type);
    // 4. 埋点
    track('route_goto', { from: currentRoute(), to: opts.url });
    // 5. 执行
    return uni[method]({ url });
  },

  goBack(delta = 1) {
    if (getCurrentPages().length <= 1) {
      return uni.reLaunch({ url: '/pages/home/index' });
    }
    return uni.navigateBack({ delta });
  },
};
```

**为什么要封装？** 三件事业务代码没法每处都写：
1. **层级降级**：微信小程序页面栈最多 10 层，超过 `navigateTo` 会失败，需降级为 `redirectTo`。
2. **登录拦截**：统一处理未登录跳登录页。
3. **埋点**：路由变更统一上报，业务无感。

### 2.4 分包策略

- **按业务域拆**：`page_order/`、`page_mine/`、`page_activity/`
- **分包大小**：单个分包 ≤ 2MB，总包可到 20MB（微信小程序）
- **分包预下载**：在 `pages.json` 里配 `preloadRule`，首页空闲时预加载高频分包
- **独立分包**：活动页等可脱离主包独立运行的场景，配 `independent: true`

---

## 三、新增 API 的 SOP

1. 在 `types/api.d.ts` 里定义请求入参 + 响应结构类型
2. 在 `apiService/<业务域>.ts` 里加函数，import 类型并标注返回值
3. 在 `apiService/index.ts` 里 barrel 导出
4. 业务代码从 `@/apiService` import 调用
5. 如果该接口有**特殊错误码**（如 `10086 = 优惠券已过期`），在业务函数 catch 里处理，**不要污染 request 基建层**

## 四、新增页面的 SOP

1. 判断归属：主包（高频/入口）还是分包（业务独立）？
2. 建文件：`pages/<业务>/index.vue` 或 `page_xxx/pages/<页面>.vue`
3. 在 `router/modules/<业务>.ts` 加路由配置
4. 运行 `generate.js` 重新生成 `pages.json`（如果项目用了此方案）
5. 调用方用 `appUtils.goto({ url: '/page_xxx/pages/xxx', params: {...} })`
6. 页面内用 `onLoad(query)` 接收参数（注意：query 都是 string，需要 Number/JSON.parse）
