---
name: orm-drizzle
description: |
  Drizzle ORM 通用开发规范：表定义（mysqlTable）、Relations、CRUD、JOIN、聚合、动态条件、Relational Query API、与 SqlSdk 协作。
  **触发**：项目使用 Drizzle 写 schema、查询、关联、迁移；在 NestJS 中注入 `DRIZZLE_DB`。
  **不触发**：项目使用 TypeORM / Sequelize；用对应 `orm-typeorm` / `orm-sequelize`。
  **配套**：在 NestJS 项目中同时加载 `backend-nestjs-development` 获取 Controller / Service / DTO / 异常 / 鉴权规范。
---

# Drizzle ORM 开发规范

> 本文以 **MySQL** 为例（`drizzle-orm/mysql-core` + `mysql2`）。PostgreSQL / SQLite 类型/驱动不同，写法相同。

## 0. 核心原则

1. **一表一文件**：放在 `src/db/schema/<表名>.ts`，同文件再 `export type` 推导类型与 Relations
2. **`schema/index.ts` 用 `export *` 聚合**，`drizzle(pool, { schema })` 自动收齐
3. **关系仅在 ORM 层声明**，DB 不建外键约束
4. **JSON 字段必加泛型**：`json('x').$type<T>()`
5. **频繁查询字段必加 `index()`**，唯一字段用 `.unique()`
6. **动态条件用 `SQL[]` + `and(...conditions)`**，禁止字符串拼 WHERE
7. **Service 注入 `DRIZZLE_DB`** 直接拿 `db` 句柄使用，不需要再做 DAO 抽象

---

## 1. 项目集成

### `database.ts`（连接池 + drizzle 实例 + 暴露 pool 给 SqlSdk）

```typescript
// src/db/database.ts
import * as mysql from 'mysql2/promise';
import { drizzle, MySql2Database } from 'drizzle-orm/mysql2';
import * as schema from './schema';

export type AppDatabase = MySql2Database<typeof schema>;

let _db: AppDatabase | null = null;
let _pool: mysql.Pool | null = null;

export async function createDatabase(): Promise<AppDatabase> {
  if (_db) return _db;
  _pool = mysql.createPool({
    host, port, user, password, database,
    waitForConnections: true, connectionLimit: 10,
  });
  _db = drizzle(_pool, { schema, mode: 'default' });
  return _db;
}

export function getDb(): AppDatabase {
  if (!_db) throw new Error('Database not initialized');
  return _db;
}
export function getPool(): mysql.Pool {
  if (!_pool) throw new Error('Database not initialized');
  return _pool;
}
```

### `tokens.ts` + `DrizzleModule`（@Global，提供注入 token）

```typescript
// src/db/tokens.ts
export const DRIZZLE_DB = Symbol('DRIZZLE_DB');

// src/db/drizzle.module.ts
@Global()
@Module({
  providers: [{
    provide: DRIZZLE_DB,
    inject: [ConfigService],
    useFactory: async () => createDatabase(),
  }],
  exports: [DRIZZLE_DB],
})
export class DrizzleModule implements OnModuleDestroy {
  async onModuleDestroy() { await closeDatabase(); }
}
```

### Service 注入

```typescript
import { Inject, Injectable } from '@nestjs/common';
import { DRIZZLE_DB } from '@/db/tokens';
import { AppDatabase } from '@/db/database';

@Injectable()
export class UserService {
  constructor(@Inject(DRIZZLE_DB) private readonly db: AppDatabase) {}
}
```

> **业务模块不需要在 imports 注册表**，`DrizzleModule` 是 `@Global`，注入 `DRIZZLE_DB` 即可。

---

## 2. 表定义（Schema）

### 标准模板

