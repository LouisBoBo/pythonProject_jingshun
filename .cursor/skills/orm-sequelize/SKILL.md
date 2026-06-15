---
name: orm-sequelize
description: |
  Sequelize（基于 sequelize-typescript）通用开发规范：Model 定义、查询 API、关联（BelongsToMany / HasMany 等）、动态条件、分页、事务、原生 SQL、与 SqlSdk 协作。
  **触发**：项目使用 Sequelize（搭配 `@nestjs/sequelize` + `sequelize-typescript`）写 Model、查询、关联、迁移；通过 `@InjectModel` 注入。
  **不触发**：项目使用 Drizzle / TypeORM；用对应 `orm-drizzle` / `orm-typeorm`。
  **配套**：在 NestJS 项目中同时加载 `backend-nestjs-development`。
---

# Sequelize 开发规范（sequelize-typescript）

> 本文以 **MySQL** 为例，配合 `sequelize-typescript` 装饰器写 Model。

## 0. 核心原则

1. **一表一文件**：放在 `src/db/models/<表名>.model.ts`
2. **`@Table({ tableName: 'snake_case', underscored: true })`**：表名显式 snake_case，列名自动驼峰转下划线（仍建议关键字段显式 `field: 'xxx'`）
3. **关系仅在 ORM 层声明**，DB 不建外键约束（sequelize-typescript 默认就不建，无需额外配置）
4. **Service 通过 `@InjectModel(Model)` 注入**，类型 `typeof Model`
5. **简单查询用 Model API；复杂联表 / 聚合用 `sequelize.query` + replacements，或 SqlSdk**
6. **动态 WHERE 用 `WhereOptions` + `Op.xxx` 操作符**，参数化绑定
7. **`models/index.ts` 用 `export *` 聚合**，统一在 `SequelizeCoreModule` 注册

---

## 1. 项目集成

### 依赖

```bash
yarn add @nestjs/sequelize sequelize sequelize-typescript mysql2
yarn add -D @types/sequelize @types/validator
```

### `SequelizeCoreModule`（@Global）

```typescript
@Global()
@Module({
  imports: [
    SequelizeModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: () => ({
        dialect: 'mysql' as const,
        host, port, username, password, database,
        models: MODELS,           // ← 集中注册所有 Model
        autoLoadModels: false,
        synchronize: false,       // ← 生产关闭
        timezone: '+08:00',
      }),
    }),
    SequelizeModule.forFeature(MODELS),
  ],
  exports: [SequelizeModule],
})
export class SequelizeCoreModule {}
```

### 业务 Module 仍要 `forFeature` 注册需要的 Model

```typescript
@Module({
  imports: [SequelizeModule.forFeature([SysUser, SysUserRole])],
  controllers: [UserController],
  providers: [UserService],
})
export class UserModule {}
```

### Service 注入

```typescript
@Injectable()
export class UserService {
  constructor(
    @InjectModel(SysUser) private readonly userModel: typeof SysUser,
    @InjectModel(SysUserRole) private readonly userRoleModel: typeof SysUserRole,
  ) {}
}
```

> 拿底层 `Sequelize` 实例：`this.userModel.sequelize!`，用于裸 SQL / 事务。

---

## 2. Model 定义

### 标准模板

