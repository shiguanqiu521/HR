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
├── Dockerfile              # 执行平面（runner）镜像：固化 mvn + python 依赖，用例代码靠 bind mount 进来
├── .dockerignore           # 构建上下文白名单，只带 requirements.txt（环境文件不进镜像层）
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
| dev 实测（2026-11-18 下午，接口收敛后重建部署、覆盖率门禁同轮） | 22 | 72 | 31 | **125 passed / 0 failed / 0 skipped**，26.15s |
| runner 容器内实测（2026-11-18 晚，与被测后端同机） | 22 | 72 | 31 | **125 passed / 0 failed / 0 skipped**，4.30s（同轮覆盖率见下节，与本地逐字相同） |
| Jenkins 执行平面预检（2026-11-19，`runner` 非 root + docker 组，`--deploy-mode file`） | 22 | 72 | 31 | **125 passed / 0 failed / 0 skipped**，4.55s（JUnit 段）+ 4.20s（门禁同轮），行 70.09% 与基线逐字相同 |

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

> 需要可复现的执行环境（不依赖某个人本机装了什么）时，用 runner 镜像代替这套本机 venv：
> `docker build -t hr-testrunner -f tests/Dockerfile tests/`，形态与限制见「覆盖率归因与门禁 → 执行平面与流水线」。

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
    | grep -nE "JAVA_TOOL_OPTIONS|host_ip|published"
docker compose -f docker-compose.yml -f docker-compose.coverage.yml up -d backend
docker logs --tail 50 hr-backend | grep -i "JAVA_TOOL_OPTIONS\|jacoco\|Started HrApplication"
```
校验那条只 grep 要确认的三类行：`JAVA_TOOL_OPTIONS` 出现、6300 上方带 `host_ip: 127.0.0.1`、8080 仍在。
**不要**图省事用 `sed -n '/backend:/,/frontend:/p'` 打印整段 service 块——`docker compose config` 输出的是
解析后的最终值，backend 的 `environment` 里含 `SPRING_DATASOURCE_PASSWORD`、`SPRING_DATA_REDIS_PASSWORD`、
`HR_AUTH_JWT_SECRET`，整段打印等于把三个明文密钥打到屏幕上（还会进 shell 历史与任何录屏）。
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

取部署字节码（`[准备]` 步骤）有**两条通道**，由 `config/coverage.yml` 的 `deploy.mode` 选择：
`ssh`（默认）复用上面那条 ssh 通道现场取，需要本机公钥已加入服务器 `authorized_keys`、能非交互执行 `docker exec`；
`file` 读部署步骤 `docker cp` 落盘的 `deploy.local_jar`，不需要 ssh 免密、也不需要 docker 权限，给 CI / 同机执行用。
两条通道已实测**逐字节一致**（同一份部署产物各取一次，30 个 class 的 sha256 全等），所以两个平面的数字能互相印证。
任一通道不满足时脚本以退出码 2 停下，不会给出不可比的数字。

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

**执行平面与流水线（"在哪跑"也要固化成产物）**

三个平面各归各处：**被测环境**只负责被测（`/root/HR` 上的 hr-backend），**执行平面**负责装工具链、跑用例、出报告，
**产物存储**负责让人看到（CI artifact / Pages / Allure 服务）。覆盖率报告**不在被测服务器上**，也不是遗漏：
JaCoCo 的计数器在被测 JVM 内部，但驱动它的是外部请求，所以形态是"被测侧留 agent 端口 → 执行侧拉数据出报告 →
产物侧存历史"。被测机器上既没有 mvn 也不该有——它是 runtime 镜像，连编译器都不带。

本项目的执行平面实况是：服务器 `mvn MISSING`、pypi 公网源全断（百度云内网源可用），所以工具链固化成镜像：

```bash
cd /root/HR
docker build -t hr-testrunner:$(git rev-parse --short HEAD) \
  --build-arg PIP_INDEX_URL=http://mirrors.baidubce.com/pypi/simple \
  --build-arg PIP_TRUSTED_HOST=mirrors.baidubce.com \
  -f tests/Dockerfile tests/
