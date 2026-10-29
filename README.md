# 人员管理系统（Employee Management System）

一套前后端分离的人员管理系统，支持员工管理、部门管理、登录认证功能。采用 JWT 无状态令牌认证，MySQL + Redis 持久化与缓存，Docker Compose 一键部署，GitHub Actions CI/CD 自动化。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Spring Boot 3.3.5 + Spring Data JPA，JDK 17 |
| 数据库 | MySQL 8.0（Docker 容器） |
| 缓存 | Redis 7（Docker 容器） |
| 前端 | Vue 3.5 + Element Plus 2.8（原生 HTML/JS，无需 npm install 与打包） |
| 构建 | Apache Maven 3.9.9 |
| 部署 | Docker Compose + GitHub Actions CI/CD |

## 目录结构

```
D:\hr-system\
├── backend\                     后端 Spring Boot 工程
│   ├── pom.xml
│   ├── settings.xml             Maven 阿里云镜像配置
│   ├── Dockerfile               后端 Docker 镜像
│   ├── wait-for-mysql.sh        MySQL 就绪等待脚本
│   ├── target\hr-employee.jar   构建产物
│   └── src\main\
│       ├── java\com\hr\
│       │   ├── HrApplication.java
│       │   ├── common\          统一响应体、分页对象、异常处理
│       │   ├── config\          CORS 配置、Redis 配置、认证拦截器注册
│       │   ├── controller\      接口层（AuthController、EmployeeController、DepartmentController）
│       │   ├── dto\             请求参数与校验注解
│       │   ├── model\           实体（Employee、SysUser、Department）
│       │   ├── repository\      JPA 数据访问层
│       │   ├── security\        JWT 令牌、密码哈希、认证拦截器
│       │   └── service\         业务逻辑
│       └── resources\
│           ├── application.yml
│           └── schema.sql       建表语句（启动自动执行，幂等）
├── frontend\                    前端静态工程
│   ├── index.html               页面与模板（员工管理 + 部门管理）
│   ├── app.js                   交互逻辑
│   ├── style.css                样式
│   ├── server.js                Node 静态服务器（端口 5173）
│   ── libs\                    Vue / Element Plus 本地库（已离线化）
├── docker\                      Docker 部署配置
│   ├── mysql\init.sql           MySQL 初始化脚本
│   ├── nginx\nginx.conf         Nginx 反向代理配置
│   └── deploy.sh                服务器部署脚本
├── .github\workflows\ci-cd.yml  GitHub Actions CI/CD 工作流
├── docker-compose.yml           Docker Compose 编排文件
── .env                         环境变量（密码等敏感配置，不提交 git）
├── .env.example                 环境变量示例
├── .gitignore
├── API.md                       接口文档
└── README.md                    本文件
```

## 快速启动

### 方式一：Docker Compose（推荐，生产环境）

