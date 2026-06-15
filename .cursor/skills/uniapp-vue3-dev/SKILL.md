---
name: uniapp-vue3-dev
description: 面向 uni-app + Vue3 + TypeScript 工程的通用开发规范与最佳实践。当任务涉及 uni-app 项目的目录规划、新增页面、新增组件、API 请求封装、路由/分包配置、Pinia 状态、hooks 抽离、多端（H5/小程序/App）条件编译、平台兼容差异、可扩展组件架构（插件式/运营位）等场景时应加载本 skill。本 skill **不绑定任何业务**，仅提供方法论与可复用模式。
---

# uni-app + Vue3 + TS 通用开发 Skill

本 skill 从真实的 uni-app 工程实践中抽象而来，提供**跨项目通用**的目录结构、分层架构、编码规范和落地 SOP。所有示例均为示意，不包含任何特定业务耦合。

---

## 触发条件（何时加载本 skill）

在 **同时满足** 以下两个条件时触发：

1. **项目类型匹配**：当前工程是 uni-app 项目（识别信号任一即可）：
   - 存在 `manifest.json` + `pages.json`
   - `package.json` 的 `dependencies` 含 `@dcloudio/uni-app` / `@dcloudio/vite-plugin-uni`
   - scripts 中含 `dev:h5` / `dev:mp-weixin` / `build:app-*` 等 uni 专用命令
   - 源码目录有 `src/pages/`、`src/page_xxx/` 分包、或 `pages.json` 里有 `subPackages`
2. **任务内容匹配**（用户请求中出现下列任一）：
   - "uni-app / uniapp / uni 小程序 / vue3 小程序" 相关开发
   - 新增/修改 **页面、分包、组件、hook、pinia store、API 请求层、路由封装**
   - **多端兼容**问题、**条件编译**（`#ifdef` / `#ifndef`）、平台差异排查
   - 请求拦截器、登录鉴权、埋点统一封装
   - "插件式/运营位/可扩展组件" 架构设计（枚举 + 映射表驱动的动态渲染）
   - uni 构建/发布（微信小程序、H5、App）相关配置

## 不触发条件（何时不加载）

下列情况不要加载本 skill：

- 纯 Web 项目（React / Vue Web / Nuxt 等），不含 uni-app 依赖
- 纯原生小程序（使用 wxml/wxss 的原生微信小程序，没有 uni-app）
- 纯 Electron / Tauri 桌面端项目
- uni-app **官方 API 的参数查询**（如 `uni.request` 某个参数怎么写）—— 应直接查文档而非加载本 skill
- 仅改 README / 文档 / 提交信息
- 仅做 Node/后端开发的任务
- 具体业务逻辑实现（如"做一个商品详情页"）—— 这类任务本 skill 仅作为背景规范参考，主要工作靠业务理解

---

## 核心原则（摘要）

> 详细内容见 `references/` 下各主题文档。使用本 skill 时，**先按需加载对应 reference**，不要一次性全部读入。

1. **分层清晰**：UI 层 (`pages/components`) → 业务 hook 层 (`hooks`) → Pinia 层 (`pinia`) → API 层 (`apiService`) → 请求基建层 (`request`)，单向依赖，下层不感知上层。
2. **模块化路由**：页面按业务域拆分到 `router/modules/*.ts`，再合并到 `pages.json`；分包按业务域命名为 `src/page_xxx/`，控制主包 ≤ 2MB。
3. **API 三层隔离**：业务代码只调 `apiService/xxx.ts` 暴露的函数，不直接写 `uni.request`。
4. **条件编译先行**：写多端代码时先想"这段在哪些端运行"，用 `#ifdef` / `#ifndef` 明确隔离，禁止运行时 `process.env.PLATFORM` 硬判断。
5. **禁止魔法字符串**：跨文件传递的状态、类型、key 一律走枚举 / 常量。
6. **禁止裸 `uni.navigateTo`**：全局封装路由工具，统一处理层级降级、登录拦截、埋点。
7. **可扩展组件**：运营位 / 动态卡片使用"枚举 + 组件映射表 + 数据处理器" 三件套，避免 `v-if` 地狱。

---

## 按需加载的参考文档（references/）

根据具体任务，**选择性加载** 以下文档，避免一次性读全量：

| 场景 | 应加载的文档 |
|---|---|
| 新建项目 / 梳理目录 / 文件归属拿不准 | `references/project-structure.md` |
| 新增/改 API、写请求拦截、对接后端 | `references/api-and-routing.md`（§API 部分） |
| 新增页面、配分包、封装路由跳转 | `references/api-and-routing.md`（§路由部分） |
| H5 与小程序表现不一致、写多端兼容 | `references/platform-compatibility.md` |
| 写 Pinia store / 自定义 hook / 用 globalData | `references/state-and-hooks.md` |

---

## 使用本 skill 的工作流

当任务匹配触发条件后，按以下顺序执行：

1. **识别任务归属**：根据上表确定需要读哪 1-2 份 reference。
2. **对照现状**：用 `list_dir` / `search_file` 看当前项目的实际目录与命名，**尊重既有约定**，不要强行套用本 skill 的示例命名。
3. **规划改动点**：按 reference 中的 SOP（新增页面 / 新增 API / 新增可扩展组件等）列出改动文件清单。
4. **执行**：使用 `replace_in_file` 做增量修改；新建文件前先确认目录是否存在。
5. **校验**：
   - 是否有硬编码路径、魔法字符串？→ 抽枚举
   - 是否直接调用 `uni.request` / `uni.navigateTo`？→ 走封装
   - 是否只在单端测过？→ 至少列出其它端可能影响点
   - 新增的 store / hook / api 是否在 index.ts 做了 barrel 导出？

---

## 禁止事项（硬红线）

- ❌ 业务页面里直接 `import` 另一个业务页面的内部方法（跨页面耦合）
- ❌ 在组件里直接 `uni.request` / `fetch` / `axios`（绕过 API 层）
- ❌ 在组件里直接写 `uni.navigateTo({ url: '/pages/xxx/xxx' })`（绕过路由封装）
- ❌ 用字符串表示业务枚举（如 `type === 'bill'`）
- ❌ 在 `App.vue` / `main.ts` 塞大量业务初始化逻辑（应由对应 store/hook 自治）
- ❌ 修改 `node_modules` 或 `unpackage/` 目录下的产物
- ❌ 把密钥、token、AppID 硬编码到源码，应走 `.env.*` + `manifest.json` 注入

---

## 版本与适用范围

- **适用**：uni-app（vue3 + vite 构建版本，`@dcloudio/vite-plugin-uni`）+ TypeScript + Pinia + Vue Router 风格的路由模块化
- **不强制**：UI 组件库（uview / uni-ui / 自研均可）、请求库（`uni.request` 原生或二次封装均可）、语言（JS 也可套用结构，只是类型约束会弱）

遇到不明确的约定时，**优先遵循当前项目已存在的惯例**，其次才是本 skill 的建议。