```typescript
// src/db/schema/sys-user.ts
import { mysqlTable, int, varchar, tinyint, datetime, timestamp, index } from 'drizzle-orm/mysql-core';
import { relations } from 'drizzle-orm';
import { sysUserRole } from './sys-user-role';

export const sysUser = mysqlTable(
  'sys_user',                                    // ← snake_case 表名
  {
    id: int('id').autoincrement().primaryKey(),
    username: varchar('username', { length: 64 }).notNull().unique(),
    password: varchar('password', { length: 255 }).notNull(),
    realName: varchar('real_name', { length: 64 }).default('').notNull(),  // ← TS 驼峰，DB 下划线
    email: varchar('email', { length: 128 }).default(''),
    status: tinyint('status').default(1).notNull(),
    lastLoginTime: datetime('last_login_time'),
    createdAt: timestamp('created_at').defaultNow().notNull(),
    updatedAt: timestamp('updated_at').defaultNow().onUpdateNow().notNull(),
  },
  (t) => ({ idxStatus: index('idx_status').on(t.status) }),
);

// 关系仅在 ORM 层声明，DB 不建外键
export const sysUserRelations = relations(sysUser, ({ many }) => ({
  userRoles: many(sysUserRole),
}));

export type SysUser = typeof sysUser.$inferSelect;
export type NewSysUser = typeof sysUser.$inferInsert;
```

### `schema/index.ts` 用 `export *` 聚合

```typescript
export * from './sys-user';
export * from './sys-user-role';
export * from './sys-role';
// ...
```

### 列类型速查

| 用途 | MySQL | PostgreSQL |
|------|-------|------------|
| 主键自增 | `int().primaryKey().autoincrement()` | `serial().primaryKey()` |
| 字符串 | `varchar({ length })` / `text()` | `varchar({ length })` / `text()` |
| 整数 | `int()` / `bigint({ mode: 'number' })` | `integer()` / `bigint()` |
| 小整 / 枚举 | `tinyint()` | `smallint()` |
| 布尔 | `boolean()` | `boolean()` |
| JSON | `json().$type<T>()` | `jsonb().$type<T>()` |
| 时间戳 | `timestamp()` / `datetime()` | `timestamp({ withTimezone: true })` |
| 小数 | `decimal({ precision, scale })` | `numeric({ precision, scale })` |

---

## 3. Relations（开启 Relational Query API）

```typescript
// 一对多
export const sysUserRelations = relations(sysUser, ({ many }) => ({
  userRoles: many(sysUserRole),
}));

// 多对一（中间表）
export const sysUserRoleRelations = relations(sysUserRole, ({ one }) => ({
  user: one(sysUser, { fields: [sysUserRole.userId], references: [sysUser.id] }),
  role: one(sysRole, { fields: [sysUserRole.roleId], references: [sysRole.id] }),
}));
```

要点：
- ✅ 必须 `export`，且被 `schema/index.ts` 收集
- ✅ 双向关系两端都要声明
- ✅ 命名：`表名 + Relations`

---

## 4. 常用 import

```typescript
import {
  eq, ne, gt, gte, lt, lte, and, or, not,
  like, ilike, inArray, notInArray,
  isNull, isNotNull, between, exists,
  desc, asc, sql,
  type SQL,
} from 'drizzle-orm';
```

---

## 5. CRUD

### 查询单条

```typescript
const [user] = await this.db.select().from(sysUser).where(eq(sysUser.id, id)).limit(1);
if (!user) throw new NotFoundException('用户不存在');
```

### 插入（MySQL：`insertId` 在 result[0]）

```typescript
const result = await this.db.insert(sysUser).values({
  username, password: hashed, realName: '', status: 1,
});
const insertId = Number((result as any)[0]?.insertId ?? (result as any).insertId);
```

> PostgreSQL/SQLite 改用 `.returning()`：`const [row] = await db.insert(t).values({...}).returning();`

### 批量插入

```typescript
await this.db.insert(sysUserRole).values(
  roleIds.map((roleId) => ({ userId, roleId })),
);
```

### 更新

```typescript
await this.db.update(sysUser).set({ status: 2 }).where(eq(sysUser.id, id));
```

### 删除

```typescript
await this.db.delete(sysUserRole).where(eq(sysUserRole.userId, userId));
```

### Upsert

```typescript
// MySQL
await this.db.insert(sysUser).values({...})
  .onDuplicateKeyUpdate({ set: { email, updatedAt: new Date() } });

// PostgreSQL
await db.insert(sysUser).values({...})
  .onConflictDoUpdate({ target: sysUser.id, set: { email } });
```

---

## 6. 多表 JOIN（手写）