```typescript
// src/db/models/sys-user.model.ts
import {
  Table, Column, Model, DataType,
  PrimaryKey, AutoIncrement, CreatedAt, UpdatedAt,
  Unique, Default, AllowNull,
  BelongsToMany,
} from 'sequelize-typescript';
import { SysRole } from './sys-role.model';
import { SysUserRole } from './sys-user-role.model';

@Table({
  tableName: 'sys_user',           // ← 显式 snake_case
  timestamps: true,                // 自动维护 createdAt / updatedAt
  underscored: true,               // 列名自动驼峰转下划线（real_name 等）
  indexes: [{ name: 'idx_status', fields: ['status'] }],
})
export class SysUser extends Model<SysUser> {
  @PrimaryKey @AutoIncrement
  @Column(DataType.INTEGER)
  id: number;

  @Unique @AllowNull(false)
  @Column(DataType.STRING(64))
  username: string;

  @AllowNull(false)
  @Column(DataType.STRING(255))
  password: string;

  @AllowNull(false) @Default('')
  @Column({ type: DataType.STRING(64), field: 'real_name' })  // ← 关键字段显式 field
  realName: string;

  @Default('')
  @Column(DataType.STRING(128))
  email: string;

  @AllowNull(false) @Default(1)
  @Column(DataType.TINYINT)
  status: number;

  @AllowNull(true)
  @Column({ type: DataType.DATE, field: 'last_login_time' })
  lastLoginTime: Date | null;

  @CreatedAt @Column({ field: 'created_at' })
  createdAt: Date;

  @UpdatedAt @Column({ field: 'updated_at' })
  updatedAt: Date;

  /**
   * 关系仅在 ORM 层声明，DB 不建外键
   * 多对多走中间表，sequelize-typescript 自动 JOIN
   */
  @BelongsToMany(() => SysRole, () => SysUserRole, 'userId', 'roleId')
  roles?: SysRole[];
}
```

### 中间表（必须用 `@ForeignKey` 让 BelongsToMany 识别两端）

```typescript
@Table({
  tableName: 'sys_user_role',
  timestamps: true, updatedAt: false, underscored: true,
  indexes: [
    { name: 'idx_ur_user', fields: ['user_id'] },
    { name: 'idx_ur_role', fields: ['role_id'] },
  ],
})
export class SysUserRole extends Model<SysUserRole> {
  @PrimaryKey @AutoIncrement
  @Column(DataType.INTEGER)
  id: number;

  @ForeignKey(() => SysUser)
  @AllowNull(false)
  @Column({ type: DataType.INTEGER, field: 'user_id' })
  userId: number;

  @ForeignKey(() => SysRole)
  @AllowNull(false)
  @Column({ type: DataType.INTEGER, field: 'role_id' })
  roleId: number;

  @CreatedAt @Column({ field: 'created_at' })
  createdAt: Date;
}
```

### 列类型速查

| 用途 | 写法 |
|------|------|
| 主键自增 | `@PrimaryKey @AutoIncrement @Column(DataType.INTEGER)` |
| 字符串 | `@Column(DataType.STRING(64))` |
| 文本 | `@Column(DataType.TEXT)` |
| 整数 | `@Column(DataType.INTEGER)` / `BIGINT` |
| 小整 / 枚举 | `@Column(DataType.TINYINT)` |
| 布尔 | `@Column(DataType.BOOLEAN)` |
| JSON | `@Column(DataType.JSON)` |
| 日期 | `@Column(DataType.DATE)` |
| 小数 | `@Column(DataType.DECIMAL(10, 2))` |

### 关系装饰器

| 关系 | 写法 |
|------|------|
| 一对一 | `@HasOne(() => Y)` / `@BelongsTo(() => X)` |
| 一对多 | `@HasMany(() => Y)` / `@BelongsTo(() => X)` |
| 多对多 | `@BelongsToMany(() => Y, () => XY, 'xId', 'yId')` |

### `models/index.ts` 用 `export *` 聚合

```typescript
export * from './sys-user.model';
export * from './sys-user-role.model';
export * from './sys-role.model';
// ...
```

---

## 3. Model 基础 CRUD

```typescript
// 查单条
const user = await this.userModel.findByPk(id);
if (!user) throw new NotFoundException('用户不存在');

// 字段裁剪
const exists = await this.userModel.findOne({
  where: { username: dto.username },
  attributes: ['id'],
});

// 创建
const saved = await this.userModel.create({ username, password: hashed } as any);
//                                                                       ^^^ 类型常需 as any
// 类型解决方案：泛型用 Model<Attrs, CreationAttrs> 拆开声明（项目可统一封装）

// 批量创建
await this.userRoleModel.bulkCreate(
  roleIds.map((roleId) => ({ userId, roleId })) as any,
);

// 更新（按条件）
await this.userModel.update({ status: 0 }, { where: { id } });

// 删除（按条件）
await this.userRoleModel.destroy({ where: { userId: id } });
await this.userModel.destroy({ where: { id } });
```

### 实例 vs 静态

