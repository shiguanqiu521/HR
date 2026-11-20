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
.venv\Scripts\python.exe coverage_gate.py --checkout-classes DIR # 出报告前先断言"部署包 == 本次检出编译产物"
# 本地这几条只测环境上现装的那份包，不改部署。要让它等于本次提交，先在服务器上构建并部署：
#   docker compose -p hr -f docker-compose.yml -f docker-compose.coverage.yml up -d --build --no-deps backend
# （CI 里这一步已由「部署本次提交」段代劳，见下节）
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
# 每轮第一步：从本次检出构建并部署被测后端（Compose v2，project 名必须与被测环境一致）
cd $WS   # 本机手跑 $WS=/root/HR；CI 是 /home/runner/workspace/hr-api-coverage-gate
set -a; . ./.env; set +a                      # 口令从 .env 进环境变量，不进命令行、不进 shell 历史
docker compose -p hr -f docker-compose.yml -f docker-compose.coverage.yml \
  up -d --build --no-deps backend
# 之后：落盘部署字节码，在 runner 容器里跑门禁
docker cp hr-backend:/app/app.jar backend/target/deployed/app.jar
# 编译本次检出的源码到隔离副本（不要在 backend/ 里编，原因见下节「部署一致性断言」）
mkdir -p $WS/.ci-verify && cp -R backend/pom.xml backend/settings.xml backend/src $WS/.ci-verify/
docker run --rm -v $WS/.ci-verify:/verify -v /home/runner/.m2:/root/.m2 \
  -v $WS/backend/settings.xml:/root/.m2/settings.xml:ro \
  hr-testrunner:latest mvn -B -q -DskipTests compile -f /verify/pom.xml
docker run --rm --network host -e TZ=Asia/Shanghai \
  -v $WS:/workspace \
  -v /home/runner/.m2:/root/.m2 \
  -v $WS/backend/settings.xml:/root/.m2/settings.xml:ro \
  hr-testrunner:latest python3 tests/coverage_gate.py --deploy-mode file \
    --checkout-classes /workspace/.ci-verify/target/classes