```

`PIP_TRUSTED_HOST` 不是可选项：内网镜像源只提供 HTTP 时 pip 会**静默忽略**这个索引，
报的是 `Could not find a version ... (from versions: none)`，看不出真实原因是索引被跳过（2026-11-18 实测踩过）。

```bash
# 每轮：先由部署步骤落盘字节码，再在 runner 容器里跑门禁（$WS 就是工作区，本机的 /root/HR 或 CI 的 workspace 都一样）
docker cp hr-backend:/app/app.jar backend/target/deployed/app.jar
docker run --rm --network host -e TZ=Asia/Shanghai \
  -v $WS:/workspace \
  -v /home/runner/.m2:/root/.m2 \
  -v $WS/backend/settings.xml:/root/.m2/settings.xml:ro \
  hr-testrunner:latest python3 tests/coverage_gate.py --deploy-mode file
```

- `--network host`：容器里 `127.0.0.1` 就是宿主回环，才能直连 8080 与只绑回环的 6300，不需要 SSH 隧道。
- **不挂 `/var/run/docker.sock`**：那等于把宿主机 root 交给测试通道（这台机器的 3306 曾被公网打穿过，见评审记录）。
  代价就是字节码不能现场 `docker exec` 取，改用 `deploy.mode=file` 读部署步骤落盘的 jar——权限与可信度都要保住。
- maven 本地库用执行账号自己的目录（CI 用 `/home/runner/.m2`，本机手动跑用 `/root/.m2`）持久化。
  首轮要下载 jacoco 插件与 spring-boot parent，之后复用。
- `-e TZ=Asia/Shanghai`：镜像默认 UTC，不加则 `reports/coverage/<时间戳>` 目录名和 `summary.json.captured_at`
  比宿主时间早 8 小时（实测：不带 09:41 UTC，带了 17:41 CST）。
- `deploy.mode` 默认仍是 `ssh`（本机驱动远端部署是对的），CI 用 `--deploy-mode file` 在命令行上覆盖，
  不为切通道维护第二份 yml（早期用 `sed` 生成 `tests/logs/coverage.ci.yml` 的写法已废弃）。
- 执行平面的账号**不需要 root，但需要 docker 组成员身份**（`usermod -aG docker runner`）。
  组成员身份在登录时分配，加组后必须重连 agent/重新登录才生效——这是最容易误判成"权限没加上"的坑。
  诚实说明：docker 组等价于宿主 root，真正的隔离需要第二台构建机，这台机器既是生产又是被测环境，做不到。
- CI 里 `tests/config/.env.dev` 由**凭据现场生成**（`.gitignore:31` 决定了它不进版本库）：
  `withCredentials` 注入 `hr-api-admin`（Username/Password）与 `hr-jwt-secret`（Secret text），
  以 `umask 077` 写进工作区，日志里只打印键名与值长度。缺这个文件时 `switch_env("dev")` 直接抛
  `FileNotFoundError`，pytest 一条也收集不到；`HR_JWT_SECRET` 为空则 `TC-AUTH-014` 按条件跳过，基线少一条用例。

**两个平面的等价性实测（2026-11-18 晚，同一部署、同一用例集）**

| 平面 | 字节码通道 | 用例执行 | 行 | 分支 | 方法 | 门禁 |
| --- | --- | --- | --- | --- | --- | --- |
| 本地 Windows（SSH 隧道 + 公网打 8080） | `deployed-ssh` | 125 passed，22.18s | 321/458 = 70.09% | 56/80 = 70.00% | 133/177 = 75.14% | 通过 |
| runner 容器（同机、打 127.0.0.1） | `deployed-file` | 125 passed，4.30s | 321/458 = 70.09% | 同上 | 同上 | 通过 |
| runner 容器复现轮 | `deployed-file` | 125 passed，4.12s | 321/458 = 70.09% | 同上 | 同上 | 通过 |

三轮的**分包明细也逐项相同**（八个包，含 `com.hr.config` 0/52、`com.hr.service` 76/89），
说明这个数字不是某台机器的偶然；容器侧快 5 倍是网络往返的差，与覆盖无关。
`summary.json.meta.classes_source` 会写明本轮用的是 `deployed-ssh` 还是 `deployed-file`，
每轮报告都能自证字节码来源，不必靠人记。

**流水线形态（仓库根 `Jenkinsfile`）**

调度器是 Jenkins 控制器（Windows 本机），执行平面是服务器上的 SSH agent（`cloud-server`，label `cloud`，
非 root 的 `runner` 账号）。阶段与用途：

| 阶段 | 干什么 | 失败时最先怀疑什么 |
| --- | --- | --- |
| Checkout | `retry(3)` 拉 master（这台机器到 github.com 偶发 TLS reset，实测 5 次 1 次失败） | 网络，不是代码 |
| 执行平面自检 | 验 docker 权限、agent 挂载、8080 有应答、6300 可达、`backend/settings.xml` 在位 | 没重连 agent（加组不重连等于没加）；后端没用 coverage overlay 重建 |
| Runner 镜像 | 镜像缺失或 `REBUILD_RUNNER=true` 才 build，之后 `pytest --version` + `mvn -v` 复验 | 内网 pip 索引少了 `PIP_TRUSTED_HOST` |
| 执行平面配置 | `withCredentials` 生成 `tests/config/.env.dev`（0600，日志只出键名与长度） | 凭据 ID 或类型不对 |
| 接口用例 | 容器里跑 pytest 出 `tests/reports/junit.xml`，只为 JUnit 结果与趋势 | 用例本身；覆盖率不会因此算重（门禁首步清零并丢弃那次取数） |
| 部署字节码落盘 | `docker cp` 运行中容器的 `/app/app.jar`，打印字节数、sha256 前缀、容器与镜像 ID | 报告可信度的来源，日志里可追溯是哪份产物 |
| 覆盖率门禁 | `coverage_gate.py --deploy-mode file`，未达标退出码 1 让构建变红 | 阈值回退 |
| post | `junit` + `archiveArtifacts`（`summary.json`、JaCoCo `index.html`/`xml`/`csv`）；构建末尾打印 `classes_source` 与三项实测值 | — |

建 job：New Item → **Pipeline** → Pipeline script from SCM → Git，URL 用官方
`https://github.com/shiguanqiu521/HR.git`、Branch `master`、Script Path `Jenkinsfile`（仓库公开，无需凭据；
不用 `gh-proxy` 之类第三方镜像，因为 Jenkinsfile 本身经此通道下发并会持有凭据，不该让镜像站进这条链路）。
两个刻意设定：**`disableConcurrentBuilds()`**——JaCoCo 计数器是被测 JVM 里的一份全局状态，并发构建会互相清零；
**不开 `cleanWs()`**——容器内 root 在 gitignore 目录里留下 0644 产物，runner 读得到（归档正常）但删不掉，
工作区一清就让构建无故变红。

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
  余量随基数变化，不要把它当固定额度：458 行时 1 行就是 0.22pp，实测 70.09% 取整成 70 只剩 0.09pp（不足 1 行）。
  这一档可用是因为同一 JVM 的稳态轮逐行完全可复现（见下节实测），真正的风险只剩"少覆盖一行"这一类信号，
  而那正是门禁要报的东西。
  "只升不降"和"保留复核依据"现在由 `update_thresholds()` 代码保证，不再靠口头约定：实测取整后不高于现有下限时
  原样保留并打印说明（否则一次失败轮就会把下限悄悄拉低）；写回时只替换数值本身，行内注释留着记"这个下限由哪一轮得出"。
