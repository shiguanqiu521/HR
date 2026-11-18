# HR 系统接口自动化测试（企业级分层架构）

## 项目结构

```
tests/
├── conftest.py             # pytest 根配置：环境切换、fixture、Allure 标签自动生成
│
├── config/                 # 配置层
│   ├── __init__.py
│   ├── settings.py         # 环境配置代理（dev/test/prod 运行时切换）
│   ├── coverage.yml        # 覆盖率归因与门禁配置（统计范围、阈值、tcpserver 地址、部署字节码来源）
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
├── reports/                # 测试报告输出（allure-results/、allure-report/、report_*.html、coverage/）
├── logs/                   # 日志文件输出
├── run.py                  # 统一测试执行入口（推荐）
├── coverage_gate.py        # 覆盖率归因与门禁（统计后端代码，非测试脚本）
├── pytest.ini              # pytest 配置（testpaths、allure 输出目录、markers）
├── requirements.txt        # 依赖
└── README.md               # 本文件
```

## 用例规模

| 范围 | 认证 | 员工 | 部门 | 合计 |
| --- | --- | --- | --- | --- |
| 用例表有效用例 | 15 | 53 | 25 | **93** |
| 自动化用例函数 | 15 | 52 | 25 | **92** |
| pytest item（参数行展开） | 22 | 72 | 31 | **125** |
| dev 实测（2026-11-10） | 21 | 72 | 30 | **123 passed / 0 failed / 1 skipped**，26.0s |
| dev 实测（2026-11-17，覆盖率门禁同轮） | 22 | 72 | 30 | **124 passed / 0 failed / 0 skipped**，22.91s |
| dev 实测（2026-11-18 上午，补 4 条 `TC-META-*` 后同轮） | 22 | 76 | 30 | **128 passed / 0 failed / 0 skipped**，23.46s（该 4 条已于同日接口收敛时删除） |

- 用例表：`../HR系统测试用例.xlsx`（功能测试 121 行 = 93 有效 + 19 已删除标注行；有效用例变更类型分布 修改 48 / 新增 16 / 不变 29），逐条变更记录见「用例变更记录」sheet（95 条）。
- `TC-AUTH-014`（过期 token 本地自签）已在 `config/.env.dev` 填入与服务端一致的 `HR_JWT_SECRET` 后转执行，2026-11-17 实测通过，无 skipped。
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

## 覆盖率归因与门禁

统计的是**接口用例执行期间后端源码（`backend/src/main/java`）被覆盖的行与分支**，不是测试脚本自身。
接入这一段之前 `backend/src/test` 完全是空的，"接口测试到底覆盖了多少后端代码"因此无法回答；
现在该目录只有一个针对接口侧不可达分支的单元测试（见下文缺口 ②），它走独立通道，不改变上面这句统计口径。

**原理**：后端 JVM 以 JaCoCo agent 的 `tcpserver` 模式运行 → 本地清零计数器 → 跑接口用例 → dump 取回执行数据 →
用 `jacoco:report` 出报告 → 按包归因并按阈值判定。
`jacoco:report` 没有 `classDirectories` 参数，只读 `${project.build.outputDirectory}`，
所以"用哪份字节码出报告"等价于"`backend/target/classes` 里放的是什么"。
agent 只在容器设置了 `JAVA_TOOL_OPTIONS` 时挂载，镜像里预置 jar 但默认不生效，因此对正常部署无影响。

**一次性准备（服务器，需重启后端容器）**

dev 服务器实况：仓库在 `/root/HR`，分支只有 `master`，登录用户 `root`；已装 Compose v2。
**重建一律走 `docker compose`（v2）**——v1 1.29.2 与 Docker Engine 29 不兼容，任何 recreate 都会在"旧容器改名让位"
之后抛 `KeyError: 'ContainerConfig'`，结果服务直接消失（2026-11-17 实测踩实）。