```

- `--network host`：容器里 `127.0.0.1` 就是宿主回环，才能直连 8080 与只绑回环的 6300，不需要 SSH 隧道。
- **不挂 `/var/run/docker.sock`**：那等于把宿主机 root 交给测试通道（这台机器的 3306 曾被公网打穿过，见评审记录）。
  代价就是字节码不能现场 `docker exec` 取，改用 `deploy.mode=file` 读部署步骤落盘的 jar——权限与可信度都要保住。
- maven 本地库用执行账号自己的目录（CI 用 `/home/runner/.m2`，本机手动跑用 `/root/.m2`）持久化。
  首轮要下载 jacoco 插件与 spring-boot parent，之后复用。
  **注意一个静默坑（2026-11-19 实测）**：这台机器上 `/home/runner/.m2/settings.xml` 与 `/root/.m2/settings.xml` 都是
  **0 字节文件**，整个目录挂进容器当 `/root/.m2` 会让 maven 直接 `Non-readable settings ... input contained no data` 失败。
  流水线之所以能跑，是因为每条 `docker run` 都再用 `-v $WS/backend/settings.xml:/root/.m2/settings.xml:ro` 把它覆盖掉——
  手动复跑时漏掉这个挂载就会得到一条与真实原因无关的报错。
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

**部署一致性断言（`--checkout-classes`，2026-11-19 加）**

门禁统计的是**部署**字节码，流水线声称验证的却是**本次检出**的提交；在"测环境上现装的包"这种形态下两者并不自动相等。
2026-11-19 就实测到过偏离：CI 检出 `c8949ca`，服务器 `/root/HR` 停在 `3b88893`，容器里的 `app.jar` 更是 11-18 14:56
构建的——只是那之后 `backend/` 恰好零改动（`git diff 3b88893 c8949ca -- backend/` 为空），数字才仍然成立。**绿灯是巧合，不是保证。**

于是门禁在覆盖 `backend/target/classes` **之前**，把本次检出编译出的每个 `.class` 与部署包 `BOOT-INF/classes/**.class` 逐文件比 sha256：

- 全等 → 打印「部署一致性断言通过（N 个 class 逐文件 sha256 相同）」，`summary.json.meta` 记 `checkout_verified=true` 与比对数；
- 不一致 → 退出码 2，列出 `DIFF` / `ONLY-CHECKOUT` / `ONLY-DEPLOYED`，且**在跑用例与清零之前**就停，不留半轮脏计数；
- 目录不存在或一个 `.class` 都没有 → 同样失败。断言不能因为「没编译」就默认通过，否则这条检查只是装饰；
- 不给这个参数 → `checkout_verified=null`，报告末尾明说"数字属于环境上现装的包"。

**为什么要编到 `.ci-verify/` 而不是 `backend/`**：门禁会用部署字节码覆盖 `backend/target/classes`。若就在 `backend/` 里编，
下一轮 maven 增量编译会因源码未变、class 时间戳更新而**跳过重编**，"本次编译产物"其实是上一轮留下的部署 class，
断言就变成拿部署字节码和自己比、永远为真。隔离副本每轮 `rm -rf` 重建，比的才是真编译结果。

**为什么用字节码比对而不是"部署时往 jar 里写 commit 标签"**：标签依赖每次部署都有人记得传，漏一次就静默退化；
字节码比对不需要任何人自觉，直接证明"环境里这份包就是这份源码编出来的"。代价是对构建环境敏感——
**部署镜像与 runner 的 JDK 补丁版本不同时，会出现源码相同、字节不同的假红**。本项目 `backend/Dockerfile` 构建阶段与
`tests/Dockerfile` 同为 `maven:3.9-eclipse-temurin-17`，2026-11-19 实测同镜像下 30 个 class 逐文件全等，
所以选择宁可假红（安全）也不要假绿。

拦截能力是在服务器上拿真实产物测出来的，不是构造的单测：

| 场景 | 结果 |
| --- | --- |
| 改 `HealthController.java` 但不重新部署 | 拦住：`字节不同：1 个` + `DIFF com/hr/controller/HealthController.class` |
| 新增类但不重新部署 | 拦住：`本次编译 31 个 class、部署 30 个` + `ONLY-CHECKOUT com/hr/CiProbeAddedClass.class` |
| 未改动的本次检出（正向） | 通过：30 个 class 全等，`125 passed`，行 70.09% / 分支 70.00%，门禁通过；含编译整轮 14 秒 |

**部署段（`部署本次提交`，2026-11-19 加）**

流水线自己从本次检出构建镜像并部署，"测的这份包就是这份提交"从此由构造保证，不再依赖有人在服务器上 `git pull` 过。
四个设计点，每个都对应一条实测：

- **`-p hr` 不是可选项**。被测栈现有 project 就叫 `hr`（`docker compose ls` 与容器的 `com.docker.compose.project`
  标签都证实），卷叫 `hr_mysql-data`、网络叫 `hr_default`。project 名一换，compose 会得到**另一套容器 + 一个空库**，
  用例在空库上跑出来的数字毫无意义，还白占 8080/6300 端口冲突。
- **`--no-deps` 只重建 backend**。mysql/redis 的生命周期归服务器运维，流水线不启动、不重启、更不会删它们的数据卷。
  自检段因此新增硬前置：`hr-mysql`/`hr-redis` 必须 `running/healthy`，缺了立刻报错，
  而不是等部署段的登录探活转满 120 秒后报一句误导性的"后端没就绪"。
- **口令走 compose 的进程环境变量，不落第二份 `.env`**。`withCredentials` 注入 `MYSQL_ROOT_PASSWORD`、
  `REDIS_PASSWORD`、`HR_AUTH_JWT_SECRET` 三个变量名，compose 插值时直接读环境（实测哑元注入后
  `docker compose config` 解析出的 `SPRING_DATASOURCE_URL`/`SPRING_DATA_REDIS_PASSWORD` 全部到位）。
  这样 runner 不需要、也确实拿不到 `/root/HR/.env`（`/root` 是 `drwx------`）。`MYSQL_DATABASE` 不是凭据，
  用 compose 里的 `:-hr_db` 默认值，已核对与服务器 `.env` 一致。
- **就绪判据是真登录，不是 `/api/health`**。后者硬编码返回 UP（已知缺陷 D4），"进程起来了但连不上库"这种状态
  它会照样放行，然后 125 条用例整片红在原因之外。探活直接 POST `/api/auth/login` 并检查响应里有 `"token"`，
  登录体由 python 从 `tests/config/.env.dev` 现读现拼、经管道送进 curl —— 口令既不落盘也不进 argv（`sh` 步骤带 `-x`，
  命令行原文会进构建日志）。40 次 × 3 秒兜底，超时才打容器日志里的 `ERROR|Exception|Caused by` 行。

**#11 踩中的坑：`-p` 传成了空值（2026-11-19，三条修复都已实测过正反两个方向）**

`docker compose -p  -f ... up` —— 日志里那个空位就是它。compose 在 `-p` 为空时**不报错**，退回按当前目录名推导
project（工作区目录叫 `hr-api-coverage-gate`），于是它新建了 `hr-api-coverage-gate_default` 网络与
`hr-api-coverage-gate_mysql-data`/`_redis-data` 两个**空库卷**，最后撞在容器名冲突上：
`Conflict. The container name "/hr-backend" is already in use`。根因不是 compose，是 Jenkins 的参数注入语义：

> **Jenkins 只把"本次构建参数表里已有的"参数导成环境变量。**新加的参数在它第一次被注册之前的那一轮拿不到，
> shell 里 `${COMPOSE_PROJECT}` 就是空串；而 Groovy 侧 `params.X` 会退回 `parameters{}` 声明的默认值
> （所以同一轮里 `withCredentials` 用的两条新凭据 ID 完全正常）。**两种取值路径不一致**，
> "只在 shell 里用"的新参数才是盲区。#11 的凭据绑定成功、`-p` 为空，就是这个不对称的现场证据。

三层修复，都验过：

| 修复 | 位置 | 实测 |
| --- | --- | --- |
| 顶层 `environment { COMPOSE_PROJECT = "${params.COMPOSE_PROJECT ?: 'hr'}" }` 显式兜底 | `options` 之后 | — |
| 自检段对"只在 shell 里用"的五个参数逐个显式判空，空值立刻停并给处置办法 | `执行平面自检` | 复刻 #11 的参数集（缺 `COMPOSE_PROJECT`）→ 退出码 1；补上 → 放行 |
| **project 归属以运行中的容器为准**：`docker inspect` 读 `com.docker.compose.project` 标签，与要用的 `-p` 不符就停在 `up` 之前 | `部署本次提交` | `hr` → 放行；空值与 `hr-test` → 都拦下，并说明"继续会另起一套空库卷" |

第三条是关键：参数对不对，不看配置、看**被测容器身上写的归属**。否则一次填错就能让 125 条用例在空库上跑完，
出一个数字看着完全正常、结论却毫无意义 —— 比红掉危险得多。

失败轮留下的孤儿资源这样查与清（本次三个卷/网络都是空目录、无任何容器引用才删）：
```bash
docker network ls --format '{{.Name}}' | grep <错误的project名>
docker volume ls --format '{{.Name}}' | grep <错误的project名>
for v in <卷名>; do echo -n "$v -> "; docker ps -a -f volume="$v" --format '{{.Names}}'; done   # 必须为空
docker volume rm <卷名...> && docker network rm <网络名> && docker rmi <错误project>-backend:latest
```

耗时与扰动都是实测：镜像构建在依赖层命中缓存时 **36 秒**（其中 `mvn clean package` 26 秒），缓存全冷 **199 秒**；
探活块对着运行中的容器跑通只花 **0.1 秒**（第 1 次探测就拿到 token）。预跑用一次性 project 与哑元凭据完成，
`hr-backend` 容器的 ID 与 `StartedAt` 前后一致——**没有扰动生产容器**，真正的 recreate 留给第一次真实构建，
`tests/logs/deploy.log`（0600）里能看到 `Recreated` 还是 `Running`，两种都正常。

顺带消掉一个口径歧义：`PasswordHasher.<clinit>` 那 +1 行只在"重启后的第一次登录落在测量窗口内"时才记为已覆盖，
而探活的这次登录发生在门禁清零**之前**，所以无论容器重建与否，门禁量到的都是稳态的 321/458 = 70.09%。

**#15 踩中的坑：`sh` 步骤的解释器不是 bash，是 dash（2026-11-19）**

#15 在第 2 段就停了，日志只有一行有用的：

```
/home/runner/workspace/hr-api-coverage-gate@tmp/durable-.../script.sh.copy: 14: Bad substitution
```

第 14 行是上一节为修 #11 加的参数判空循环，写的是 `eval "val=${$v:-}"`（用变量名取变量值）。
服务器上 `/bin/sh -> dash`，而 **dash 没有 `${!name}`、也没有 `${$name}` 这种间接展开**。Jenkins 的 `sh` 步骤
用的就是 `/bin/sh`，所以整块直接报错。三条这次一起踩出来的教训：

1. **`sh -n` 和本机 bash 都抓不到这类错**。本机 Git Bash 的 `bash -n` 通过；更反直觉的是
   **`dash -n` 也通过** —— 因为 `${$v:-}` 不是语法错，是**展开期**错误，`-n` 只解析不执行。
   要抓它只有一条路：**用 dash 真跑一遍**。
2. **校验方法（可复用，跨项目同样适用）**：把 Jenkinsfile 里的 `sh '''…'''` 块原样取出塞给 Groovy
   自己的词法器解串（别手搓转义规则：`\\` 才是续行，`\` + 换行会被 Groovy 吃掉换行），
   然后在**临时工作区 + 桩 PATH**（`docker`/`curl`/`mvn`/`python3`/`bash`/`sleep` 全部替身）下逐块
   `sh -x` 跑。这样既覆盖到展开期，又不碰被测服务。判定看两点：解释器不得报 `Bad substitution`/
   `not found`/语法错，且成功路径模式下每块必须跑到最后（rc=0）——否则说明有的分支从没被执行过。
   这套校验的**有效性是反证过的**：拿 #15 那版（改前）跑，它精确复现了 `14: Bad substitution`，
   行号与 Jenkins 日志一致；拿改后版本跑，10 块在 dash 下全部跑到最后，成功/失败两种桩各一轮。
3. **写进规约**：Jenkinsfile 的 `sh` 块按 POSIX sh 写。需要 bash 特性（`/dev/tcp`、数组、`${var//}`、
   间接展开）时**显式 `bash -c '…'`**，别让它们混在默认解释器里 —— 部署段的 6300 探活就是这么写的，
   所以它没事，而判空循环那么写就红了。

**#16 踩中的坑：容器以 root 往工作区写，下一轮的 `rm -rf` 就删不动了（2026-11-19）**

#15 的 dash 问题修好后，构建一路走到了第 8 段（部署段第一次真跑：`Container hr-backend Recreated`、
新镜像 `8bb3b5985a3f`、6300 可达、登录第 6 次探测拿到 token、`125 passed in 7.72s`），
然后死在「本次提交编译」段的**第一行**：

```
rm: cannot remove '.ci-verify/target/classes/com/hr/...': Permission denied   × 35
ERROR: script returned exit code 1
```

根因与流水线逻辑无关，是**属主**：`mvn` 在容器里是 root，产出直接写进宿主挂载的 `.ci-verify/target`，
于是那份 `target` 是 `root:root`；下一轮构建的 `rm -rf .ci-verify` 由 agent 的 `runner` 执行，
删不掉别人属主的目录。**这不是偶发，是结构性的——不改写法每一轮都会红在同一个地方。**
同一类残留在工作区里还有几处（`logs/`、`tests/reports/coverage`、`backend/target/classes`、各处 `__pycache__`），
区别只在于流水线从不从宿主侧删它们，所以照跑不误（也就是下一节"不开 `cleanWs()`"的原因）。

改法是在**产生残留的那一步**收尾，而不是绕开删除：

| 改动 | 作用 |
| --- | --- |
| `docker run` 加 `-e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)"`，容器命令包成 `sh -c 'mvn …; rc=$?; chown -R "$HOST_UID":"$HOST_GID" /verify; exit $rc'` | 编译产物回到 `runner` 名下；`rc` 先存再 chown，编译失败也照样把属主还回去、且**不吞掉失败退出码**（不能为了让下一轮能删而把这一轮的红洗成绿） |
| `rm -rf` 加 `2>/dev/null`，之后 `[ -e .ci-verify ]` 判在不在，还在就用容器内的 root 清一次 | 处理"构建被 `timeout` 打断、收尾 chown 没跑到"那一轮——它留下的还是 root 属主，只有容器里的 root 删得掉。顺带把 35 行 `Permission denied` 变成一行说明 |
| 兜底也失败才 `exit 1`，并打印可直接执行的 `sudo rm -rf <路径>` | 真删不动时给的是处置动作，不是让用户再猜一轮 |

**验证是真跑的，不是推演**（在 `/tmp/ownws` 里，只读 `/root/HR/backend`，不碰任何运行中的容器）：
先手工造出 #16 的现场（`.ci-verify` 归 runner、里面的 `target` 归 root），以 `runner` 身份把「本次提交编译」段
原样连跑三轮 —— 第 1 轮打印兜底清理并编出 30 个 class、跑完 `find .ci-verify -user root` 为 0；
第 2、3 轮直接 `rm -rf` 就过（不再触发兜底），class 数恒为 30。
真实现场那份 root 属主残留**故意留着**，让 #17 顺带把兜底分支在正式工作区里再验一次。

#12、#13、#14 那三次红则与流水线代码无关：这个 job 的 `<lightweight>true</lightweight>`，
**取 Jenkinsfile 这一步发生在 Windows 控制器上**（日志里能看到 `C:\Program Files\Git\bin\git.exe fetch`），
控制器到 github.com 链路本来就抖，三次都是 `Recv failure: Connection was reset`，且都发生在
`Start of Pipeline` 之前 —— agent 没参与、工作区没动。第 4 次点就过去了。
要根治得改 job 配置（关掉 Lightweight checkout），但它会把取回变成一次完整 checkout、
**这一步落在控制器还是 agent 上我还没实测**，所以先不写成结论；观察到的事实是：一次红就重跑，
连续多次红再来动这个开关。

**#17~#19 踩中的坑：github 的可达性不能当常量用（2026-11-19~20）**

两种红长得不一样，先分清再动手：

| 现象 | 位置 | 判据 |
| --- | --- | --- |
| 日志 18 行、一个 stage 都没打印 | **取 Jenkinsfile**，发生在 Windows 控制器上（日志里是 `C:\Program Files\Git\bin\git.exe`，早于 `Start of Pipeline`） | 别改 Jenkinsfile，重跑 |
| `Failed to connect to github.com port 443 after 134449 ms` | agent 上的 checkout，在 `retry` 块里 | 网络与钉位，不是代码 |

实测（同一台服务器、同一个 IP、不同时刻）：`140.82.112.4` 有时 21~49 秒拉下整个仓库、有时小请求 0 字节；
`20.247.166.64` 昨夜 35 秒可用、今晨 09:54 连小请求都不通；`dig` 给的第一个应答经常正是死的那个。
**结论：没有稳定可用的 IP，只有一条按分钟到小时漂移的链路。** 所以"测一次能用就钉住"必然腐烂——
我自己钉 `140.82.113.4` 两次，两次都在几分钟内失效。

落地的机制是 `/usr/local/sbin/github-ip-probe.sh` + `github-ip-probe.{service,timer}`（root，5 分钟一轮）：

- **两档判据**。便宜档 = `info/refs` 小请求（每轮跑，拦 SYN 黑洞 / 0 字节）；
  全档 = 真做一次 `git clone --depth 1`（按时间戳或"当前钉位小请求已不通"时才跑，拦"refs 通但 pack 传不动"）。
  只用小请求是错的：`20.6.7.17` 就是 0.6 秒返回 200、真实克隆 59 秒起甚至完全传不动的那个。
- **只在当前钉位真拉不动时才换**，换的是"按候选顺序第一个拉得动的"，不是全场最快；
  活着但变慢（≥60 秒）只写 journal 预警、不动配置——整条链路变慢时换 IP 治不了它，换只会让配置跟着噪声抖。
- 候选全不通时**保持原钉位并告警**：构建红在 Checkout 比静默改配置好归因（宁可假红也不要假绿）。
- 超时 `CLONE_TIMEOUT=120`：成功样本实测分布在 4~49 秒，一度设 50 秒会把"活着但慢"判成死，
  于是每次坏窗口都换一次钉位。**超时必须明显大于最慢的成功样本。**
- 自检开关 `FORCE_FULL=1`。反向自检真跑过：23:35 那轮它在"小请求通、pack 拉不动"的候选堆里换到了可用 IP，
  而我第一版的判据（只看小请求 200）会把那个 IP 判成可用。
- **别手工改 `/etc/hosts` 里 BEGIN/END 那一段，也别停这两个 unit**：删了就是把构建重新押在运气上。
  块里的说明文字由脚本自己重写，手工写在标记之间的注释会在第一次换钉位时被吃掉。
- 没解决的部分：链路整体黑洞时（15:37~15:45 连续三轮全部候选不通）钉位无能为力，只能靠 `retry` 撞窗口；
  #23 的 checkout 就是这么撞过去的——两次 135 秒失败后第 3 次成功，代价约 5 分钟。
  SSH 通道实测能握手（22 和 443 都返回 `Permission denied (publickey)`，说明走的是另一组边缘 IP、
  且隧道是通的），要用它得在仓库里加只读 deploy key，属账号决策，**尚未做**。

**#23 踩中的坑：上一轮的"修复"其实没修好，因为 Jenkins 用 `sh -xe` 跑（2026-11-20）**

#23 走到第 8 段就没往下走，但和 #16 长得不一样——**日志里一行报错都没有**：编译段只执行到
`rm -rf .ci-verify 2>/dev/null` 这一句就结束了，随后 `Stage "覆盖率门禁" skipped due to earlier failure(s)`。

根因是 `set -e`：`rm` 因为 root 属主残留返回 1，`-e` 就地终止，**#16 加的容器侧兜底根本没机会执行**。
`2>/dev/null` 只是把 35 行 `Permission denied` 变成了安静，红还是红。取证直接看工作区：
`.ci-verify` 归 `runner`、里面的 `target/` 归 `root`。

改法只有两个 `|| true`（判定逻辑一条没动）：

| 位置 | 改动 | 为什么不是随手加的 |
| --- | --- | --- |
| `rm -rf .ci-verify 2>/dev/null` | 后面补 `\|\| true` | 不加就是"合法非零 → set -e 终止 → 兜底成死代码" |
| 兜底那条 `docker run … rm -rf /ws/.ci-verify` | 同样补 `\|\| true` | 它一失败会把下一条 `[ -e ]` 的提示信息一起掐掉，报出来的还是没头没尾的一行 |

回归验证是真拿两种 uid 复现的，不是桩：先造出 #23 现场并**证伪**（`su runner` 下 `rm` rc=1、
`Permission denied`、残留仍在），再以 `runner` + `sh -xe` 跑修后的整段 → 走到"用容器内的 root 清一次" →
`本次检出编译出 30 个 class` → rc=0 → `find .ci-verify ! -user runner` 为 0。

**比这条 bug 更值得记的是校验器自己的两个洞**：

1. 预跑用的是 `sh -x`，**没带 `-e`**。凡是"命令合法地返回非零"的写法（清理、探测、`grep` 无匹配）都测不出来。
   现在校验器统一 `sh -xe`，10 个块 ok / fail 两种桩各跑一遍全过（ok 模式要求每块都跑到 rc=0）。
2. 块文本抽取按"整行只有 `'''`"找块尾，而 Groovy 三引号字符串在**第一个** `'''` 处结束（收尾可以和命令同行）。
   结果 10 个块里 4 个被截断——门禁块只剩 2 行、真块 8 行——"10/10 通过"当时覆盖的是错文本。
   现在改成按 `'''` 切分再判开引号，块数与 `grep -c "sh '''"` 对齐（10）。

> 一句话：**校验器的覆盖面本身要验证**，否则"全绿"只是自我安慰。这两洞都是我自己写的、自己报过"已验证"的。

#23 也不是白红：第一次真构建把部署段和证据链都跑通了——compose project 核对「hr」、
新镜像 `e80b8349ef58`、6300 可达、登录第 6 次探测拿到 token、`125 passed in 7.36s`、
字节码落盘 61074733 字节 `sha256 3b9fbdd4eb6fac0f`；post 的本轮新鲜度判定也按设计拒绝了历轮残留的
`summary.json`（"不作为本轮结论"）。**门禁数字这一轮没产出，"覆盖率门禁"那一段还没在真构建里跑通过。**

**流水线形态（仓库根 `Jenkinsfile`）**

调度器是 Jenkins 控制器（Windows 本机），执行平面是服务器上的 SSH agent（`cloud-server`，label `cloud`，
非 root 的 `runner` 账号）。阶段与用途：

| 阶段 | 干什么 | 失败时最先怀疑什么 |
| --- | --- | --- |
| Checkout | `retry(3)` + 显式 `CloneOption timeout: 5` 拉 master（github.com 需服务器 `/etc/hosts` 钉可用 IP，全量传输实测 34~65 秒）；末尾 `touch tests/logs/.build-start` 作为本轮产物时间基准 | 网络与解析，不是代码 |
| 执行平面自检 | 验 docker 权限、**五个"只在 shell 里用"的参数逐个非空**、`hr-mysql`/`hr-redis` 是 `running/healthy`、`backend/settings.xml` 在位；顺带报出 `hr-backend` 现用镜像 | 参数空值（新增参数没进 `environment{}` 兜底，见上节 #11）；块里混进 bash 写法（`sh` 步骤的解释器是 dash，见上节 #15）；没重连 agent（加组不重连等于没加）；数据服务没起（部署段只管 backend） |
| Runner 镜像 | 镜像缺失或 `REBUILD_RUNNER=true` 才 build，之后 `pytest --version` + `mvn -v` 复验 | 内网 pip 索引少了 `PIP_TRUSTED_HOST` |
| 执行平面配置 | `withCredentials` 生成 `tests/config/.env.dev`（0600，日志只出键名与长度） | 凭据 ID 或类型不对 |
| 部署本次提交 | 先读运行中容器的 `com.docker.compose.project` 标签和 `COMPOSE_PROJECT` 核对（不一致立刻停，不进 `up`）；三条凭据以环境变量注入 compose，`-p hr -f docker-compose.yml -f docker-compose.coverage.yml up -d --build --no-deps backend`；再验 6300 可达、并用 `/api/auth/login` 拿到 token 当就绪判据 | `project` 名不对（会得到一套空库的新栈，归属核对就是拦这个的）；凭据值与运行中 mysql/redis 不一致（后端连不上库，探活转满 120 秒后打容器 ERROR 行）；`--build` 失败看 `tests/logs/deploy.log` |
| 接口用例 | 容器里跑 pytest 出 `tests/reports/junit.xml`，只为 JUnit 结果与趋势 | 用例本身；覆盖率不会因此算重（门禁首步清零并丢弃那次取数） |
| 部署字节码落盘 | `docker cp` 运行中容器的 `/app/app.jar`，打印字节数、sha256 前缀、容器与镜像 ID——这份 jar 现在就是上一段刚构建的产物 | 报告可信度的来源，日志里可追溯是哪份产物 |
| 本次提交编译 | 把 `backend/{pom.xml,settings.xml,src}` 拷到 `.ci-verify/` 隔离副本，容器里 `mvn -DskipTests compile`，产出 class 数必须 > 0；容器收尾用 `HOST_UID/HOST_GID` 把产物 chown 回 runner，宿主侧删不动时改用容器内的 root 清一次（见上节 #16） | 本次检出的源码编译不过（与部署无关，先看代码）；或 maven 本地库缺插件导致在线下载失败；报"root 属主残留"= 上一轮被 timeout 打断，兜底会自己清，清不动才手工 `sudo rm -rf` |
| 覆盖率门禁 | `coverage_gate.py --deploy-mode file --checkout-classes /workspace/.ci-verify/target/classes`：先做部署一致性断言，再判阈值；不一致退出码 2、未达标退出码 1 | 有了部署段之后断言仍报红 = 那次部署没落到容器里（比对 `deploy.log` 里的 `Recreated`/`Running` 与落盘段打印的镜像 ID），不是覆盖率掉了 |
| post | **先按 `.build-start` 过滤新鲜度**：本轮没产出 `junit.xml`/`summary.json` 就跳过发布并说明，只有本轮产物才 `junit` + `archiveArtifacts`（`summary.json`、JaCoCo `index.html`/`xml`/`csv`）；构建末尾打印 `classes_source`、`checkout_verified` 与三项实测值 | 上一轮残留被当成本轮结论（#11 修掉的洞：FAILURE 的构建曾报出 #10 的 `125 passed` 与 70.09%） |

建 job 前先备齐**四条凭据**（Manage Jenkins → Credentials → System → Global）：`hr-api-admin`
（Username with password，接口用例的管理员账号）、`hr-jwt-secret` / `hr-mysql-root-password` / `hr-redis-password`
（都是 Secret text，值由人从服务器 `.env` 里抄出来录入：`grep -E '^(HR_AUTH_JWT_SECRET|MYSQL_ROOT_PASSWORD|REDIS_PASSWORD)=' /root/HR/.env`）。
凭据 ID 就是流水线参数 `HR_*_CREDENTIAL_ID` 的默认值，改名要同步改参数。
job 本身：New Item → **Pipeline** → Pipeline script from SCM → Git，URL 用官方
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