```typescript
// 实例方法
const user = await this.userModel.findByPk(id);
user!.status = 0;
await user!.save();

// 静态方法（推荐，避免先查后写两次 SQL）
await this.userModel.update({ status: 0 }, { where: { id } });
```

### `toJSON()`

```typescript
const json = user.toJSON();   // 拿到纯对象（去掉 Sequelize 实例方法）
const { password, ...safe } = json;
```

---

## 4. 动态条件（WhereOptions + Op）

```typescript
import { Op, WhereOptions } from 'sequelize';

const where: WhereOptions = {};
if (query.username) (where as any).username = { [Op.like]: `%${query.username}%` };
if (query.status !== undefined) (where as any).status = query.status;
if (query.ids?.length) (where as any).id = { [Op.in]: query.ids };
if (query.startAt) (where as any).createdAt = { [Op.gte]: query.startAt };

const list = await this.userModel.findAll({
  where,
  order: [['id', 'DESC']],
  limit: pageSize,
  offset: (page - 1) * pageSize,
});
```

### 常用 `Op` 操作符

| 用途 | `Op.xxx` |
|------|----------|
| 模糊 | `Op.like`，`Op.notLike` |
| 包含 | `Op.in`，`Op.notIn` |
| 范围 | `Op.between` |
| 大小 | `Op.gt` / `Op.gte` / `Op.lt` / `Op.lte` |
| 不等 | `Op.ne` |
| 为空 | `Op.is`（搭配 `null`） |
| 与/或 | `Op.and`，`Op.or` |

```typescript
where: {
  [Op.or]: [
    { username: { [Op.like]: `%${kw}%` } },
    { realName: { [Op.like]: `%${kw}%` } },
  ],
}
```

---

## 5. 分页（findAndCountAll）

```typescript
const { rows, count } = await this.userModel.findAndCountAll({
  where,
  order: [['id', 'DESC']],
  limit: pageSize,
  offset: (page - 1) * pageSize,
});
return { list: rows, total: count, page, pageSize };
```

### 关联查询的分页（必须 `distinct: true`）

```typescript
const { rows, count } = await this.userModel.findAndCountAll({
  where,
  include: [{ model: SysRole, through: { attributes: [] } }],
  order: [['id', 'DESC']],
  limit: pageSize,
  offset: (page - 1) * pageSize,
  distinct: true,         // ← JOIN 后必须 distinct，否则 count 翻倍
});
```

> `through: { attributes: [] }` 表示中间表字段不返回。

---

## 6. 关联查询（include）

```typescript
const rows = await this.userModel.findAll({
  where: { status: 1 },
  include: [
    { model: SysRole, through: { attributes: [] } },
    // 也可以嵌套
    // { model: Org, include: [{ model: Tag }] },
  ],
});
```

访问关联：

```typescript
const roles = (user as any).roles as SysRole[];   // 类型常需断言
```

---

## 7. 原生 SQL（`sequelize.query`）

Sequelize 自带支持，**命名参数 `:name` 用 `replacements`**：

```typescript
import { QueryTypes } from 'sequelize';

const sequelize = this.userModel.sequelize!;
const rows = await sequelize.query<{ id: number; username: string }>(
  `SELECT id, username FROM sys_user WHERE status = :status`,
  {
    replacements: { status: 1 },
    type: QueryTypes.SELECT,
  },
);
```

要点：
- ✅ 始终用 `replacements` 参数化绑定
- ✅ `type: QueryTypes.SELECT` 让返回值是行数组（不是 `[rows, metadata]`）
- ❌ 严禁拼接 SQL：`` `WHERE status = ${status}` ``

> Sequelize 原生 SQL 返回的是 **snake_case 字段名**，需要在代码里手动映射到 camelCase。

---

## 8. 配合 SqlSdk（推荐复杂查询）