```bash
cd /root/HR
git pull origin master
docker compose build backend                    # 镜像内加入 jacocoagent.jar，耗时比平时多几秒
docker compose -f docker-compose.yml -f docker-compose.coverage.yml config \
    | sed -n '/backend:/,/frontend:/p'         # 校验：JAVA_TOOL_OPTIONS 与 6300 都要出现，且 8080 仍在
docker compose -f docker-compose.yml -f docker-compose.coverage.yml up -d backend
docker logs --tail 50 hr-backend | grep -i "JAVA_TOOL_OPTIONS\|jacoco\|Started HrApplication"
```
最后一条必须打印 `Picked up JAVA_TOOL_OPTIONS: -javaagent:/opt/jacoco/jacocoagent.jar=...`，
没有就说明 agent 没挂上，先别采集。用完恢复：
`docker compose -f docker-compose.yml up -d backend`。

> 若这台机器用 v1 采集过，可能残留 `<容器id>_<name>` 形态的让位容器（v1/v2 共用同一套改名规则），
> v2 会以 `The container name "/xxx_hr-mysql" is already in use` 拒绝重建。
> 先确认这些容器不是当前在跑的服务（`docker ps -a`），再 `docker rm -f` 掉它们。

> 已知不一致（待单独修正，不影响本流程）：`docker/deploy.sh` 与 `.github/workflows/ci-cd.yml`
> 里写的是 `/opt/hr-system`、`git pull origin main`、`docker compose`，与实际服务器的
> `/root/HR`、`master` 两项不符，因此 CI 的部署阶段在这台机器上跑不通。

**采集通道**：overlay 默认把 tcpserver 只绑到服务器回环（`127.0.0.1:6300`），公网不可达。二选一
```bash
# 方式一（推荐）：本地另开窗口常驻 SSH 隧道，配置保持 host: 127.0.0.1
ssh -N -L 6300:127.0.0.1:6300 root@106.12.144.134

# 方式二：直连，需在服务器 /root/HR/.env 设置 JACOCO_DUMP_BIND=0.0.0.0 后重新 up -d，
# 并由云安全组把 6300 限制到指定来源 IP；采集时加 --dump-host 106.12.144.134
```

取部署字节码（`[准备]` 步骤）走的是同一条 ssh 通道，需要本机公钥已加入服务器 `authorized_keys`、
可以非交互执行 `docker exec`；不满足时脚本以退出码 2 停下，不会给出不可比的数字。

**每轮执行（本地，需先起好 SSH 隧道）**
```bash
cd D:\hr-system\tests
.venv\Scripts\python.exe coverage_gate.py                       # 取部署字节码 + 清零 + 全量用例 + 归因 + 门禁
.venv\Scripts\python.exe coverage_gate.py -k department         # 只跑部分用例，看这块用例集贡献了多少覆盖
.venv\Scripts\python.exe coverage_gate.py --check-only           # 不跑用例，只读上一轮清零之后新跑到的代码
.venv\Scripts\python.exe coverage_gate.py --update-thresholds    # 用实测值固化门禁下限（棘轮）
.venv\Scripts\python.exe coverage_gate.py --keep-classes         # 复用上一轮的字节码重算（调试用，非结论）
.venv\Scripts\python.exe coverage_gate.py --build                # 本地编译字节码（服务跑本机时的调试，非结论）
```

**输出**
- 终端：按包的行/分支/方法覆盖率表 + 合计 + 门禁判定，未达标退出码 1（可直接接 CI）
- `reports/coverage/<时间戳>/index.html`：JaCoCo 原生报告，可下钻到行号看未覆盖代码
- `reports/coverage/latest/`：指向最新一轮；`reports/coverage/summary.json`：机器可读，供后续 CI 阶段消费

**门禁口径**
- `config/coverage.yml` 的 `package_prefix` 决定统计范围（默认 `com.hr.`），`exclude_packages` 可把纯数据/配置包移出门禁；
  2026-11-18 口径已定：**不豁免任何包**，`dto`/`model`/`common`/`config` 一并计入，阈值按全量数字固化。
