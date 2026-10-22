# 人员管理系统 - 接口文档

| 项目 | 内容 |
| --- | --- |
| 服务名称 | hr-employee（人员管理系统后端） |
| 技术栈 | Spring Boot 3.3.5 + Spring JDBC + SQLite 3 |
| 服务地址 | `http://localhost:8080` |
| 接口前缀 | `/api` |
| 数据格式 | 请求与响应均为 `application/json;charset=UTF-8` |
| 日期格式 | `hireDate` 为 `yyyy-MM-dd`；`createdAt` / `updatedAt` 为 `yyyy-MM-dd HH:mm:ss` |
| 文档版本 | v1.1.0 |
| 更新日期 | 2026-09-19 |

---

## 一、通用约定

### 1.1 统一响应结构

所有接口（成功与失败）都返回同一层结构：

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": 1758182400000
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | 业务状态码，与 HTTP 状态码一致 |
| message | string | 提示信息，成功固定为 `success`，失败为具体错误原因 |
| data | object / array / null | 业务数据，失败时为 `null` |
| timestamp | long | 服务端响应时间戳（毫秒） |

### 1.2 状态码说明

HTTP 状态码与响应体 `code` 始终保持一致，便于用任一维度做断言。

| code | HTTP Status | 含义 | 典型场景 |
| --- | --- | --- | --- |
| 200 | 200 | 成功 | 请求正常处理 |
| 400 | 400 | 参数校验失败 | 必填项为空、手机号格式错误、状态值不合法、分页参数越界、JSON 无法解析 |
| 401 | 401 | 未认证 | 未携带 Token、Token 无效或已过期 |
| 404 | 404 | 资源不存在 | 员工 id 不存在，或该员工已被软删除 |
| 409 | 409 | 业务冲突 | 手机号已被其他在职记录占用 |
| 500 | 500 | 服务器内部错误 | 未预期的异常 |

### 1.3 员工状态字典

`status` 为字符串枚举，仅接受以下三个值，传入其他值返回 `400`：

| 值 | 说明 |
| --- | --- |
| 在职 | 正常在职员工 |
| 试用期 | 试用期员工 |
| 离职 | 已离职员工 |

### 1.4 员工对象（Employee）字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | long | 员工主键，数据库自增，创建时不传 |
| name | string | 姓名，必填，最长 50 |
| phone | string | 手机号，必填，11 位中国大陆手机号，未删除记录内唯一 |
| department | string | 部门，必填，最长 50 |
| position | string | 岗位，必填，最长 50 |
| hireDate | string | 入职时间，必填，格式 `yyyy-MM-dd` |
| status | string | 状态，必填，见 1.3 |
| createdAt | string | 创建时间，服务端生成，只读 |
| updatedAt | string | 最后更新时间，服务端生成，只读 |

> `deleted`（软删除标记）为数据库内部字段，不在接口响应中暴露。

---

## 二、认证与鉴权

### 2.1 认证机制

系统采用 **JWT（JSON Web Token）** 无状态认证。登录成功后服务端返回 JWT 令牌，客户端需在后续所有请求的 `Authorization` 请求头中携带该令牌。

**令牌格式**

```
Authorization: Bearer <token>
```

**令牌有效期**

默认 720 分钟（12 小时），可通过配置文件 `hr.auth.token-ttl-minutes` 调整。过期后需重新登录。

**白名单接口**

以下接口无需认证即可访问：

| 路径 | 说明 |
| --- | --- |
| `POST /api/auth/login` | 登录接口 |
| `GET /api/health` | 健康检查 |

**401 响应**

未携带令牌、令牌无效或已过期时，返回 `401`：

```json
{
  "code": 401,
  "message": "未登录或登录凭证缺失，请先登录",
  "data": null,
  "timestamp": 1789792217193
}
```

| message | 触发场景 |
| --- | --- |
| `未登录或登录凭证缺失，请先登录` | 请求头未携带 `Authorization` 或格式错误 |
| `登录凭证无效，请重新登录` | Token 签名无效或被篡改 |
| `登录已过期，请重新登录` | Token 超过有效期 |

### 2.2 登录接口

用户凭用户名和密码换取 JWT 令牌。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `POST` |
| 请求路径 | `/api/auth/login` |
| Content-Type | `application/json` |

**请求参数（Body）**

| 参数 | 类型 | 必填 | 校验规则 |
| --- | --- | --- | --- |
| username | string | 是 | 非空，最长 50 |
| password | string | 是 | 非空，最长 100 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**成功响应** `200`

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbiIs...",
    "tokenType": "Bearer",
    "expiresIn": 43200,
    "username": "admin",
    "displayName": "系统管理员"
  },
  "timestamp": 1789792221549
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| token | string | JWT 令牌，后续请求需携带此值 |
| tokenType | string | 固定为 `Bearer` |
| expiresIn | int | 令牌有效期（秒） |
| username | string | 登录用户名 |
| displayName | string | 用户显示名称 |

