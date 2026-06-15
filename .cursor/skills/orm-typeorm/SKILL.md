---
name: orm-typeorm
description: |
  TypeORM 通用开发规范：Entity 定义、Repository / QueryBuilder、关联关系（OneToMany/ManyToOne 等）、动态条件、分页、事务、与 SqlSdk 协作。
  **触发**：项目使用 TypeORM 写 Entity、查询、关联、迁移；在 NestJS 中通过 `@InjectRepository` 注入。
  **不触发**：项目使用 Drizzle / Sequelize；用对应 `orm-drizzle` / `orm-sequelize`。
  **配套**：在 NestJS 项目中同时加载 `backend-nestjs-development`。
---

# TypeORM 开发规范

> 本文以 **MySQL** 为例，PostgreSQL 写法相同（仅类型/选项略有差异）。

## 0. 核心原则

1. **一表一文件**：放在 `src/db/entities/<表名>.entity.ts`
2. **数据库列名 `snake_case`，TS 属性 `camelCase`**：靠 `@Column({ name: 'real_name' })` 显式映射
3. **关系仅在 ORM 层声明**：`createForeignKeyConstraints: false`，DB 不建外键
4. **`@Entity('表名')` 必须显式写表名**，不靠默认推导
5. **Service 通过 `@InjectRepository(Entity)` 注入 `Repository<Entity>`**
6. **简单查询用 Repository API；复杂 JOIN 用 `createQueryBuilder` 或 SqlSdk**
7. **动态 WHERE 用 `FindOptionsWhere<T>` 拼字段；复杂条件用 QueryBuilder `andWhere`**
8. **`synchronize: false`**：生产用 migration，**禁止** `synchronize: true`

---

## 1. 项目集成

### `data-source.ts`（脚本/迁移用）

```typescript
import { DataSource, DataSourceOptions } from 'typeorm';
import * as path from 'path';

export const dataSourceOptions: DataSourceOptions = {
  type: 'mysql',
  host: process.env.DATABASE_HOST,
  port: Number(process.env.DATABASE_PORT),
  username: process.env.DATABASE_USERNAME,
  password: process.env.DATABASE_PASSWORD,
  database: process.env.DATABASE_NAME,
  entities: [path.join(__dirname, 'entities', '*.entity.{ts,js}')],
  synchronize: false,
  logging: false,
  charset: 'utf8mb4_unicode_ci',
  timezone: '+08:00',
};
export const AppDataSource = new DataSource(dataSourceOptions);
```

### `TypeOrmCoreModule`（@Global，统一注册所有 Entity + DataSource）

```typescript
@Global()
@Module({
  imports: [
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (configService) => ({
        type: 'mysql', host, port, username, password, database,
        entities: ENTITIES,
        synchronize: false,
      }),
    }),
    TypeOrmModule.forFeature(ENTITIES),
  ],
  exports: [TypeOrmModule],
})
export class TypeOrmCoreModule {}
```

### 业务 Module 仍要 `forFeature` 注册需要的 Entity

```typescript
@Module({
  imports: [TypeOrmModule.forFeature([SysUser, SysUserRole])],
  controllers: [UserController],
  providers: [UserService],
})
export class UserModule {}
```

> 即使全局 module 已经 `forFeature` 一次，业务 module 仍需再注册自己用到的 Entity，否则 `@InjectRepository` 报"找不到 Repository"。

### Service 注入

```typescript
@Injectable()
export class UserService {
  constructor(
    @InjectRepository(SysUser) private readonly userRepo: Repository<SysUser>,
    @InjectRepository(SysUserRole) private readonly userRoleRepo: Repository<SysUserRole>,
  ) {}
}
```

---

## 2. Entity 定义

### 标准模板

