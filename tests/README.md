# HR 系统接口自动化测试（企业级分层架构）

## 项目结构

```
tests/
├── conftest.py             # pytest 根配置：环境切换、fixture、Allure 标签自动生成
│
├── config/                 # 配置层
│   ├── __init__.py
│   ├── settings.py         # 环境配置代理（dev/test/prod 运行时切换）
│   ├── .env.example        # 配置模板（可提交，不含真实密钥）
│   ├── .env.dev            # 开发环境配置（已被 .gitignore 忽略）
│   ├── .env.test           # 测试环境配置（同上）
│   └── .env.prod           # 生产环境配置（同上）
│
├── data/                   # 数据层
│   ├── auth_data.yaml      # 认证模块测试数据
│   ├── employee_data.yaml  # 员工模块测试数据
│   └── department_data.yaml # 部门模块测试数据
│
├── common/                 # 公共组件层
│   ├── __init__.py
│   ├── logger.py           # 日志组件（控制台+文件）
│   ├── assertions.py       # 通用断言工具
│   ├── request_handler.py  # 接口请求封装（请求/响应留痕，供报告附件）
│   ├── data_factory.py     # 数据工厂（生成测试数据 + 参数化数据 + 自动清理）
│   └── ui_base.py          # UI 自动化基类（预留）
│
├── api/                    # 接口封装层
│   ├── __init__.py
│   ├── auth_api.py         # 认证接口
│   ├── employee_api.py     # 员工接口
│   └── department_api.py   # 部门接口
│
├── pages/                  # 页面对象层（UI 测试预留）
│   ├── __init__.py
│   ├── login_page.py
│   ├── employee_page.py
│   └── department_page.py
│
├── fixtures/
│   └── conftest.py         # 与根 conftest.py 同一份内容（保留旧路径引用，勿单独修改）
│
├── testcases/              # 用例层
│   ├── api/                # 接口测试用例
│   │   ├── test_auth.py        # 认证模块：15 个用例函数 / 22 个 item
│   │   ├── test_employee.py    # 员工模块：52 个用例函数 / 72 个 item
│   │   └── test_department.py  # 部门模块：24 个用例函数 / 30 个 item
│   └── ui/                 # UI 测试用例（预留，当前无用例）
│
├── reports/                # 测试报告输出（allure-results/、allure-report/、report_*.html）
├── logs/                   # 日志文件输出
├── run.py                  # 统一测试执行入口（推荐）
├── pytest.ini              # pytest 配置（testpaths、allure 输出目录、markers）
├── requirements.txt        # 依赖
└── README.md               # 本文件
```

## 用例规模

| 范围 | 认证 | 员工 | 部门 | 合计 |
| --- | --- | --- | --- | --- |
| 用例表有效用例 | 15 | 53 | 24 | **92** |
| 自动化用例函数 | 15 | 52 | 24 | **91** |
| pytest item（参数行展开） | 22 | 72 | 30 | **124** |
| dev 实测（2026-11-10） | 21 | 72 | 30 | **123 passed / 0 failed / 1 skipped**，26.0s |

- 用例表：`../HR系统测试用例.xlsx`（功能测试 107 行 = 92 有效 + 15 已删除标注行；变更类型分布 修改 48 / 新增 15 / 不变 29），逐条变更记录见「用例变更记录」sheet（85 条）。
- 唯一 skipped：`TC-AUTH-014`（过期 token 本地自签），在 `config/.env.dev` 填入与服务端一致的 `HR_JWT_SECRET` 后转执行，届时目标为 124 passed / 0 failed / 0 skipped。
- 唯一未自动化的有效用例：`TC-DEL-007`（软删除落库校验，需数据库直连，保留为手工用例）。
- 设计与评审说明：`../接口测试用例设计评审与修改清单.md`。

## 快速开始

### 1. 安装依赖
```bash
cd D:\hr-system\tests
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> Allure 命令行工具需单独安装（用于生成 HTML 报告）：
> - macOS：`brew install allure`
> - Windows：下载 [allure-commandline](https://github.com/allure-framework/allure2/releases) 并加入 PATH
> - 未安装 Allure 时 `run.py` 会跳过 Allure 报告并保留 pytest-HTML 报告

### 2. 运行测试

**推荐：使用统一入口（自动生成双报告）**
```bash
python run.py                        # 默认 dev 环境，生成 HTML + Allure 报告
python run.py --env test             # 指定测试环境
python run.py --env prod -k login    # 环境 + 关键字过滤
python run.py --no-allure            # 只生成 HTML 报告
python run.py --allure-serve         # 执行完自动打开 Allure 预览
```

**直接使用 pytest（调试用）：**
```bash
pytest --collect-only -q                       # 只看收集结果（不连服务，用于校验用例结构）
pytest testcases/api/ -v                       # 全部接口用例
pytest testcases/api/test_department.py -v -k "edit"   # 单模块 + 关键字
pytest --env test                              # 指定环境
```

**报告输出：**
```
reports/
├── report_20261110_132000.html      # HTML 报告（每次执行生成新文件）
├── allure-results/                  # Allure 原始数据（每次执行前清理）
└── allure-report/                   # Allure 静态 HTML 报告
```

### 3. 环境配置

配置优先级：**操作系统环境变量 > `.env.{环境名}` > 代码默认值**。

```bash
# 方式一：就地修改配置文件（推荐，敏感值不入版本库）
copy config\.env.example config\.env.dev    # 首次使用
notepad config\.env.dev                     # 填写 HR_BASE_URL / 账号 / HR_JWT_SECRET

