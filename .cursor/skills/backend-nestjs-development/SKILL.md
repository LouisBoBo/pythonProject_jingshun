---
name: backend-nestjs-development
description: |
  NestJS 后端开发通用规范（ORM 无关）。提供分层架构、Controller / Service / Module / DTO、统一响应、异常处理、鉴权、Swagger、日志、安全、跨 ORM 抽象（SqlSdk）等核心约定。
  **触发**：用 NestJS 写 Controller / Service / Module / DTO / 鉴权 / 异常 / 响应封装 / Swagger / 日志 / 配置 / 文件上传 / 缓存等任务。
  **不触发**：前端、非 NestJS 后端。
  **配套 ORM skill**：定义表/查询/事务时同时加载 `orm-drizzle` / `orm-typeorm` / `orm-sequelize` 中**项目实际使用**的那一个。
---

# NestJS 后端开发规范

## 0. 核心原则

1. **三层职责**：Controller 收请求、Service 处业务、ORM/SqlSdk 访数据。Controller 不写业务，Service 不感知 HTTP。
2. **ORM 直接进 Service**：本规范允许 Service 直接注入 Repository / Model / db，无需 DAO 抽象层。**多 ORM 共存**靠 `SqlSdk`（裸 SQL）解决。
3. **统一响应**：业务方法只 `return data`；包装 `{ code, message, data }` 由全局 `ResponseInterceptor` 完成。
4. **统一异常**：业务错误 `throw new ServiceException('xxx')`，由全局 Filter 转成 `{ code: FAIL, message }`。
5. **DTO 用 class**：Swagger / class-validator 都需要运行时元数据；禁用 `interface`。
6. **必有 Swagger**：所有 Controller / DTO 加注解；响应类型用 `createResultDataDto / createResultDataPageDto`。
7. **必有鉴权**：业务接口加 `@UseGuards(AdminAuthGuard)` + `@ApiBearerAuth()`，公开接口加 `@Public()`。
8. **SQL 注入零容忍**：参数化查询；动态字段名/排序必须白名单。
9. **关联关系 ORM 内声明，库内不建外键**：避免数据迁移与多写场景被外键拖累。
10. **命名规范固定**：表名 `snake_case + 模块前缀`（如 `sys_user`），TS 变量/属性 `camelCase`，类型/类 `PascalCase`。

---

## 1. 推荐目录结构

```
src/
├── main.ts                     # 启动 + 全局 Pipe/Filter/Interceptor/Swagger
├── app.module.ts               # 根模块
├── common/
│   ├── exception/              # ServiceException
│   ├── filter/                 # AllExceptionsFilter
│   ├── interceptor/            # ResponseInterceptor
│   ├── decorator/              # @Public、@CurrentUser、@OperationLog 等
│   ├── interface/              # ResultData / createResultDataDto 等
│   └── logger/                 # winston 封装
├── guards/                     # AdminAuthGuard / PermissionGuard / JwtStrategy
├── config/                     # ConfigService 包装 + AppConfigKey 枚举
├── enum/                       # 业务枚举常量
├── db/                         # 表/实体/模型 + 数据库 Module（具体见对应 ORM skill）
├── sdk/
│   └── sqlSdk/                 # 跨 ORM 的裸 SQL + 分页抽象
├── modules/
│   └── 业务域/                 # 如 admin/user
│       ├── xxx.module.ts
│       ├── xxx.controller.ts
│       ├── xxx.service.ts
│       └── dto/xxx.dto.ts
└── utils/                      # 通用工具
```

---

## 2. 命名规范

### 数据库表

| 模块 | 前缀 | 示例 |
|------|------|------|
| 系统管理 | `sys_` | `sys_user` / `sys_role` / `sys_permission` |
| 业务域 X | `x_` | `x_order` / `x_order_item` |
| 关联表 | `主_从` | `sys_user_role` |

- 单数名词、全小写下划线（`sys_user`，**不用** `sys_users` / `sysUser`）
- 字段名同样 `snake_case`（`real_name` / `created_at`）
- ORM 负责 `real_name` ↔ `realName` 字段映射

### TS 侧映射（一眼记忆法）

```
sys_user_role         (表：snake_case + 前缀)
     ↓ 去下划线
sysUserRole           (TS 变量 / 属性：camelCase)
SysUserRole           (TS 类 / 类型：PascalCase)
SysUserRoleDto        (DTO：PascalCase + Dto)
sys-user-role.ts      (文件名：kebab-case)
```

---

## 3. DTO 规范

### 命名