```typescript
// src/db/entities/sys-user.entity.ts
import {
  Entity, PrimaryGeneratedColumn, Column,
  CreateDateColumn, UpdateDateColumn, Index,
  OneToMany,
} from 'typeorm';
import { SysUserRole } from './sys-user-role.entity';

@Entity('sys_user')                  // ← 显式 snake_case 表名
@Index('idx_status', ['status'])     // ← 索引
export class SysUser {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ type: 'varchar', length: 64, unique: true })
  username: string;

  @Column({ type: 'varchar', length: 255 })
  password: string;

  @Column({ name: 'real_name', type: 'varchar', length: 64, default: '' })
  realName: string;                  // ← TS 驼峰，DB 下划线

  @Column({ type: 'varchar', length: 128, default: '', nullable: true })
  email: string;

  @Column({ type: 'tinyint', default: 1 })
  status: number;

  @Column({ name: 'last_login_time', type: 'datetime', nullable: true })
  lastLoginTime: Date | null;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  /**
   * 关系仅在 ORM 层声明，DB 不建外键
   * 多对多通常用 OneToMany + ManyToOne 模拟，避免 @ManyToMany 强行接管中间表
   */
  @OneToMany(() => SysUserRole, (ur) => ur.user, {
    createForeignKeyConstraints: false,
  })
  userRoles?: SysUserRole[];
}
```

### 中间表

```typescript
@Entity('sys_user_role')
@Index('idx_ur_user', ['userId'])
@Index('idx_ur_role', ['roleId'])
export class SysUserRole {
  @PrimaryGeneratedColumn()
  id: number;

  @Column({ name: 'user_id', type: 'int' })
  userId: number;

  @Column({ name: 'role_id', type: 'int' })
  roleId: number;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @ManyToOne(() => SysUser, (u) => u.userRoles, { createForeignKeyConstraints: false })
  @JoinColumn({ name: 'user_id' })
  user?: SysUser;

  @ManyToOne(() => SysRole, { createForeignKeyConstraints: false })
  @JoinColumn({ name: 'role_id' })
  role?: SysRole;
}
```

### 列类型速查

| 用途 | 写法 |
|------|------|
| 主键自增 | `@PrimaryGeneratedColumn()` |
| 字符串 | `@Column({ type: 'varchar', length: 64 })` |
| 文本 | `@Column({ type: 'text' })` |
| 整数 | `@Column({ type: 'int' })` / `bigint` |
| 小整 / 枚举 | `@Column({ type: 'tinyint' })` |
| 布尔 | `@Column({ type: 'boolean' })` |
| JSON | `@Column({ type: 'json' })` |
| 时间戳 | `@CreateDateColumn() / @UpdateDateColumn()` |
| 日期 | `@Column({ type: 'datetime', nullable: true })` |
| 小数 | `@Column({ type: 'decimal', precision: 10, scale: 2 })` |

### 关系装饰器

| 关系 | 写法 |
|------|------|
| 一对一 | `@OneToOne(() => X) @JoinColumn()` |
| 多对一 | `@ManyToOne(() => X, (x) => x.ys) @JoinColumn({ name: 'x_id' })` |
| 一对多 | `@OneToMany(() => Y, (y) => y.x)` |
| 多对多 | 推荐 `OneToMany + ManyToOne` 走中间表，避免 `@ManyToMany` 接管中间表 |

> 所有关系都加 `{ createForeignKeyConstraints: false }`，不在 DB 层建外键。

---

## 3. Repository 基础 CRUD

```typescript
// 查单条
const user = await this.userRepo.findOne({
  where: { id },
  select: ['id', 'username'],   // 字段裁剪
});
if (!user) throw new NotFoundException('用户不存在');

// 查存在性
const exists = await this.userRepo.findOne({
  where: { username: dto.username },
  select: ['id'],
});
if (exists) throw new ServiceException('用户名已存在');

// 创建
const entity = this.userRepo.create({ username, password: hashed });
const saved = await this.userRepo.save(entity);

// 更新
await this.userRepo.update(id, { status: 0 });

// 删除
await this.userRepo.delete(id);
await this.userRoleRepo.delete({ userId: id });   // 按条件删
```

### `save` vs `insert` vs `update`