**失败响应** `401`

```json
{
  "code": 401,
  "message": "用户名或密码错误",
  "data": null,
  "timestamp": 1789792217862
}
```

> 安全说明：无论用户名不存在还是密码错误，均返回相同提示，防止用户枚举攻击。

### 2.3 当前用户信息

获取当前登录用户的基本信息。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `GET` |
| 请求路径 | `/api/auth/me` |
| 认证 | 需要 Bearer Token |

**请求示例**

```bash
curl http://localhost:8080/api/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..."
```

**成功响应** `200`

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "userId": 1,
    "username": "admin",
    "displayName": "系统管理员"
  },
  "timestamp": 1789792227776
}
```

### 2.4 默认账号

系统首次启动时自动创建默认管理员账号：

| 字段 | 值 |
| --- | --- |
| 用户名 | `admin` |
| 密码 | `admin123` |
| 显示名称 | `系统管理员` |

> 生产环境请务必修改默认密码。密码配置项：`hr.auth.default-password`（存储在配置文件中，数据库内为 PBKDF2 哈希值）。

---

## 三、接口明细

### 3.1 员工新增

录入员工基础信息，成功后返回完整员工对象（含服务端生成的 `id`、`createdAt`、`updatedAt`）。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `POST` |
| 请求路径 | `/api/employees` |
| Content-Type | `application/json` |
| 认证 | 需要 Bearer Token |

**请求参数（Body）**

| 参数 | 类型 | 必填 | 校验规则 |
| --- | --- | --- | --- |
| name | string | 是 | 非空，长度 ≤ 50 |
| phone | string | 是 | 非空，匹配 `^1[3-9]\d{9}$`，未删除记录内唯一 |
| department | string | 是 | 非空，长度 ≤ 50 |
| position | string | 是 | 非空，长度 ≤ 50 |
| hireDate | string | 是 | 非空，格式 `yyyy-MM-dd` |
| status | string | 是 | 必须是 `在职` / `试用期` / `离职` 之一 |

**请求示例**

```bash
curl -X POST http://localhost:8080/api/employees \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "张三",
    "phone": "13800138000",
    "department": "研发部",
    "position": "测试工程师",
    "hireDate": "2026-03-01",
    "status": "在职"
  }'
```

**成功响应** `200`

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "张三",
    "phone": "13800138000",
    "department": "研发部",
    "position": "测试工程师",
    "hireDate": "2026-03-01",
    "status": "在职",
    "createdAt": "2026-09-18 14:02:11",
    "updatedAt": "2026-09-18 14:02:11"
  },
  "timestamp": 1758175331000
}
```

**失败响应示例**

手机号重复（`409`）：

```json
{
  "code": 409,
  "message": "手机号已存在：13800138000",
  "data": null,
  "timestamp": 1758175340000
}
```

参数校验失败（`400`，多条错误用 `; ` 拼接）：

```json
{
  "code": 400,
  "message": "姓名不能为空; 手机号格式不正确，需为11位中国大陆手机号",
  "data": null,
  "timestamp": 1758175350000
}
```

> 多条错误的拼接顺序由 Bean Validation 实现决定，不保证固定顺序，调用方请整体展示 `message`，不要依赖其中字段出现的先后。

---

### 3.2 员工列表查询（分页 + 筛选）

分页查询未删除的员工，支持按姓名、部门模糊筛选，按 `id` 倒序返回（最新新增在前）。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `GET` |
| 请求路径 | `/api/employees` |
| 认证 | 需要 Bearer Token |

**请求参数（Query）**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| page | int | 否 | 1 | 页码，从 1 开始；小于 1 返回 `400` |
| size | int | 否 | 10 | 每页条数，取值 1 ~ 100；越界返回 `400` |
| name | string | 否 | - | 姓名，模糊匹配（`LIKE %name%`），空串视为不筛选 |
| department | string | 否 | - | 部门，模糊匹配（`LIKE %department%`），空串视为不筛选 |

**响应 data 结构**

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| list | array | 当前页员工列表，元素为 Employee 对象 |
| total | long | 符合筛选条件的总记录数（不含已软删除） |
| page | int | 当前页码 |
| size | int | 每页条数 |
| pages | int | 总页数，由 `total` 与 `size` 计算 |

**请求示例**

