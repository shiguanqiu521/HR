# 人员管理系统（Employee Management System）

一套前后端分离的人员管理系统，部署在 `D:\hr-system`，实现登录认证 + 员工新增、列表查询、信息编辑、软删除、详情查看功能。采用 JWT 无状态令牌认证，不含角色权限控制。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Spring Boot 3.3.5 + Spring JDBC（JdbcTemplate），JDK 17 |
| 数据库 | SQLite 3（文件库 `backend/data/hr.db`，零配置、无需安装服务） |
| 前端 | Vue 3.5 + Element Plus 2.8（原生 HTML/JS，无需 npm install 与打包） |
| 构建 | Apache Maven 3.9.9（已安装在 `D:\tools\apache-maven-3.9.9`） |

## 目录结构

```
D:\hr-system\
├── backend\                     后端 Spring Boot 工程
│   ├── pom.xml
│   ├── data\hr.db               SQLite 数据库文件（首次启动自动创建）
│   ├── target\hr-employee.jar   构建产物
│   └── src\main\
│       ├── java\com\hr\
│       │   ├── HrApplication.java
│       │   ├── common\          统一响应体、分页对象、异常处理
│       │   ├── config\          CORS 配置、认证拦截器注册
│       │   ├── controller\      接口层（含 AuthController）
│       │   ├── dto\             请求参数与校验注解（含登录 DTO）
│       │   ├── model\           实体（Employee、SysUser）
│       │   ├── repository\      SQLite 数据访问
│       │   ├── security\        JWT 令牌、密码哈希、认证拦截器
│       │   └── service\         业务逻辑（含 AuthService）
│       └── resources\
│           ├── application.yml
│           └── schema.sql       建表语句（启动自动执行，幂等）
├── frontend\                    前端静态工程
│   ├── index.html               页面与模板
│   ├── app.js                   交互逻辑
│   ├── style.css                样式
│   ├── server.js                Node 静态服务器（端口 5173）
│   └── libs\                    Vue / Element Plus 本地库（已离线化）
├── API.md                       接口文档
├── build.bat                    一键构建后端
├── start-backend.bat            一键启动后端（8080）
└── start-frontend.bat           一键启动前端（5173）
```

## 快速启动

需要 **两个命令行窗口**，先后端后前端。

### 方式一：双击脚本（推荐）

1. 双击 `start-backend.bat` → 等待控制台出现 `Started HrApplication`
2. 双击 `start-frontend.bat` → 出现 `Frontend server running at http://localhost:5173`
3. 浏览器打开 **http://localhost:5173**
4. 使用默认账号登录：用户名 `admin`，密码 `admin123`

### 方式二：命令行

```bat
:: 窗口 1 - 后端
cd /d D:\hr-system\backend
set JAVA_HOME=D:\Program Files\Java\jdk-17
D:\tools\apache-maven-3.9.9\bin\mvn.cmd -B clean package -DskipTests
"%JAVA_HOME%\bin\java.exe" -Dfile.encoding=UTF-8 -jar target\hr-employee.jar

:: 窗口 2 - 前端
cd /d D:\hr-system\frontend
node server.js
```

### 验证部署是否成功

```bat
curl http://localhost:8080/api/health
```

返回 `{"code":200,...,"data":{"status":"UP"}}` 即后端正常。前端页面右上角会显示「后端已连接」绿点。

## 停止服务

在对应命令行窗口按 `Ctrl + C`，或直接关闭窗口。

## 功能说明

| 功能 | 页面入口 | 对应接口 |
| --- | --- | --- |
| 用户登录 | 登录页（启动后首屏），输入用户名密码 | `POST /api/auth/login` |
| 员工新增 | 列表页右上「新增员工」按钮，弹窗表单，含前端校验 | `POST /api/employees` |
| 员工列表查询 | 顶部姓名 / 部门输入框 + 查询、重置；底部分页器 | `GET /api/employees` |
| 员工信息编辑 | 表格行「编辑」，或详情抽屉「编辑该员工」 | `PUT /api/employees/{id}` |
| 员工删除 | 表格行「删除」，二次确认后软删除 | `DELETE /api/employees/{id}` |
| 员工详情查看 | 表格行「详情」，右侧抽屉展示完整字段 | `GET /api/employees/{id}` |

## 数据说明

- **软删除**：删除只把 `employee.deleted` 置为 1，数据行永久保留。历史数据可用 SQL 查看：

  ```sql
  SELECT * FROM employee WHERE deleted = 1;
  ```

  用命令行查询（sqlite3 CLI 未安装时可用任意 SQLite 图形工具打开 `D:\hr-system\backend\data\hr.db`）。

- **手机号唯一**：数据库层面对未删除记录建了唯一索引，服务层同时做校验并返回友好提示（HTTP 409）。

- **重置数据**：停止后端后删除 `backend\data\hr.db`，重启即自动重新建表（空库）。

## 端口与配置

| 配置项 | 默认值 | 修改位置 |
| --- | --- | --- |
| 后端端口 | 8080 | `backend\src\main\resources\application.yml` → `server.port` |
| 前端端口 | 5173 | `start-frontend.bat`，或 `set PORT=xxxx` 后运行 `node server.js` |
| 数据库路径 | `./data/hr.db` | `application.yml` → `spring.datasource.url` |
| 前端调用的后端地址 | `http://localhost:8080/api` | `frontend\app.js` → `API_BASE` |
| JWT 密钥 | `hr-employee-jwt-secret-key-change-me-in-production-2026` | `application.yml` → `hr.auth.jwt-secret` |
| 令牌有效期 | 720 分钟（12 小时） | `application.yml` → `hr.auth.token-ttl-minutes` |
| 默认用户名 | `admin` | `application.yml` → `hr.auth.default-username` |
| 默认密码 | `admin123` | `application.yml` → `hr.auth.default-password` |

> 后端已开启 `/api/**` 的 CORS，前后端跨端口访问无需额外配置。
>
> **安全提示**：生产环境务必修改 `jwt-secret` 和 `default-password`。密码在数据库中以 PBKDF2-HMAC-SHA256 哈希存储，不会明文落库。

## 接口文档

完整接口文档见 **[API.md](./API.md)**，包含认证机制（JWT 令牌）、统一响应结构、状态码约定、字段校验规则、每个接口的请求/响应示例与边界行为说明。