```typescript
const rows = await this.db
  .select({
    user: sysUser,
    roleIds: sql<string | null>`GROUP_CONCAT(${sysRole.id})`.as('roleIds'),
    roleNames: sql<string | null>`GROUP_CONCAT(${sysRole.roleName})`.as('roleNames'),
  })
  .from(sysUser)
  .leftJoin(sysUserRole, eq(sysUserRole.userId, sysUser.id))
  .leftJoin(sysRole, eq(sysRole.id, sysUserRole.roleId))
  .where(whereClause)
  .groupBy(sysUser.id)
  .orderBy(desc(sysUser.id))
  .limit(pageSize)
  .offset(offset);
```

---

## 7. 动态条件

```typescript
import { and, eq, like, type SQL } from 'drizzle-orm';

const conditions: SQL[] = [];
if (query.username) conditions.push(like(sysUser.username, `%${query.username}%`));
if (query.status !== undefined && query.status !== null) {
  conditions.push(eq(sysUser.status, query.status));
}
const whereClause = conditions.length > 0 ? and(...conditions) : undefined;

const rows = await this.db.select().from(sysUser).where(whereClause);
```

要点：
- ✅ 类型用 `SQL[]`，不用 `any[]`
- ✅ 数量为 0 时传 `undefined` 让 Drizzle 跳过 WHERE
- ✅ 多租户字段（如 `organizationId`）作为第一个条件强制加入

---

## 8. 分页（手写 count + data）

```typescript
async getUserList(query: QueryUserDto) {
  const page = query.page || 1;
  const pageSize = query.pageSize || 10;

  const conditions: SQL[] = [];
  if (query.status !== undefined) conditions.push(eq(sysUser.status, query.status));
  const where = conditions.length ? and(...conditions) : undefined;

  // count（独立查主表，避免 JOIN 后行数膨胀）
  const [c] = await this.db
    .select({ count: sql<number>`count(*)` })
    .from(sysUser)
    .where(where);
  const total = Number(c?.count ?? 0);

  // data
  const list = await this.db
    .select().from(sysUser).where(where)
    .orderBy(desc(sysUser.id))
    .limit(pageSize).offset((page - 1) * pageSize);

  return { list, total, page, pageSize };
}
```

> 复杂联表分页 → 用 `SqlSdk.queryAndCount`，省掉手写 count（见 §11）。

---

## 9. Relational Query API（自动 JOIN）

前提：Relations 已在 schema 中注册。

```typescript
const rows = await this.db.query.sysUser.findMany({
  where: whereClause,
  orderBy: [desc(sysUser.id)],
  limit: pageSize,
  offset,
  with: {
    userRoles: {
      with: { role: true },
      // 可对关联表加 where / limit / orderBy
    },
  },
  columns: { id: true, username: true, password: false }, // 字段裁剪
});
```

| 场景 | 推荐 |
|------|------|
| 简单一对多 / 一对一 | Relational Query（`db.query.xxx`） |
| 复杂 JOIN + GROUP BY + 聚合 | 手写 `select().from().leftJoin()` 或 SqlSdk |
| 分页 + 关联（且需精确 total） | 手写（count 单独查主表） |

---

## 10. 原生 SQL

```typescript
import { sql } from 'drizzle-orm';

// ✅ 模板字符串自动参数化
const rows = await this.db.execute(
  sql`SELECT * FROM sys_user WHERE username = ${name}`,
);

// ✅ 用作 select 表达式
.select({
  id: sysUser.id,
  fullName: sql<string>`concat(${sysUser.firstName}, ' ', ${sysUser.lastName})`,
})

// ❌ sql.raw() 拼用户输入
const q = `WHERE name = '${userInput}'`;
db.execute(sql.raw(q));
```

`sql.raw` 仅用于纯静态 SQL 或**白名单后**的字段名。

---

## 11. 配合 SqlSdk（推荐复杂查询）

```typescript
import { SqlSdk } from '@/sdk/sqlSdk';
import { DrizzleSqlExecutor } from '@/sdk/sqlSdk/executor';

@Injectable()
export class UserQueryService {
  private readonly sdk = new SqlSdk(new DrizzleSqlExecutor());

  async list(page: number, pageSize: number, status: number) {
    return this.sdk.queryAndCount<{ id: number; username: string; roleIds: string }>({
      sql: `SELECT u.id, u.username,
                   GROUP_CONCAT(r.id)        AS roleIds,
                   GROUP_CONCAT(r.role_name) AS roleNames
            FROM sys_user u
            LEFT JOIN sys_user_role ur ON ur.user_id = u.id
            LEFT JOIN sys_role r       ON r.id = ur.role_id
            WHERE u.status = :status
            GROUP BY u.id
            ORDER BY u.id DESC`,
      bindings: { status },
      page, pageSize,
    });
  }
}
```