```bash
# 默认第一页，每页 10 条
curl "http://localhost:8080/api/employees?page=1&size=10" \
  -H "Authorization: Bearer <token>"

# 按姓名模糊筛选
curl "http://localhost:8080/api/employees?page=1&size=10&name=张" \
  -H "Authorization: Bearer <token>"

# 按部门筛选
curl "http://localhost:8080/api/employees?page=1&size=10&department=研发" \
  -H "Authorization: Bearer <token>"

# 姓名 + 部门组合筛选
curl "http://localhost:8080/api/employees?page=1&size=5&name=张&department=研发部" \
  -H "Authorization: Bearer <token>"
```

**成功响应** `200`

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "list": [
      {
        "id": 2,
        "name": "张小明",
        "phone": "13900139000",
        "department": "研发部",
        "position": "后端工程师",
        "hireDate": "2025-11-20",
        "status": "试用期",
        "createdAt": "2026-09-18 14:05:33",
        "updatedAt": "2026-09-18 14:05:33"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 10,
    "pages": 1
  },
  "timestamp": 1758175533000
}
```

**边界行为**

- 无匹配数据时 `list` 为 `[]`，`total` 为 `0`，`pages` 为 `0`，仍返回 `200`。
- 已软删除的员工不会出现在结果中。
- `page` 超出总页数时返回空 `list`，`total` 仍为真实总数。

**失败响应示例**（`400`）

```json
{
  "code": 400,
  "message": "每页条数 size 必须在 1 ~ 100 之间",
  "data": null,
  "timestamp": 1758175600000
}
```

---

### 3.3 员工详情查看

按 id 查询单条员工的完整信息。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `GET` |
| 请求路径 | `/api/employees/{id}` |
| 认证 | 需要 Bearer Token |

**请求参数（Path）**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | long | 是 | 员工主键 |

**请求示例**

```bash
curl http://localhost:8080/api/employees/1 \
  -H "Authorization: Bearer <token>"
```

**成功响应** `200`

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "张三",
    "phone": "13800138000",
    "department": "研发部",
    "position": "测试工程师",
    "hireDate": "2026-03-01",
    "status": "在职",
    "createdAt": "2026-09-18 14:02:11",
    "updatedAt": "2026-09-18 14:02:11"
  },
  "timestamp": 1758175700000
}
```

**失败响应** `404`（id 不存在，或该员工已被软删除）

```json
{
  "code": 404,
  "message": "员工不存在或已被删除，id=999",
  "data": null,
  "timestamp": 1758175710000
}
```

---

### 3.4 员工信息编辑

全量更新员工基础资料。请求体字段与「员工新增」完全一致，均为必填。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `PUT` |
| 请求路径 | `/api/employees/{id}` |
| Content-Type | `application/json` |
| 认证 | 需要 Bearer Token |

**请求参数**

| 参数 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| id | Path | long | 是 | 员工主键 |
| name / phone / department / position / hireDate / status | Body | - | 是 | 校验规则同 3.1 |

**请求示例**

```bash
curl -X PUT http://localhost:8080/api/employees/1 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "张三",
    "phone": "13800138000",
    "department": "测试部",
    "position": "高级测试工程师",
    "hireDate": "2026-03-01",
    "status": "试用期"
  }'
```

**成功响应** `200`（返回更新后的完整对象，`updatedAt` 已刷新）

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "张三",
    "phone": "13800138000",
    "department": "测试部",
    "position": "高级测试工程师",
    "hireDate": "2026-03-01",
    "status": "试用期",
    "createdAt": "2026-09-18 14:02:11",
    "updatedAt": "2026-09-18 14:20:47"
  },
  "timestamp": 1758176447000
}
```

**失败响应示例**

员工不存在或已删除（`404`）：

```json
{
  "code": 404,
  "message": "员工不存在或已被删除，id=999",
  "data": null,
  "timestamp": 1758176450000
}
```

手机号被他人占用（`409`）：

```json
{
  "code": 409,
  "message": "手机号已被其他员工占用：13900139000",
  "data": null,
  "timestamp": 1758176460000
}
```

> 说明：编辑时若手机号未变更（仍是自己的），不会触发 409；只有与其他未删除记录冲突才报错。`createdAt` 不会被修改。

---

### 3.5 员工删除（软删除）

逻辑删除，将 `deleted` 置为 1 并刷新 `updatedAt`，**数据行保留在数据库中不做物理删除**。删除后该员工不再出现在列表和详情中。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `DELETE` |
| 请求路径 | `/api/employees/{id}` |
| 认证 | 需要 Bearer Token |

**请求参数（Path）**

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| id | long | 是 | 员工主键 |

**请求示例**

```bash
curl -X DELETE http://localhost:8080/api/employees/1 \
  -H "Authorization: Bearer <token>"