- **容器重启后的首轮比稳态轮高 1 行，阈值只认稳态轮**：清零协议清的是计数器，不是类加载状态。
  `PasswordHasher` 的静态字段初始化（`private static final SecureRandom RANDOM = new SecureRandom();`）
  在整个 JVM 生命周期里只执行一次——重启后第一次登录若落在测量窗口内，这行记为已覆盖，之后每一轮都记为未覆盖。
  2026-11-18 同一部署、同一用例集实测：重启后首轮 322/458=70.31%，其后各轮稳定 321/458=70.09%，方法数同步差 1
  （`<clinit>` 本身算一个方法）。这是 `com.hr.config` 整包 0% 那条口径的镜像，不是用例不稳定。
  固化阈值前先在目标 JVM 上跑一轮丢弃，或直接把首轮读高 1 行计入理解。
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
  按 `deploy.mode` 取回运行中的 `BOOT-INF/classes`（`ssh` 现场取 / `file` 读落盘 jar）覆盖 `backend/target/classes`，
  保证出报告用的就是实际执行的那份。本机 javac 与构建镜像的 JDK 补丁版本不同就会产出不同的类文件，
  id 对不上的类被 JaCoCo **静默丢弃**（显示 0% 而不是报错）——2026-11-17 实测因此丢掉了整个 `EmployeeService`，
  `com.hr.service` 只报 45.05%，而取回部署字节码后的干净单轮是 83.52%。
  `--build`（本地编译）只在服务跑在本机时用于调试，`--keep-classes` 用于对同一轮数据复算，
  两者的数字都不作为覆盖率结论。