| 用途 | 命名 | 位置 |
|------|------|------|
| 创建 | `Create实体Dto` | `modules/.../dto/` |
| 更新 | `Update实体Dto` | `modules/.../dto/` |
| 查询 | `Query实体Dto`（含分页字段） | `modules/.../dto/` |
| 输出 | `实体Dto` / `实体WithXxxDto` | `modules/.../dto/` |

### 写法（每个字段必须 `@ApiProperty` + `class-validator`）

```typescript
import { ApiProperty } from '@nestjs/swagger';
import { IsString, IsNotEmpty, IsOptional, IsNumber, IsArray, IsEmail, ValidateIf } from 'class-validator';

export class CreateUserDto {
  @ApiProperty({ description: '用户名', example: 'admin' })
  @IsString() @IsNotEmpty()
  username: string;

  @ApiProperty({ description: '密码', example: 'admin123' })
  @IsString() @IsNotEmpty()
  password: string;

  @ApiProperty({ description: '邮箱', required: false })
  @ValidateIf((o) => o.email !== undefined && o.email !== '')
  @IsEmail() @IsOptional()
  email?: string;

  @ApiProperty({ description: '角色ID列表', required: false, example: [1, 2] })
  @IsArray() @IsNumber({}, { each: true }) @IsOptional()
  roleIds?: number[];
}

export class QueryUserDto {
  @ApiProperty({ description: '用户名（模糊）', required: false })
  @IsString() @IsOptional()
  username?: string;

  @ApiProperty({ description: '状态', required: false })
  @IsNumber() @IsOptional()
  status?: number;

  @ApiProperty({ description: '页码', example: 1, required: false })
  @IsNumber() @IsOptional()
  page?: number;

  @ApiProperty({ description: '每页数量', example: 10, required: false })
  @IsNumber() @IsOptional()
  pageSize?: number;
}
```

### 常用 class-validator

| 场景 | 装饰器 |
|------|--------|
| 必填字符串 | `@IsString() @IsNotEmpty()` |
| 整数 | `@IsNumber()` / `@IsInt()` |
| 数组 | `@IsArray() @IsNumber({}, { each: true })` |
| 邮箱（允许空字符串） | `@ValidateIf(o => o.email) @IsEmail()` |
| 枚举 | `@IsIn([1, 2, 3])` |
| 嵌套对象 | `@ValidateNested({ each: true }) @Type(() => XxxDto)` |

---

## 4. Controller 规范

### HTTP 方法选择

| 操作 | 方法 | 路径示例 |
|------|------|---------|
| 列表（复杂筛选/分页） | **`POST`** | `/list` |
| 详情 | `GET` | `/:id` |
| 创建 | `POST` | `/` |
| 更新 | `PUT` | `/:id` |
| 删除 | `DELETE` | `/:id` |
| 简单选项 | `GET` | `/options` |

> 列表用 `POST` 是工程约定：复杂查询条件（数组/嵌套对象）GET 难传，URL 长度 / 敏感信息 / 类型校验都更友好。

### 标准模板

```typescript
import { Controller, Get, Post, Put, Delete, Body, Param, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth, ApiParam } from '@nestjs/swagger';
import { AdminAuthGuard } from '@/guards/admin-auth.guard';
import { OperationLog } from '@/common/decorator/operation-log.decorator';
import { createResultDataDto, createResultDataPageDto } from '@/common/interface/ResultData';
import { UserService } from './user.service';
import { CreateUserDto, UpdateUserDto, QueryUserDto, UserDto, UserWithRolesDto } from './dto/user.dto';

@ApiTags('用户管理__admin_user')
@Controller('apiAdmin/user')
@UseGuards(AdminAuthGuard)
@ApiBearerAuth()
export class UserController {
  constructor(private readonly userService: UserService) {}

  @Post('list')
  @ApiOperation({ summary: '获取用户列表（分页）' })
  @ApiResponse({ status: 200, type: createResultDataPageDto(UserWithRolesDto, '用户列表') })
  async getUserList(@Body() query: QueryUserDto) {
    return this.userService.getUserList(query);
  }

  @Get(':id')
  @ApiOperation({ summary: '根据ID获取用户' })
  @ApiParam({ name: 'id', description: '用户ID' })
  @ApiResponse({ status: 200, type: createResultDataDto(UserWithRolesDto, '用户信息') })
  async getUserById(@Param('id') id: number) {
    return this.userService.getUserById(+id);
  }

  @Post()
  @ApiOperation({ summary: '创建用户' })
  @OperationLog({ module: '用户管理', action: '创建用户' })
  async createUser(@Body() dto: CreateUserDto) {
    return this.userService.createUser(dto);
  }

  @Put(':id')
  @ApiOperation({ summary: '更新用户' })
  @OperationLog({ module: '用户管理', action: '更新用户' })
  async updateUser(@Param('id') id: number, @Body() dto: UpdateUserDto) {
    return this.userService.updateUser(+id, dto);
  }

  @Delete(':id')
  @ApiOperation({ summary: '删除用户' })
  @OperationLog({ module: '用户管理', action: '删除用户' })
  async deleteUser(@Param('id') id: number) {
    await this.userService.deleteUser(+id);
    return null;
  }
}
```