- `thresholds.line/branch` 为 `null` 时只测量不判定；核对后 `--update-thresholds` 写入下限（向下取整）。
  阈值只升不降：回退必须显式改配置并在评审中说明原因。
  **向下取整本身就是回退余量**：实测 69.91% 固化成 69，等于给 4 行以内的波动留了缓冲。
  所以"要不要把阈值上调到小数位"不是一个需要人工拍的决定——棘轮对同一轮实测是幂等的（`int(69.91) == 69`），
  跑一轮再执行 `--update-thresholds` 得到什么就是什么，只有跨整数上升才改变阈值。
- 用例存在 failed 时本轮覆盖率**不作为质量结论**（脚本会在判定后提示），先按「失败归因先于改用例」处理。
- 计数在采集前清零，所以只有**接口用例驱动的执行**计入覆盖；仅在应用启动阶段跑一次的代码
  （`@PostConstruct`、建表初始化、`@Bean` 装配、各层构造器）会显示为未覆盖，属口径设定而非缺陷。
  这条口径的代价是实测的：`com.hr.config` 整包 0%，加上各类构造器共约 91 行，占总行数的 20%。
  **口径已定（2026-11-18）：采用清零协议。** 装配代码写错的表现是容器起不来，用例集第一条请求就会失败，
  排除在外不损失信号；其中唯一有业务含义的 `UserDataInitializer`（首启建 admin）按 `TC-DEL-007` 的先例
  归入需要数据库直连的手工/集成用例，不塞进接口自动化。冷启动协议（重启后端 → 跑一轮 → 取数时不清零）不采用：
  它要求每次测量都中断一次共享服务，而且度量的是部署行为而不是用例集的有效性。
- **`.exec` 每轮必须重建**：`jacoco:dump` 对 `destFile` 是追加合并而不是覆盖，脚本因此在每次 dump 前先删掉
  `backend/target/jacoco-api.exec`，且把"只为清零计数器"的那次取数直接丢弃。手工调用 mvn 目标采集时若忘了删，
  报告就变成历轮并集——门禁将永远测不出覆盖率下降，`-k` 也测不出单块用例集的贡献。
  `--check-only` 只删旧文件、不清零 agent 计数，读的是自上次清零以来的累计覆盖。
- **两个覆盖率通道各写各的执行数据文件**：接口用例通道用 `jacoco-api.exec`（脚本 dump 落地），
  单元测试通道用 maven 默认的 `jacoco.exec`（`pom.xml` 里 `prepare-agent` 挂给 surefire）。
  出报告时脚本显式传 `-Djacoco.dataFile`，否则 `jacoco:report` 会读默认名的 `jacoco.exec`，
  本机跑过一次 `mvn test` 就把接口覆盖率的数据源换掉了，而且数字看起来"正常"。
  两个通道的数字**不能相加也不能互相印证**：门禁判定只认接口用例通道；单元测试通道走 `mvn test`，
  它度量的是单元测试写得好不好，回答不了"接口用例集覆盖了系统多少代码"。
- **字节码口径决定数字是否可信**：执行数据与字节码按 class id（类文件内容哈希）匹配，报告默认在采集前
  用 `config/coverage.yml` 的 `deploy.ssh` 从运行中的容器取回 `BOOT-INF/classes` 覆盖 `backend/target/classes`，
  保证出报告用的就是实际执行的那份。本机 javac 与构建镜像的 JDK 补丁版本不同就会产出不同的类文件，
  id 对不上的类被 JaCoCo **静默丢弃**（显示 0% 而不是报错）——2026-11-17 实测因此丢掉了整个 `EmployeeService`，
  `com.hr.service` 只报 45.05%，而取回部署字节码后的干净单轮是 83.52%。
  `--build`（本地编译）只在服务跑在本机时用于调试，`--keep-classes` 用于对同一轮数据复算，
  两者的数字都不作为覆盖率结论。
- coverage overlay 只用于 dev/test；生产环境不启用，也不要把 6300 开放到公网。