> `DrizzleSqlExecutor` 直接走底层 mysql2 pool（最高效）。

---

## 12. 类型工具

```typescript
type SysUserRow = typeof sysUser.$inferSelect;
type NewSysUser = typeof sysUser.$inferInsert;

// 业务方法签名建议**仍用业务 DTO**，避免 Drizzle 类型四处扩散
async findById(id: number): Promise<UserDto | null> {
  const [r] = await this.db.select().from(sysUser).where(eq(sysUser.id, id)).limit(1);
  return r ?? null;
}
```

---

## 13. 事务

```typescript
await this.db.transaction(async (tx) => {
  await tx.delete(sysUserRole).where(eq(sysUserRole.userId, userId));
  if (roleIds.length > 0) {
    await tx.insert(sysUserRole).values(roleIds.map((roleId) => ({ userId, roleId })));
  }
});
```

要点：
- ✅ 事务内必须用 `tx`，不能再用 `this.db`
- ✅ 抛异常 = 自动回滚；不要 `try/catch` 然后吞掉
- ❌ 不要在事务内做耗时 I/O（HTTP / Redis 大量操作）
- ❌ 嵌套调用其他方法时，要把 `tx` 透传下去

---

## 14. 迁移（drizzle-kit）

```typescript
// drizzle.config.ts
import type { Config } from 'drizzle-kit';
export default {
  schema: './src/db/schema/index.ts',
  out: './src/db/migrations',
  dialect: 'mysql',
  dbCredentials: { host, user, password, database },
} satisfies Config;
```

```bash
npx drizzle-kit generate    # 生成迁移 SQL（生产用）
npx drizzle-kit push        # 直接 push 到 DB（仅开发）
npx drizzle-kit studio      # 可视化
```

- ✅ 生产用 `generate`，迁移文件入 git
- ❌ 生产**不用** `push`
- ❌ 不要手改已发布的迁移文件

---

## 15. 反例速查

| ❌ | ✅ |
|----|----|
| 手维护 `dbSchema` 对象 | `export *` 让 drizzle 自动收 |
| `conditions: any[]` | `conditions: SQL[]` |
| `sql.raw()` 拼用户输入 | `sql\`...${value}...\`` 模板（自动参数化） |
| `json('x')` 不带泛型 | `json('x').$type<T>()` |
| 频繁查询字段无索引 | `index('idx_x').on(t.x)` |
| 关系层建外键 | 关系只声明在 schema |
| Relations 没 export | 必须 export，且被 `schema/index.ts` 收 |
| 事务内继续 `this.db.xxx` | 必须 `tx.xxx` |
| `db.transaction` 包裹耗时 I/O | 事务外完成 |
| 复杂 JOIN 全用 select API | 复杂场景优先 SqlSdk |
| 生产 `drizzle-kit push` | 生产用 `generate` + 迁移文件 |

---

## 16. 新增一张表 Checklist

- [ ] `db/schema/<表名>.ts` 定义表（snake_case 表名 + 字段，TS 驼峰命名）
- [ ] 频繁查询字段加 `index()`、唯一字段加 `.unique()`
- [ ] 枚举/状态字段 JSDoc 注释每个值含义
- [ ] JSON 字段加 `.$type<T>()`
- [ ] 如需关联查询，定义 `relations()` 并 `export`
- [ ] 在 `db/schema/index.ts` 加 `export * from './<表名>'`
- [ ] `export type` 导出 `$inferSelect` / `$inferInsert` 推导类型
- [ ] 业务侧 Service 直接 `@Inject(DRIZZLE_DB) db: AppDatabase` 使用
- [ ] 复杂查询优先评估能否用 `SqlSdk`
- [ ] 生成迁移：`npx drizzle-kit generate`，提交 SQL 文件

---

## 17. 官方资源

- 文档：https://orm.drizzle.team/docs/overview
- API 速查：https://orm.drizzle.team/docs/select
- Relational Query：https://orm.drizzle.team/docs/rqb