### 强约束

- 路由前缀按端区分：管理端 `/apiAdmin/...`、前台端 `/api/...`
- 业务接口必须 `@UseGuards(AdminAuthGuard)` + `@ApiBearerAuth()`
- 公开接口加 `@Public()` 装饰器跳过守卫
- 重要写操作加 `@OperationLog({ module, action })` 自动记日志
- Controller 不写业务逻辑、不直接访问数据库
- 不信任前端传的 `userId` / `organizationId` 等，从 `@CurrentUser()` 取

---

## 5. Service 规范

```typescript
@Injectable()
export class UserService {
  // 注入方式取决于所用 ORM，详见对应 orm-* skill
  constructor(/* ORM 句柄 */) {}

  async createUser(dto: CreateUserDto): Promise<UserDto> {
    const exists = await /* 查重 */;
    if (exists) throw new ServiceException('用户名已存在');

    const hashed = await bcrypt.hash(dto.password, 10);
    const saved = await /* 插入 */;
    return this.getUserById(saved.id);
  }

  async getUserById(id: number): Promise<UserWithRolesDto> {
    const user = await /* 查询 */;
    if (!user) throw new NotFoundException('用户不存在');
    return user;
  }
}
```

### 必守

- ✅ 只返回业务数据，不返回 `{ code, message, data }`
- ✅ 业务校验失败 `throw new ServiceException('...')`
- ✅ 资源找不到 `throw new NotFoundException('...')`
- ✅ 鉴权失败 `throw new UnauthorizedException('...')`
- ❌ 不要 `try/catch` 后返回 `{ success: false }`，让异常冒到 Filter
- ❌ 不要在 Service 里 import `Request` / `Response`

---

## 6. Module 注册

```typescript
@Module({
  imports: [
    /* 数据库 module（按 ORM 不同）见对应 orm-* skill */
    PermissionCacheModule,  // 共享业务模块
  ],
  controllers: [UserController],
  providers: [UserService],
  exports: [UserService],   // 跨模块复用时导出
})
export class UserModule {}
```

跨模块依赖时：在被依赖方 Module **export Service**，在依赖方 Module **import 该 Module**（不要直接把 Service 写到 providers）。

---

## 7. 异常 + 响应（约定）

### 业务异常

```typescript
import { HttpException, HttpStatus } from '@nestjs/common';
import { ResultCode } from '@/common/interface/ResultData';

export class ServiceException extends HttpException {
  constructor(message: string) {
    super({ code: ResultCode.FAIL, message }, HttpStatus.OK);
  }
}
```

使用：

```typescript
throw new ServiceException('用户名已存在');
throw new ServiceException('开始时间不能晚于结束时间');
```

### 响应包装

| 工具 | 用途 |
|------|------|
| `createResultDataDto(Dto, '描述')` | 单对象响应类型 |
| `createResultDataArrayDto(Dto, '描述')` | 数组响应类型 |
| `createResultDataPageDto(Dto, '描述')` | `{ list, total, page, pageSize }` 分页响应类型 |

由 `ResponseInterceptor` 自动包装：

```
{ code: 200, message: '操作成功', data: <业务数据> }
```

---

## 8. 鉴权与多租户

### 守卫

```typescript
@Controller('apiAdmin/user')
@UseGuards(AdminAuthGuard)        // 全 controller 鉴权
@ApiBearerAuth()
export class UserController {
  @Get('public-info')
  @Public()                       // 单接口跳过
  async publicInfo() { /* ... */ }
}
```

### 取当前用户

```typescript
@CurrentUser() user: AdminJwtPayload
```

### 强约束

- ✅ 任何敏感查询必须按租户/组织隔离：`where organization_id = ?`，参数从 `currentUser` 取
- ❌ 严禁信任 Body / Query 里的 `userId` / `organizationId`
- ✅ 密码必须 `bcrypt.hash(plain, 10)`，对比用 `bcrypt.compare`
- ❌ 响应 DTO 必须排除 `password / token / secret`