**干净单轮实测（2026-11-18 上午，128 passed 同轮，字节码来源 = 部署容器，连跑两轮完全一致）**

下表为接口收敛前（`/api/employees/meta/departments` 仍在代码里时）的口径。

| 口径 | 实测 | 门禁下限 | 说明 |
| --- | --- | --- | --- |
| 行 | **69.91%**（323/462） | 69 | 最低的是 `com.hr.config` **0/52**：`RedisConfig`/`WebConfig`/`UserDataInitializer` 只在应用启动时执行，清零后被口径排除；其余缺口是各层构造器 |
| 分支 | **70.00%**（56/80） | 70 | 未覆盖分支集中在 JDBC 层判空（主键/COUNT 返回 null，接口打不到）与 `appendFilters` 的 name/department 空白组合 |
| 方法 | 75.00%（135/180） | 不计入门禁 | 仅用于定位漏测的方法 |

补 4 条 `TC-META-*` 之前，同口径基线是 124 passed / 行 **69.48%**（321/462）/ 方法 73.89%（133/180）、分支不变
（该组数字连跑三轮完全一致，可复现）。多出的 2 行 2 方法正是 `EmployeeController.departments()` 与
`EmployeeService.departments()`，`jacoco.xml` 复核两者 `covered=1 / missed=0`。

这一轮最初暴露的两个**真实缺口**（不是口径问题）现均已闭环，但处理方式和一开始的设想不同：

① `GET /api/employees/meta/departments` 无任何用例调用 —— 先按"补用例"处理（`TC-META-001~004`），
复核源码时发现它是部门字典的**重复实现**：`EmployeeService.departments()` 只是 `DepartmentService.allNames()`
的一行委托，无附加逻辑，前端员工表单下拉走的是 `/api/departments/meta/names`，全仓库没有任何消费方。
最终按**接口收敛**处理（2026-11-18）：后端移除该端点及其服务方法，一并删掉无调用方的遗留查询
`EmployeeRepository.findDepartments()`；`TC-META-001~004` 随之作废（编号不回收，表内保留追溯行），
其中"未认证"这一判定点不随接口消失，迁到唯一字典入口新增 `TC-DN-003`。
**给零覆盖的重复代码补用例不是目标，删掉重复才是**——这是覆盖率归因跑出来的第二个非口径结论。
归因粒度足以支撑这个判断：删掉 4 条用例但后端字节码还没换的那一轮（2026-11-18 14:03）实测
124 passed / 行 **321/462 = 69.48%** / 方法 133/180，与补用例之前的基线**逐字相同**，
说明那 2 行 2 方法确实只由这 4 条用例驱动，不是别处的副作用。

② `AuthService.login` 的「账号已停用」分支接口侧无法触达 —— 走的是**单元测试通道**：
`sys_user` 没有写入口（首启固定 `enabled=1`），dev 库 3306 又只绑服务器回环，测试机无法直连造前置数据。
`backend/src/test/java/com/hr/service/AuthServiceTest.java` 用 Mockito 直接驱动该分支，
`mvn test` 实测 `AuthService` 行 12/12、分支 4/4。`login` 的其余三个分支仍由接口用例锚定，单元测试不重复。

**为什么数字比 2026-11-17 记录的 89.18% 低**：那批数字是脏的，两个污染源——
① `jacoco:dump` 对 `destFile` 是**追加合并**，历轮数据全攒在 `backend/target/jacoco.exec` 里，报告算的是并集；
② 并集里还混着容器启动那一刻的**启动期覆盖**（config 整包 + 各层构造器 ≈ 91 行），而清零协议下这部分按口径不计入。
同一子集用例，保留旧 `.exec` 时报 89.18%，删掉后同一命令报 49.57%——这就是判据。

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
- **覆盖率归因与门禁**：接口用例驱动后端 JaCoCo agent，按包统计被测系统的行/分支覆盖，阈值棘轮只升不降
- **分层架构**：接口封装、数据、断言、用例分离，可跨项目复用同一套骨架