# 方式二：操作系统环境变量（临时覆盖）
set HR_ENV=test                             # Windows
export HR_ENV=test                          # Linux/Mac
export HR_BASE_URL=http://test-server:8080
export HR_ADMIN_USER=admin
export HR_ADMIN_PWD=
export HR_JWT_SECRET=
```

| 配置项 | 说明 |
| --- | --- |
| `HR_BASE_URL` | 被测服务地址 |
| `HR_ADMIN_USER` / `HR_ADMIN_PWD` | 登录凭证，供 session 级 `request_client` fixture 自动登录 |
| `HR_JWT_SECRET` | 后端 `hr.auth.jwt-secret`；仅 `TC-AUTH-014` 本地自签过期 token 用，留空则该用例条件跳过 |
| `HR_LOG_LEVEL` | DEBUG / INFO / WARNING / ERROR |

> `.env.dev` / `.env.test` / `.env.prod` 已被 `.gitignore` 忽略，仓库中只保留 `.env.example` 模板；
> 真实密钥请在目标机器上就地填写，不提交、不写入用例代码。

## 分层说明

| 层级 | 目录 | 职责 |
|------|------|------|
| 配置层 | config/ | 环境配置、多环境切换（.env.dev/.env.test/.env.prod） |
| 数据层 | data/ | 静态测试数据（yaml） |
| 公共组件层 | common/ | 日志、断言、请求封装、数据工厂与数据清理 |
| 接口封装层 | api/ | 每个模块的接口调用封装，不含断言 |
| 页面对象层 | pages/ | UI 测试页面对象（预留） |
| fixture 层 | conftest.py | 认证客户端、API 实例、数据工厂与清理器 |
| 用例层 | testcases/ | 测试用例实现，只写数据与断言 |

## 用例编写约定

1. **一个用例函数对应一个 TC 编号**，参数化数据行属于同一编号，不另立函数。
2. **docstring 首行格式固定**：`TC-XXX-nnn [P级] 标题`，其中编号、级别、标题与用例表逐字一致。
   `conftest.pytest_collection_modifyitems` 据此生成 Allure 标签，用例代码里不写任何 allure 装饰器。
3. 断言统一走 `common.assertions.AssertUtil`：
   - 单点判定用 `assert_status_code` / `assert_biz_code` / `assert_message_contains` / `assert_message_equals`；
   - 参数校验类失败用 `assert_validation_error`（HTTP 400 + code 400 + message 关键字 + data 为 null 四个判定点合一）。
4. 预期结果按后端源码推导（DTO 注解 → `@Valid` → Service 校验顺序 → `GlobalExceptionHandler`），
   不写"400 或 404"这类两分支都能通过的模糊预期。
5. 测试数据一律由 `DataFactory` 生成（uuid 唯一化），创建的数据通过 `DataCleaner` 追踪并自动清理。
6. **判定点不依赖环境历史数据**：需要"库里已有 N 条"的用例，在用例内用 `created_employee` /
   `two_employees` / `created_department` / `two_departments` 预置；比较式断言
   （`total == baseline`、`len(a) == len(b)`）必须先有一条绝对锚点（如 `total >= 2`），
   否则空库时两侧同为 0 会恒真——属假通过。
7. **失败归因先于改用例**：报错时按顺序判定，再决定动作，禁止为了让用例变绿而放宽预期。
   - 实际结果 ≠ 需求文档或源码约定 → 判为**系统缺陷**，预期保持按需求书写并提单；
   - 前置条件（环境、数据、配置）不满足 → 补前置，预期不动；
   - 预期在文档和源码中都找不到依据、而实现与文档一致 → 才允许修正预期，
     并在「用例变更记录」中写明依据来自哪一节文档、哪一行源码。
   - 文档未承诺的行为差异记为**改进建议**（如 R1 通配符转义），不得当作缺陷断言。

## Allure 报告结构

`conftest.py` 中的 `pytest_collection_modifyitems` 钩子自动为每条用例设置以下标签：

| 标签 | 来源 | 示例 |
|------|------|------|
| **feature** | 模块文件名 | 认证模块 / 员工管理模块 / 部门管理模块 |
| **story** | 类名去 Test 前缀 | Login / Employee Create / Department Edit |
| **severity** | docstring 首行的 `[P0]/[P1]/[P2]`（缺失时回退 TC 编号前缀） | critical / normal / minor |
| **title** | docstring 首行 | TC-AUTH-001 [P0] 登录成功-获取Token |
| **description** | 类 docstring | POST /api/auth/login |

`environment.properties` 自动写入测试环境名、服务地址、Python/pytest 版本与执行时间。

失败用例自动附加：
- **Request Body**：请求方法、URL、请求体（JSON 格式）
- **Response**：HTTP 状态码、响应体

## 核心特性

- **数据隔离**：每个用例使用 uuid 生成唯一数据，互不干扰
- **自动清理**：DataCleaner 在用例结束（含失败）后清理追踪到的数据
- **零装饰器用例**：Allure 层级与严重级由用例编号和级别自动推导，避免人工标注漂移
- **多环境支持**：`--env` 参数或 `HR_ENV` 环境变量切换 dev/test/prod，运行时生效
- **配置与密钥分离**：`.env.*` 不入库，仓库只保留 `.env.example`
- **Allure + HTML 双报告**：失败用例附带请求响应现场
- **分层架构**：接口封装、数据、断言、用例分离，可跨项目复用同一套骨架