```typescript
import { SqlSdk } from '@/sdk/sqlSdk';
import { SequelizeSqlExecutor } from '@/sdk/sqlSdk/executor';

@Injectable()
export class UserQueryService {
  private readonly sdk: SqlSdk;

  constructor(@InjectModel(SysUser) userModel: typeof SysUser) {
    this.sdk = new SqlSdk(new SequelizeSqlExecutor(userModel.sequelize!));
  }

  async list(page: number, pageSize: number, status: number) {
    return this.sdk.queryAndCount<{ id: number; username: string }>({
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

> 复杂联表查询比手写 `findAll + include` 更直观，类型也更可控（自己声明返回行类型）。

---

## 9. 事务

### 推荐：`sequelize.transaction`（自动 commit / rollback）

```typescript
@Injectable()
export class OrderService {
  constructor(@InjectModel(Order) private orderModel: typeof Order) {}

  async createOrder(dto) {
    const sequelize = this.orderModel.sequelize!;
    return sequelize.transaction(async (t) => {
      const order = await this.orderModel.create({ ... }, { transaction: t });
      await Stock.decrement('count', { by: 1, where: { skuId: dto.skuId }, transaction: t });
      return order;
    });
  }
}
```

要点：
- ✅ 事务内**所有写操作必须传 `{ transaction: t }`**，否则不在事务里
- ✅ 抛异常自动回滚
- ❌ 不要在事务内做耗时 I/O
- ❌ 嵌套调用其他方法时把 `t` 透传下去

### 手动控制（不推荐，但有时需要）

```typescript
const t = await sequelize.transaction();
try {
  await Order.create({ ... }, { transaction: t });
  await t.commit();
} catch (err) {
  await t.rollback();
  throw err;
}
```

---

## 10. 迁移（sequelize-cli）

```bash
# 安装
yarn add -D sequelize-cli

# 生成迁移
npx sequelize-cli migration:generate --name add-user-status

# 执行
npx sequelize-cli db:migrate

# 回滚
npx sequelize-cli db:migrate:undo
```

- ✅ `synchronize: false` 是铁律
- ✅ 迁移 SQL 入 git
- ❌ 不要修改已发布的迁移文件

---

## 11. 反例速查

| ❌ | ✅ |
|----|----|
| `synchronize: true` | 永远 `false`，用 migration |
| `@Table` 不写 `tableName` | 显式 `tableName: 'snake_case'` |
| 关键字段不写 `field` 靠 `underscored` 推断 | 显式 `@Column({ field: 'real_name' })` |
| 拼接 SQL 进 `sequelize.query` | 走 `replacements` 命名参数 |
| 关联查询 `findAndCountAll` 不加 `distinct: true` | 必须加，否则 count 翻倍 |
| `findOne` 后 `.update` 走两步 | 直接 `Model.update({...}, { where })` |
| 事务内忘传 `{ transaction: t }` | 所有写操作必须传 |
| 复杂 JOIN 全用 `include` 嵌套 | 优先 SqlSdk 或裸 SQL |
| 用 `@HasOne / @BelongsTo` 时 DB 建外键 | sequelize-typescript 默认不建，不用额外操作 |
| 时间字段手维护 `createdAt` | `@CreatedAt / @UpdatedAt` |

---

## 12. 新增一张表 Checklist

- [ ] `db/models/<表名>.model.ts` 定义 Model（`@Table({ tableName, underscored: true })`）
- [ ] 关键字段显式 `@Column({ field: 'snake_name' })`
- [ ] 索引在 `@Table.indexes` 里声明
- [ ] `@CreatedAt / @UpdatedAt` 自动维护时间
- [ ] 关系装饰器（`@BelongsToMany / @HasMany / @BelongsTo`）
- [ ] 中间表的外键字段加 `@ForeignKey`
- [ ] 在 `db/models/index.ts` 加 `export * from './<表名>.model'`
- [ ] 在 `SequelizeCoreModule` 的 `MODELS` 数组登记
- [ ] 业务 Module 用 `SequelizeModule.forFeature([X])` 注册
- [ ] Service 用 `@InjectModel(X) model: typeof X` 注入
- [ ] 复杂查询优先评估 SqlSdk

---

## 13. 官方资源

- Sequelize 文档：https://sequelize.org/docs/v6/
- sequelize-typescript：https://github.com/RobinBuschmann/sequelize-typescript
- @nestjs/sequelize：https://docs.nestjs.com/techniques/database#sequelize-integration