---

## 9. 全局配置（main.ts 必备）

```typescript
const app = await NestFactory.create<NestExpressApplication>(AppModule);

app.useGlobalFilters(new AllExceptionsFilter());
app.useGlobalPipes(new ValidationPipe({
  whitelist: false,            // 允许未声明字段透传（按团队偏好）
  forbidNonWhitelisted: true,
  transform: true,             // 自动 number / boolean 转型
}));
app.enableCors();

// Swagger 仅在 dev 开启
if (isDev) {
  const config = new DocumentBuilder()
    .setTitle('Nest API').setVersion('1.0')
    .addBearerAuth({ type: 'http', scheme: 'bearer' }, 'JWT-auth')
    .build();
  SwaggerModule.setup('api/docs', app, SwaggerModule.createDocument(app, config));
}

await app.listen(port);
```

---

## 10. SqlSdk —— 跨 ORM 的裸 SQL 抽象（重要）

当需要：
- 写**复杂联表 / GROUP_CONCAT / 窗口函数 / 多表聚合**
- 想让代码**在 Drizzle / TypeORM / Sequelize 之间复用**
- 摆脱 ORM QueryBuilder 的语法繁琐

→ 用 `SqlSdk`，三套 ORM 上 API 完全一致。

### 用法

```typescript
import { SqlSdk } from '@/sdk/sqlSdk';
// 选择对应 ORM 的 executor（详见对应 orm-* skill）
import { DrizzleSqlExecutor } from '@/sdk/sqlSdk/executor';

@Injectable()
export class UserQueryService {
  private readonly sdk = new SqlSdk(new DrizzleSqlExecutor());

  async list(page: number, pageSize: number, status: number) {
    return this.sdk.queryAndCount<{ id: number; username: string }>({
      sql: `SELECT u.id, u.username
            FROM sys_user u
            WHERE u.status = :status
            ORDER BY u.id DESC`,
      bindings: { status },
      page, pageSize,
    });
  }
}
```

### API

| 方法 | 用途 |
|------|------|
| `query<T>({ sql, bindings })` | 执行 SELECT，返回行数组 |
| `findOne<T>({ sql, bindings })` | 自动追加 `LIMIT 1`，返回首行 |
| `queryAndCount<T>({ sql, bindings, page, pageSize })` | **并行**执行 count + data，返回 `{ list, total, page, pageSize }` |

### 安全要点

- ✅ 命名参数 `:name`（推荐）或位置参数 `?`，bindings 走参数绑定
- ✅ 表名 / 列名 / 排序字段 → **代码内白名单后**再拼接，**不能**走 bindings
- ❌ `sql: \`WHERE status = ${status}\`` —— SQL 注入
- ❌ `queryAndCount` 的 SQL 中**不要**写 `LIMIT`，由 SDK 追加
- ❌ 不要拼接用户输入的 `ORDER BY`，必须白名单

### 何时不用 SqlSdk

- 简单 CRUD / 单表查询：用 ORM 原生 API（更类型安全）
- 需要 ORM 实体关系自动加载：用 ORM 原生（`relations` / `with` / `include`）

---

## 11. 安全规范

### 参数化查询（无论 ORM 还是 SqlSdk）

```typescript
// ✅ ORM 条件 API
.where('status = :status', { status })
.where(eq(sysUser.status, status))
where: { status }

// ✅ SqlSdk 命名参数
sdk.query({ sql: `WHERE status = :status`, bindings: { status } })

// ❌ 字符串拼接
.where(`status = ${status}`)
```

### 动态字段必须白名单

```typescript
const ALLOWED_SORT = ['id', 'username', 'createdAt'] as const;
const sortBy = ALLOWED_SORT.includes(query.sortBy as any) ? query.sortBy : 'id';
const sortOrder = ['ASC', 'DESC'].includes(query.sortOrder?.toUpperCase()) ? query.sortOrder.toUpperCase() : 'DESC';
```

### 速率限制（敏感接口）

```typescript
import { Throttle } from '@nestjs/throttler';

@Throttle({ default: { limit: 5, ttl: 60_000 } })
@Post('login')
async login(@Body() dto: LoginDto) { /* ... */ }
```

---

## 12. 日志

### 用 NestJS Logger（项目已用 winston 接管）