| 方法 | 是否触发 hooks | 是否返回完整实体 | 适用 |
|------|--------------|---------------|------|
| `save(entity)` | ✅ | ✅ | 创建 / 全量更新 |
| `insert(data)` | ❌ | 只返回 `insertId` | 批量插入、性能优先 |
| `update(id, partial)` | ❌ | 只返回 `affected` 数 | 局部更新 |

---

## 4. 动态条件（FindOptionsWhere）

```typescript
import { Like, In, Between, FindOptionsWhere } from 'typeorm';

const where: FindOptionsWhere<SysUser> = {};
if (query.username) where.username = Like(`%${query.username}%`);
if (query.status !== undefined) where.status = query.status;
if (query.ids?.length) where.id = In(query.ids);

const list = await this.userRepo.find({
  where,
  order: { id: 'DESC' },
  take: pageSize,
  skip: (page - 1) * pageSize,
});
```

### 常用操作符

| 用途 | 写法 |
|------|------|
| 模糊 | `Like('%xx%')` |
| 包含 | `In([1, 2])` |
| 范围 | `Between(start, end)` |
| 不等 | `Not(value)` |
| 大小 | `MoreThan(n)` / `LessThan(n)` / `MoreThanOrEqual` |
| 为空 | `IsNull()` |

---

## 5. 分页（findAndCount）

```typescript
const [list, total] = await this.userRepo.findAndCount({
  where,
  order: { id: 'DESC' },
  take: pageSize,
  skip: (page - 1) * pageSize,
});
return { list, total, page, pageSize };
```

### 关联查询的分页（注意 `distinct`）

```typescript
const [rows, total] = await this.userRepo.findAndCount({
  where,
  relations: ['userRoles', 'userRoles.role'],   // 两层关系
  order: { id: 'DESC' },
  take: pageSize,
  skip: (page - 1) * pageSize,
});
```

---

## 6. QueryBuilder（复杂 JOIN）

```typescript
const qb = this.userRepo
  .createQueryBuilder('u')
  .leftJoin(SysUserRole, 'ur', 'ur.user_id = u.id')
  .leftJoin(SysRole, 'r', 'r.id = ur.role_id')
  .addSelect('GROUP_CONCAT(r.id)', 'roleIds')
  .addSelect('GROUP_CONCAT(r.role_name)', 'roleNames')
  .groupBy('u.id')
  .orderBy('u.id', 'DESC')
  .limit(pageSize)
  .offset((page - 1) * pageSize);

if (query.username) qb.andWhere('u.username LIKE :u', { u: `%${query.username}%` });
if (query.status !== undefined) qb.andWhere('u.status = :s', { s: query.status });

// 拿到 entity + 额外原始列
const { entities, raw } = await qb.getRawAndEntities<{
  roleIds: string | null;
  roleNames: string | null;
}>();

// count 单独查（避免 JOIN 后行数膨胀，QueryBuilder 的 getCount 在 GROUP BY 时也不准）
const total = await this.userRepo.count({ where: countWhere });
```

### `getMany` / `getOne` / `getRawMany` / `getManyAndCount`

| 方法 | 返回 |
|------|------|
| `getOne()` / `getMany()` | Entity 实例 |
| `getRawOne()` / `getRawMany()` | 原始字段对象（含 `addSelect` 的列） |
| `getRawAndEntities()` | 同时拿 entity 和 raw |
| `getManyAndCount()` | `[entities, total]`（GROUP BY 场景下 count 可能不准，建议单独查） |

---

## 7. 配合 SqlSdk（推荐复杂查询）

```typescript
import { InjectDataSource } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';
import { SqlSdk } from '@/sdk/sqlSdk';
import { TypeOrmSqlExecutor } from '@/sdk/sqlSdk/executor';

@Injectable()
export class UserQueryService {
  private readonly sdk: SqlSdk;

  constructor(@InjectDataSource() ds: DataSource) {
    this.sdk = new SqlSdk(new TypeOrmSqlExecutor(ds));
  }

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

> SqlSdk 跳过 ORM 层直接走底层连接，复杂 JOIN 比 QueryBuilder 简洁得多。

---

## 8. 事务

### 推荐：`DataSource.transaction`

```typescript
@Injectable()
export class OrderService {
  constructor(@InjectDataSource() private readonly ds: DataSource) {}

