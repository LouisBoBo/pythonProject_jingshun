# 多端兼容与条件编译

> uni-app 的核心价值是"一套代码多端运行"，但**不等于所有 API 都跨端一致**。本文档列出常见坑与规范。

---

## 一、条件编译语法

### 1.1 基本形式

```ts
// #ifdef H5
console.log('只在 H5 执行');
// #endif

// #ifdef MP-WEIXIN
wx.getSystemInfoSync();
// #endif

// #ifndef APP-PLUS
// 除 App 外都执行
// #endif

// #ifdef H5 || MP-WEIXIN
// H5 或微信小程序
// #endif
```

### 1.2 支持的平台标识

| 标识 | 含义 |
|---|---|
| `H5` | H5 |
| `APP-PLUS` | App（vue 版） |
| `MP` | 所有小程序 |
| `MP-WEIXIN` | 微信小程序 |
| `MP-ALIPAY` | 支付宝小程序 |
| `MP-BAIDU` | 百度小程序 |
| `MP-TOUTIAO` | 字节跳动小程序 |
| `MP-QQ` | QQ 小程序 |

### 1.3 可用位置

- `.vue` 文件的 `<template>` / `<script>` / `<style>`
- `.ts` / `.js` / `.json` / `.scss` 文件
- `pages.json`、`manifest.json`

```vue
<template>
  <!-- #ifdef MP-WEIXIN -->
  <button open-type="getUserProfile">微信授权</button>
  <!-- #endif -->

  <!-- #ifdef H5 -->
  <button @tap="h5Login">H5 登录</button>
  <!-- #endif -->
</template>
```

### 1.4 文件级条件编译

按后缀区分：
- `api.h5.ts` → 只在 H5 编译
- `api.mp-weixin.ts` → 只在微信小程序编译

```ts
// api/index.ts
import { login } from './api';       // 自动按平台找到 api.h5.ts 或 api.mp-weixin.ts
```

---

## 二、常见平台差异速查

| 能力 | H5 | 微信小程序 | App |
|---|---|---|---|
| `localStorage` | ✅ | ❌（用 `uni.setStorage`） | ✅ |
| DOM 操作 | ✅ | ❌ | ❌ |
| `window` / `document` | ✅ | ❌ | ❌ |
| `cookie` | ✅ | ❌（手动在 header 维护） | ✅ |
| `setTimeout` 后台执行 | ✅ | ⚠️（切后台会暂停） | ⚠️ |
| 文件下载 | 浏览器行为 | `uni.downloadFile` + `uni.saveFile` | 同小程序 |
| 分享 | 需第三方 SDK | `onShareAppMessage` | 原生 API |
| 支付 | H5 支付网关 | `uni.requestPayment` | SDK |
| 登录 | OAuth 跳转 | `uni.login` + code 换 openid | 原生登录 |
| 页面栈深度 | 无限制 | 最多 10 层 | 一般 10 层 |
| `<web-view>` | 同源限制 | 业务域名白名单 | 无限制 |
| 路由参数大小 | 无限制 | ~2KB | 较大 |

---

## 三、必须注意的坑

### 3.1 query 参数只能传基本类型

微信小程序 URL query 有 **~2KB 大小限制**，且只能是字符串。

**错误**：
```ts
uni.navigateTo({ url: `/pages/detail/index?item=${JSON.stringify(item)}` });
```

**正确**（大对象走 globalData / store 中转）：
```ts
useTempStore().setPayload(item);
uni.navigateTo({ url: '/pages/detail/index?payloadId=xxx' });
```

### 3.2 `getCurrentPages()` 在 App.vue 里为空

页面还没加载时调 `getCurrentPages()` 返回 `[]`，不要在 `onLaunch` 里依赖当前页面。

### 3.3 小程序没有 `window.location`

获取当前页面 URL：
```ts
const pages = getCurrentPages();
const current = pages[pages.length - 1];
// H5: current.$page.fullPath
// 小程序: current.route + options
```

### 3.4 样式单位

- 优先 `rpx`：以 750rpx 为屏幕宽度（小程序） / 375px × 2（H5）
- **`rpx` 在 H5 也生效**，uni-app 会自动换算
- 固定像素（边框）用 `px`
- `vh` / `vw`：**小程序部分旧版本不支持**，用 `rpx` 替代

### 3.5 事件绑定

- uni-app 推荐 `@tap` 而非 `@click`
- `@click` 在小程序实际也是 tap，差异小，但 H5 上 `@click` 有 300ms 延迟（旧机型）
- 统一用 `@tap`

### 3.6 v-show vs v-if

- 小程序的 `v-show` 生成 `hidden` 属性，性能更好
- 频繁切换用 `v-show`，条件不变用 `v-if`

### 3.7 无法用 CSS `position: fixed` 的背景

小程序的 `page` 元素背景 fixed 失效，需在 `pages.json` 里配：
```json
{
  "style": {
    "backgroundColor": "#f5f5f5",
    "backgroundColorContent": "#f5f5f5"
  }
}
```

### 3.8 tabbar 页不能用 `navigateTo`

```ts
// ❌ 失败
uni.navigateTo({ url: '/pages/home/index' });
// ✅
uni.switchTab({ url: '/pages/home/index' });
```

路由封装工具应根据目标页是否是 tabbar 自动切换方法。

---

## 四、写多端代码的工作流

1. **先想清楚**：这个功能在每个端是否都存在？不存在的端怎么降级？
2. **优先跨端 API**：`uni.setStorage` > `localStorage`；`uni.request` > `fetch`
3. **平台专属代码用 `#ifdef` 隔离**，不要用 `process.env.UNI_PLATFORM === 'h5'` 硬判（条件编译在**编译期**剔除，运行时判断会把所有平台代码打进包里）
4. **每个端至少冒烟测试一次**：`yarn dev:h5`、`yarn dev:mp-weixin`、App 真机
5. **分享 / 支付 / 登录 / 推送** 四大高危区，必须分端实现并各自测试

---

## 五、manifest.json 的常见配置

- **H5**：`base` 路径、路由模式（`hash` / `history`）、代理
- **小程序**：AppID、permission、requiredBackgroundModes、分包配置
- **App**：包名、证书、启动图、权限、SDK 配置

`manifest.json` **不要提交敏感信息**（AppID / AppSecret 走环境变量或 CI 注入）。