```typescript
import { Logger } from '@nestjs/common';

@Injectable()
export class UserService {
  private readonly logger = new Logger(UserService.name);

  async createUser(dto: CreateUserDto) {
    this.logger.log(`创建用户: ${dto.username}`);
    try { /* ... */ }
    catch (err) { this.logger.error('创建失败', (err as Error).stack); throw err; }
  }
}
```

| 级别 | 用途 |
|------|------|
| `error` | 异常（带 stack） |
| `warn` | 警告（重试、配额） |
| `log` | 关键业务流（登录、写操作） |
| `debug` | 仅 dev |

❌ 禁打：密码、token、身份证、手机号全段
❌ 禁用 `console.log`，统一 `Logger`
❌ 循环里打日志 → 汇总后一次输出

---

## 13. 文件上传约定

| 类型 | 路径 | 是否入库 |
|------|------|---------|
| 临时（OCR / 预览） | `temp/...` | ❌ |
| 正式 | `{biz}/{YYYYMMDD}/{uuid}` | ✅ `sys_file` 表 |

流程：前端先传到 temp → 业务确认时调"保存接口" → 后端 copy 到正式目录 + 写 file 表。

---

## 14. 配置管理

```typescript
// 用枚举集中管理 key
export enum AppConfigKey {
  databaseHost = 'DATABASE_HOST',
  jwtSecret = 'JWT_SECRET',
}

// 通过 ConfigService（或项目自带 Config 包装）取值
Config.getItem<string>(AppConfigKey.jwtSecret);
```

- ✅ 敏感值走 `.env`（不入 git），`.env.example` 列字段清单
- ❌ 严禁硬编码密钥 / URL

---

## 15. 新增 CRUD 模块 Checklist

- [ ] 在 `db/` 下定义表/实体/模型（具体方式见对应 `orm-*` skill）
- [ ] `modules/业务/dto/xxx.dto.ts`：Create / Update / Query / 输出 DTO，class + Swagger + class-validator
- [ ] `modules/业务/xxx.service.ts`：业务逻辑，注入 ORM 句柄，抛 `ServiceException`
- [ ] `modules/业务/xxx.controller.ts`：路由 + Swagger + 响应类型工具 + 守卫 + `@OperationLog`
- [ ] `modules/业务/xxx.module.ts`：注册（含 ORM 表注册）
- [ ] 在 `app.module.ts` 引入新 Module
- [ ] 列表用 `POST /list`
- [ ] 业务接口加 `@UseGuards(AdminAuthGuard)`
- [ ] 涉及租户/组织：从 `@CurrentUser()` 取 ID 注入查询条件
- [ ] 响应 DTO 排除 `password / token`
- [ ] 复杂联表查询 → 优先用 `SqlSdk`

---

## 16. 反例速查

| ❌ 错误 | ✅ 正确 |
|--------|--------|
| Service 返回 `{ code, message, data }` | 只 `return data` |
| `try/catch` 后返回 `{ success: false }` | `throw new ServiceException(...)` |
| `throw new HttpException(...)` 当业务异常用 | 用 `ServiceException` |
| Controller 写业务逻辑 | 移到 Service |
| Controller 直接访问数据库 | 必走 Service |
| `interface` 定义 DTO | `class` + Swagger 装饰器 |
| 缺 `@ApiOperation` / `@ApiResponse` | 必须补全 |
| `@Get('list')` + 复杂 Query | `@Post('list')` + `@Body()` |
| 信任前端传 `organizationId` | 从 `@CurrentUser()` 取 |
| 字符串拼 SQL（任何形式） | 参数化 / 条件 API |
| 动态排序字段直拼 | 白名单 |
| 密码明文存 | `bcrypt.hash(..., 10)` |
| 响应 DTO 含 `password` | 必须排除 |
| 临时文件直接存正式目录 | 走 temp 转正式流程 |
| `console.log` 打日志 | `Logger` |
| 跨模块直接把对方 Service 写进 providers | 在对方 Module export → 自己 Module import |
| ORM 关系层建外键约束 | 关系仅在 ORM 层声明 |

---

## 17. 何时加载哪个 ORM 子 skill

| 任务 | 加载 |
|------|------|
| 写 Drizzle schema / 用 `drizzle-orm` 写查询 / 用 `db.query.xxx` | `orm-drizzle` |
| 写 TypeORM Entity / 用 `Repository` / `QueryBuilder` | `orm-typeorm` |
| 写 Sequelize Model（`sequelize-typescript`）/ 用 Model API | `orm-sequelize` |
| 跨 ORM 通用查询 / 复杂裸 SQL | 本 skill §10 SqlSdk |