```

**成功响应** `200`

```json
{
  "code": 200,
  "message": "success",
  "data": null,
  "timestamp": 1758176500000
}
```

**失败响应** `404`（id 不存在，或已被删除后重复调用）

```json
{
  "code": 404,
  "message": "员工不存在或已被删除，id=1",
  "data": null,
  "timestamp": 1758176510000
}
```

> 幂等性说明：重复删除同一 id，第二次返回 `404`（而非静默成功），便于测试断言。

---

## 四、辅助接口

以下两个接口不属于 5 个核心功能，仅用于部署自检和前端下拉数据，不影响主流程。

### 4.1 健康检查

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `GET` |
| 请求路径 | `/api/health` |
| 认证 | 无需认证（白名单） |

```bash
curl http://localhost:8080/api/health
```

```json
{
  "code": 200,
  "message": "success",
  "data": { "status": "UP", "application": "hr-employee" },
  "timestamp": 1758176600000
}
```

### 4.2 部门字典

返回当前所有未删除员工中出现过的部门（去重、升序），供前端部门下拉候选使用。

| 项目 | 内容 |
| --- | --- |
| 请求方法 | `GET` |
| 请求路径 | `/api/employees/meta/departments` |
| 认证 | 需要 Bearer Token |

```bash
curl http://localhost:8080/api/employees/meta/departments \
  -H "Authorization: Bearer <token>"
```

```json
{
  "code": 200,
  "message": "success",
  "data": ["研发部", "测试部", "人事部"],
  "timestamp": 1758176700000
}
```

---

## 五、接口清单汇总

| # | 功能 | 方法 | 路径 | 成功码 | 主要失败码 | 认证 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 用户登录 | POST | `/api/auth/login` | 200 | 401 | 无需 |
| 2 | 当前用户信息 | GET | `/api/auth/me` | 200 | 401 | 需要 |
| 3 | 员工新增 | POST | `/api/employees` | 200 | 400 / 401 / 409 | 需要 |
| 4 | 员工列表查询 | GET | `/api/employees` | 200 | 400 / 401 | 需要 |
| 5 | 员工详情查看 | GET | `/api/employees/{id}` | 200 | 401 / 404 | 需要 |
| 6 | 员工信息编辑 | PUT | `/api/employees/{id}` | 200 | 400 / 401 / 404 / 409 | 需要 |
| 7 | 员工删除（软删除） | DELETE | `/api/employees/{id}` | 200 | 401 / 404 | 需要 |
| - | 健康检查 | GET | `/api/health` | 200 | - | 无需 |
| - | 部门字典 | GET | `/api/employees/meta/departments` | 200 | 401 | 需要 |

---

## 六、数据库表结构

数据库文件：`D:\hr-system\backend\data\hr.db`（SQLite，首次启动自动建表）

```sql
CREATE TABLE employee
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,           -- 姓名
    phone      TEXT    NOT NULL,           -- 手机号
    department TEXT    NOT NULL,           -- 部门
    position   TEXT    NOT NULL,           -- 岗位
    hire_date  TEXT    NOT NULL,           -- 入职时间 yyyy-MM-dd
    status     TEXT    NOT NULL,           -- 在职 / 试用期 / 离职
    deleted    INTEGER NOT NULL DEFAULT 0, -- 软删除标记：0 正常，1 已删除
    created_at TEXT    NOT NULL,           -- 创建时间 yyyy-MM-dd HH:mm:ss
    updated_at TEXT    NOT NULL            -- 更新时间 yyyy-MM-dd HH:mm:ss
);

CREATE INDEX idx_employee_deleted    ON employee (deleted);
CREATE INDEX idx_employee_name       ON employee (name);
CREATE INDEX idx_employee_department ON employee (department);

-- 仅对未删除记录生效的手机号唯一索引
CREATE UNIQUE INDEX uk_employee_phone_active ON employee (phone) WHERE deleted = 0;

CREATE TABLE IF NOT EXISTS sys_user
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,  -- 登录用户名
    password_hash TEXT    NOT NULL,         -- PBKDF2-HMAC-SHA256 哈希值
    salt          TEXT    NOT NULL,         -- 16 字节随机盐值（hex）
    display_name  TEXT    NOT NULL,         -- 显示名称
    enabled       INTEGER NOT NULL DEFAULT 1, -- 是否启用：1 启用，0 禁用
    created_at    TEXT    NOT NULL,         -- 创建时间 yyyy-MM-dd HH:mm:ss
    updated_at    TEXT    NOT NULL          -- 更新时间 yyyy-MM-dd HH:mm:ss
);
```

> 软删除记录可通过 SQL 直接查询历史数据：
> `SELECT * FROM employee WHERE deleted = 1;`