- coverage overlay 只用于 dev/test；生产环境不启用，也不要把 6300 开放到公网。

**干净单轮实测（2026-11-18 下午，接口收敛并重建部署后，125 passed 同轮，字节码来源 = 部署容器）**

| 口径 | 实测（稳态轮） | 门禁下限 | 说明 |
| --- | --- | --- | --- |
| 行 | **70.09%**（321/458） | **70**（本轮由棘轮从 69 抬起） | 分母 462→458 全部是被删掉的**未覆盖**行（下表逐处核对），已覆盖行数 321 一个没变——行% 上升纯粹来自分母缩小，不是覆盖增加 |
| 分支 | **70.00%**（56/80） | 70 | 分支总数不受收敛影响（删掉的三处都没有判定）；未覆盖分支仍集中在 JDBC 层判空（主键/COUNT 返回 null，接口打不到）与 `appendFilters` 的 name/department 空白组合 |
| 方法 | 75.14%（133/177） | 不计入门禁 | 180→177 是删除的三个方法，此前均为未覆盖；仅用于定位漏测的方法 |

容器重启后的首轮读作 **322/458 = 70.31%、方法 134/177**，与稳态轮只差 `PasswordHasher` 的静态字段初始化那一行
（见上一节口径条）；上表取的是稳态轮，15:06 与 15:17 两轮逐项逐字相同，抬起后的阈值 70 在 15:17 那轮按
`实测 70.09% / 阈值 70% → 达标` 实际判定过一次。

收敛删除的行数逐处核对（14:03 那轮 vs 15:06 那轮，均取部署字节码）：

| 删除位置 | 减少的可执行行 | 说明 |
| --- | --- | --- |
| `EmployeeController.departments()` | 1 | 注解与方法签名行不计为可执行行，只有 `return` 那一行；此前该端点无用例，一直是未覆盖 |
| `EmployeeService.departments()` + 构造器里对 `DepartmentService` 的字段赋值 | 2 | 方法体 1 行未覆盖；字段赋值在启动期执行，清零口径下同样计为未覆盖 |
| `EmployeeRepository.findDepartments()` | 1 | 跨 3 个源码行的 `queryForList` 调用按 JaCoCo 口径记 1 行；零调用方 |

同口径历史数字（便于对照）：接口收敛前补上 4 条 `TC-META-*` 的那一轮（11:50）是 128 passed /
行 **69.91%**（323/462）/ 方法 75.00%（135/180）——多出的 2 行 2 方法正是 `EmployeeController.departments()` 与
`EmployeeService.departments()`，`jacoco.xml` 复核两者 `covered=1 / missed=0`；删掉那 4 条用例而字节码未换时
（14:03）回到 124 passed / 行 **69.48%**（321/462）/ 方法 73.89%（133/180），与更早的基线逐字相同，连跑三轮完全一致。

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
重建部署后的两轮（15:00、15:06）分母如期降到 458、已覆盖行数不变，收敛落地。
带 token 复核线上行为时还发现：已移除的 `/api/employees/meta/departments` 返回的是 **500 `No static resource ...`**
而不是 404——任意未映射路径同样如此，即这是全局异常处理把 `NoResourceFoundException` 归到了 `Exception` 分支，
属既有缺陷（见评审清单 D7），与本次收敛无关，但收敛让它第一次有了可复现的观察入口。

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