1. 确保已安装 Docker 和 Docker Compose
2. 复制环境变量文件并修改密码：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，修改 MySQL 和 Redis 密码
   ```
3. 启动所有服务：
   ```bash
   docker-compose up -d --build
   ```
4. 等待 90 秒后访问 **http://localhost**
5. 使用默认账号登录：用户名 `admin`，密码 `admin123`

### 方式二：本地开发（前后端分离）

需要 **两个命令行窗口**，先后端后前端。

**窗口 1 - 后端**

```bash
cd D:\hr-system\backend
set JAVA_HOME=D:\Program Files\Java\jdk-17
D:\tools\apache-maven-3.9.9\bin\mvn.cmd -B clean package -DskipTests
"%JAVA_HOME%\bin\java.exe" -Dfile.encoding=UTF-8 -jar target\hr-employee.jar
```

**窗口 2 - 前端**

```bash
cd D:\hr-system\frontend
node server.js
```

**验证部署是否成功**

```bash
curl http://localhost:8080/api/health
```

返回 `{"code":200,...,"data":{"status":"UP"}}` 即后端正常。前端页面右上角会显示「后端已连接」绿点。

### 方式三：GitHub Actions 自动部署

推送代码到 `main` 或 `master` 分支时，自动触发 CI/CD：

1. **构建与测试**：编译代码、运行单元测试
2. **部署到生产**：SSH 连接服务器 → git pull → docker compose build → docker compose up -d
3. **健康检查**：验证后端和前端是否正常启动

## 停止服务

**Docker Compose：**

```bash
docker-compose down
```

**本地开发：**

在对应命令行窗口按 `Ctrl + C`，或直接关闭窗口。

## 功能说明

| 功能 | 页面入口 | 对应接口 |
| --- | --- | --- |
| 用户登录 | 登录页（启动后首屏），输入用户名密码 | `POST /api/auth/login` |
| 员工新增 | 员工管理标签页 → 「新增员工」按钮，弹窗表单，含前端校验 | `POST /api/employees` |
| 员工列表查询 | 顶部姓名 / 部门输入框 + 查询、重置；底部分页器 | `GET /api/employees` |
| 员工信息编辑 | 表格行「编辑」，或详情抽屉「编辑该员工」 | `PUT /api/employees/{id}` |
| 员工删除 | 表格行「删除」，二次确认后软删除 | `DELETE /api/employees/{id}` |
| 员工详情查看 | 表格行「详情」，右侧抽屉展示完整字段 | `GET /api/employees/{id}` |
| 部门新增 | 部门管理标签页 → 「新增部门」按钮，弹窗表单 | `POST /api/departments` |
| 部门列表查询 | 顶部搜索框 + 部门列表展示 | `GET /api/departments` |
| 部门信息编辑 | 表格行「编辑」，弹窗表单 | `PUT /api/departments/{id}` |
| 部门删除 | 表格行「删除」，二次确认后软删除 | `DELETE /api/departments/{id}` |

## 数据说明

- **软删除**：删除只把 `deleted` 置为 1，数据行永久保留。历史数据可用 SQL 查看：

  ```sql
  SELECT * FROM employee WHERE deleted = 1;
  SELECT * FROM department WHERE deleted = 1;
  ```

- **手机号唯一**：数据库层面对未删除记录建了唯一索引，服务层同时做校验并返回友好提示（HTTP 409）。

- **部门名称唯一**：未删除的部门名称不能重复，重复时返回 HTTP 409。

- **重置数据**：停止后端后删除 MySQL 数据卷，重启即自动重新建表（空库）：
  ```bash
  docker-compose down
  docker volume rm hr_mysql-data
  docker-compose up -d
  ```

## 端口与配置

| 配置项 | 默认值 | 修改位置 |
| --- | --- | --- |
| 后端端口 | 8080 | `docker-compose.yml` → `backend.ports` |
| 前端端口 | 80 | `docker-compose.yml` → `frontend.ports` |
| MySQL 端口 | 3306 | `docker-compose.yml` → `mysql.ports` |
| Redis 端口 | 6379 | `docker-compose.yml` → `redis.ports` |
| 数据库名 | `hr_db` | `.env` → `MYSQL_DATABASE` |
| MySQL 密码 | `root` | `.env` → `MYSQL_ROOT_PASSWORD` |
| Redis 密码 | 无 | `.env` → `REDIS_PASSWORD` |
| JWT 密钥 | `hr-employee-jwt-secret-key-change-me-in-production-2026` | `.env` → `HR_AUTH_JWT_SECRET` |
| 令牌有效期 | 720 分钟（12 小时） | `application.yml` → `hr.auth.token-ttl-minutes` |
| 默认用户名 | `admin` | `application.yml` → `hr.auth.default-username` |
| 默认密码 | `admin123` | `application.yml` → `hr.auth.default-password` |

> **安全提示**：生产环境务必修改 `.env` 中的密码和 JWT 密钥。密码在数据库中以 PBKDF2-HMAC-SHA256 哈希存储，不会明文落库。`.env` 文件已在 `.gitignore` 中，不会被提交到 git。

## 接口文档

完整接口文档见 **[API.md](./API.md)**，包含认证机制（JWT 令牌）、统一响应结构、状态码约定、字段校验规则、每个接口的请求/响应示例与边界行为说明。

## CI/CD 部署

项目已配置 GitHub Actions 自动化部署流程，详见 `.github/workflows/ci-cd.yml`。

**部署流程：**

1. 推送代码到 `main` 或 `master` 分支
2. GitHub Actions 自动触发：
   - 构建后端并运行单元测试
   - SSH 连接生产服务器
   - 拉取最新代码
   - Docker Compose 重新构建并启动
   - 健康检查验证服务正常

**服务器要求：**

- Docker + Docker Compose
- 配置 GitHub Secrets：`SERVER_HOST`、`SERVER_USER`、`SERVER_SSH_KEY`