  async createOrder(dto) {
    return this.ds.transaction(async (manager) => {
      const order = await manager.save(Order, { ... });
      await manager.update(Stock, { skuId: dto.skuId }, { count: () => 'count - 1' });
      return order;
    });
  }
}
```

### 或：`QueryRunner`（精细控制）

```typescript
const qr = this.ds.createQueryRunner();
await qr.connect();
await qr.startTransaction();
try {
  await qr.manager.save(Order, { ... });
  await qr.manager.delete(Cart, { id });
  await qr.commitTransaction();
} catch (err) {
  await qr.rollbackTransaction();
  throw err;
} finally {
  await qr.release();
}
```

要点：
- ✅ 事务内必须用 `manager`，不能用外面的 `Repository`
- ✅ 抛异常自动回滚（`transaction` 包装下）
- ❌ 不要在事务内做耗时 I/O

---

## 9. 迁移

```bash
# 生成（基于 entity diff）
npx typeorm migration:generate -d src/db/data-source.ts src/db/migrations/AddUserStatus

# 创建空白迁移
npx typeorm migration:create src/db/migrations/CustomFix

# 执行
npx typeorm migration:run -d src/db/data-source.ts

# 回滚
npx typeorm migration:revert -d src/db/data-source.ts
```

- ✅ `synchronize: false` 是铁律
- ✅ 迁移 SQL 入 git，code review 后上线
- ❌ 不要修改已发布的迁移文件

---

## 10. 反例速查

| ❌ | ✅ |
|----|----|
| `synchronize: true` | 永远 `false`，用 migration |
| `@Entity()` 不写表名靠默认 | `@Entity('sys_user')` 显式 |
| 关系不加 `createForeignKeyConstraints: false` | 强制不建外键 |
| `@ManyToMany + @JoinTable` 接管中间表 | `OneToMany + ManyToOne` 自管中间表 |
| QueryBuilder 拼字符串条件 | `.andWhere('x = :x', { x })` 参数化 |
| `getManyAndCount` 在 GROUP BY 下用 | count 单独查（避免误算） |
| 事务内继续用 `this.repo.xxx` | 用 `manager.xxx` |
| 复杂 JOIN 全用 QueryBuilder 拼 | 优先 SqlSdk |
| `@Column` 不写 `name` 靠驼峰转下划线 | 显式 `name: 'real_name'` |
| 时间字段手动维护 `createdAt` | 用 `@CreateDateColumn / @UpdateDateColumn` |

---

## 11. 新增一张表 Checklist

- [ ] `db/entities/<表名>.entity.ts` 定义 Entity（`@Entity('snake_case')`）
- [ ] 字段全部显式 `@Column({ name: 'snake_name', type: 'xxx' })`
- [ ] 索引用 `@Index`，唯一字段用 `unique: true` 或 `@Index(..., { unique: true })`
- [ ] `@CreateDateColumn / @UpdateDateColumn` 自动维护时间
- [ ] 关系装饰器加 `{ createForeignKeyConstraints: false }`
- [ ] 在 `TypeOrmCoreModule` 的 `ENTITIES` 数组登记
- [ ] 业务 Module 用 `TypeOrmModule.forFeature([X])` 注册
- [ ] Service 用 `@InjectRepository(X) repo: Repository<X>` 注入
- [ ] 复杂查询优先评估 SqlSdk
- [ ] 生成迁移：`typeorm migration:generate ...`，提交 SQL

---

## 12. 官方资源

- 文档：https://typeorm.io
- Repository API：https://typeorm.io/repository-api
- QueryBuilder：https://typeorm.io/select-query-builder
