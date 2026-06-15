# 项目结构规范（uni-app + Vue3 + TS 通用）

> 本文档描述一个**职责分层、按业务域组织**的 uni-app 工程结构，适用于中大型项目。小项目可按需裁剪。

## 目标

- **单向依赖**：UI → hook → store → api → request，上层可依赖下层，反向禁止。
- **按域分包**：主包仅保留入口与公共页面，业务页面按域拆 `page_xxx/` 子分包，控制主包体积 ≤ 2MB（微信小程序硬限制）。
- **barrel 导出**：每个二级目录提供 `index.ts` 汇总导出，业务代码只从目录根 import，方便重构。

---

## 推荐目录

```
src/
├── main.ts                  # 应用入口，只做 app 级初始化
├── App.vue                  # 全局生命周期，只做全局监听（登录态、主题等）
├── pages.json               # uni 页面路由配置（由 router/generate 脚本生成或手工维护）
├── manifest.json            # 平台配置、AppID、权限
│
├── pages/                   # 主包页面（tabbar 页、登录、启动页）
│   └── home/index.vue
│
├── page_xxx/                # 业务子分包（每个业务域一个分包）
│   ├── pages/               # 该分包的页面
│   └── components/          # 该分包独占的组件
│
├── components/              # 全局通用组件
│   ├── common/              # 原子组件：Button、Icon、Empty
│   └── business/            # 跨业务复用的业务组件
│
├── hooks/                   # 组合式逻辑
│   ├── common/              # 通用：useDebounce、useRequest、useTabbarHeight
│   ├── business/            # 跨页面复用的业务 hook
│   └── index.ts
│
├── pinia/                   # 状态管理
│   ├── modules/
│   │   ├── user.ts
│   │   └── app.ts
│   └── index.ts
│
├── apiService/              # 业务 API 聚合层（按业务域分文件）
│   ├── user.ts              # 导出 login / getUserInfo ...
│   ├── order.ts
│   └── index.ts             # barrel
│
├── request/                 # 请求基建层
│   ├── index.ts             # 封装 uni.request / axios，拦截器、错误码
│   ├── interceptor.ts
│   └── types.ts             # ApiResponse<T>、RequestOptions
│
├── router/                  # 路由模块化
│   ├── modules/             # 每个业务域一个路由配置
│   │   ├── home.ts
│   │   └── order.ts
│   ├── generate.js          # 合并 modules 生成 pages.json（可选）
│   └── utils.ts             # appUtils.goto / goBack / redirect 等封装
│
├── store/                   # 非响应式的全局单例（globalData、缓存管理器）
│   └── globalData.ts
│
├── utils/                   # 纯函数工具
│   ├── date.ts
│   ├── format.ts
│   └── index.ts
│
├── constants/               # 全局常量与枚举
│   ├── enum.ts
│   └── config.ts
│
├── types/                   # 全局 TS 类型
│   ├── api.d.ts
│   ├── business.d.ts
│   └── global.d.ts
│
├── static/                  # 静态资源（图片、字体），打包不处理
└── styles/                  # 全局样式、变量、mixin
    ├── variables.scss
    └── common.scss
```

---

## 各目录职责边界

### `pages/` vs `page_xxx/`
- `pages/`：**主包**，只放 tabbar 页、启动页、登录页等所有用户都会进的高频页面。
- `page_xxx/`：**子分包**，业务域独立。命名建议用业务简写，如 `page_order/`、`page_mine/`。
- 判断标准：新页面是否所有用户都会打开？是 → 主包；否 → 分包。

### `components/` vs `page_xxx/components/`
- 全局 `components/`：**≥2 个分包**会用到 → 放这里。
- 分包内 `components/`：**只有该分包**用 → 就近放置，降低主包体积。

### `hooks/` vs 页面内 `<script setup>`
- 逻辑可抽离、可复用、或单文件超过 300 行 → 抽 hook。
- 只服务单个页面且 <100 行 → 留在页面内。

### `apiService/` vs `request/`
- `request/`：**不感知业务**，只负责网络、拦截、错误码、loading。
- `apiService/`：**按业务域聚合**，暴露语义化函数（`getUserProfile()`），内部调 `request`。
- 业务代码**只能 import apiService**，禁止直接 import request。

### `store/globalData` vs `pinia/`
- `pinia`：**响应式**状态，UI 需要监听变化。
- `globalData`：**非响应式**单例（设备信息、启动参数、系统配置），只读多，写少，不需要触发 UI 更新。
- 判断：UI 要不要跟着变？要 → pinia；不要 → globalData。

---

## 命名约定

| 类型 | 约定 | 示例 |
|---|---|---|
| 目录 | kebab-case 或 snake_case（遵循项目既有） | `page_order/` |
| Vue 组件文件 | PascalCase | `UserAvatar.vue` |
| 页面文件 | 小写，入口统一 `index.vue` | `pages/home/index.vue` |
| hook | `use` 前缀 + camelCase | `useLoginCheck.ts` |
| pinia store | `useXxxStore` | `useUserStore` |
| API 函数 | 动词 + 名词 camelCase | `getOrderList`, `submitOrder` |
| 枚举 | PascalCase，值用 UPPER_SNAKE | `enum OrderStatus { PENDING, PAID }` |
| 常量 | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| 类型 | PascalCase，泛型 `T`/`TItem` | `type OrderItem` |

---

## barrel 导出规范

每个二级目录必须有 `index.ts`：

```ts
// apiService/index.ts
export * from './user';
export * from './order';

// 业务代码统一这样 import
import { getOrderList } from '@/apiService';
// 不要 import { getOrderList } from '@/apiService/order';
```

**好处**：重构时只改 barrel，业务代码零感知。

---

## 常见反模式

- ❌ 所有页面都塞在 `pages/` 下，主包超过 2MB
- ❌ `components/` 里堆满只用一次的页面私有组件
- ❌ hook 里直接操作 DOM（uni 多端无 DOM 概念）
- ❌ `utils/` 里放带副作用的函数（应放 service/hook）
- ❌ 一个 store 文件超过 500 行（按业务域拆分）
