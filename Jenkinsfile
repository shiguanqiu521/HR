/*
 * HR 接口自动化 + 后端覆盖率门禁
 *
 * 三平面拓扑（与 tests/README.md「执行平面与流水线」一致）：
 *   被测环境  hr-backend / hr-mysql / hr-redis，JaCoCo agent 以 tcpserver 挂在 127.0.0.1:6300
 *   执行平面  本流水线所在 agent（服务器上的 runner 账号，需在 docker 组里）里起的 runner 容器
 *   产物存储  Jenkins 的 junit 结果 + archiveArtifacts（summary.json、JaCoCo HTML/XML/CSV）
 * 控制器只做调度：工具链固化在 tests/Dockerfile 的镜像里，不从任何人的笔记本跑，报告也不写进被测服务的容器。
 *
 * 前置条件（缺任何一条，「执行平面自检」段会直接说清原因，不会让你去猜 mvn 的报错）：
 *   1. agent 账号在 docker 组里（执行平面要能驱动 compose 重建后端）。组成员身份在登录时分配，
 *      加组后必须重连 agent（或重启 Jenkins）才生效。
 *   2. 四条 Jenkins 凭据：hr-api-admin（Username with password，接口用例的管理员账号），
 *      hr-jwt-secret / hr-mysql-root-password / hr-redis-password（都是 Secret text，值由人从服务器 .env
 *      抄进 Manage Jenkins 录入）。runner 读不到 /root/HR/.env，也不该读到——凭据就是为绕开它而存在的。
 *   3. 被测环境的 hr-mysql / hr-redis 在运行且 healthy。流水线只重建 backend（--no-deps），
 *      不启动、不重建数据服务，也不碰 hr_mysql-data 卷——那是在服务器上的运维动作。
 *   4. 后端的镜像与部署由「部署本次提交」段完成（Compose v2 + coverage overlay；v1.29 的 recreate 必崩），
 *      所以不需要事先手工 up -d backend。**代价要说清：这一段的 compose up 会重建 hr-backend 容器，
 *      也就是重启对外提供服务的后端**（是否每次都重建由配置哈希与镜像 ID 决定，日志里
 *      `Recreated` 与 `Running` 两种都算正常，看 tests/logs/deploy.log）。
 *
 * 工作区属主：容器内的 root 会在 gitignore 目录（backend/target、tests/reports、tests/logs）里留下
 * root 属主、0644 的产物，Jenkins 读得到（archiveArtifacts 正常），但**不要开 cleanWs() 或
 * "Wipe Out Workspace"** —— runner 删不掉这些文件，会让构建无故变红。
 */
pipeline {
    agent { label 'cloud' }

    parameters {
        string(name: 'RUNNER_IMAGE', defaultValue: 'hr-testrunner:latest',
               description: '执行平面镜像；不存在时由本流水线构建')
        booleanParam(name: 'REBUILD_RUNNER', defaultValue: false,
                     description: '强制重建 runner 镜像（改过 tests/Dockerfile 或 requirements.txt 后打开）')
        string(name: 'PIP_INDEX_URL', defaultValue: 'http://mirrors.baidubce.com/pypi/simple',
               description: '构建镜像用的 pip 索引；境外机器可换 https://pypi.org/simple')
        string(name: 'PIP_TRUSTED_HOST', defaultValue: 'mirrors.baidubce.com',
               description: 'http 索引必须同时给信任主机，否则 pip 静默忽略该索引（症状是 from versions: none）')
        string(name: 'DEPLOY_MODE', defaultValue: 'file',
               description: '门禁取部署字节码的通道：file=读 docker cp 落盘的 jar（同机/CI）；ssh=远端现取（本机驱动时用）')
        string(name: 'MVN_LOCAL_REPO', defaultValue: '/home/runner/.m2',
               description: '容器里 mvn 本地仓库对应的宿主目录（用 agent 账号自己的目录，不挂 /root）')
        string(name: 'BACKEND_CONTAINER', defaultValue: 'hr-backend',
               description: '被测后端容器名，运行中的字节码从它身上取')
        string(name: 'COMPOSE_PROJECT', defaultValue: 'hr',
               description: 'compose project 名，必须与被测环境现有 project 一致（-p）：一致才重建同一套容器、复用 hr_mysql-data 卷；填错会得到一套空库的新栈')
        string(name: 'HR_ADMIN_CREDENTIAL_ID', defaultValue: 'hr-api-admin',
               description: '接口用例管理员账号凭据（Username with password）')
        string(name: 'HR_JWT_CREDENTIAL_ID', defaultValue: 'hr-jwt-secret',
               description: '后端 JWT 密钥凭据（Secret text）：部署时注入 HR_AUTH_JWT_SECRET，用例侧 TC-AUTH-014 本地自签过期 token 也用它')
        string(name: 'HR_MYSQL_CREDENTIAL_ID', defaultValue: 'hr-mysql-root-password',
               description: 'MYSQL_ROOT_PASSWORD 凭据（Secret text）：compose 插值 SPRING_DATASOURCE_PASSWORD 用，必须与运行中 mysql 的口令一致，否则后端连不上库')
        string(name: 'HR_REDIS_CREDENTIAL_ID', defaultValue: 'hr-redis-password',
               description: 'REDIS_PASSWORD 凭据（Secret text）：compose 插值 SPRING_DATA_REDIS_PASSWORD 与 redis --requirepass 用')
        string(name: 'MAIL_TO', defaultValue: '',
               description: '失败收件人，留空则不发邮件（SMTP 取全局 E-mail Notification 配置）')
    }

    options {
        timestamps()
        skipDefaultCheckout(true)
        // JaCoCo 的计数器是被测 JVM 里的一份全局状态，并发构建会互相清零，必须串行
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '20'))
        // 预算按实测算：#10 全程 72.5 秒；部署段最坏是 compose build 缓存全冷 199 秒 + 容器重建与登录探活。
        // 20 分钟对最坏一轮还有 4 倍以上余量，不去动它——超时该意味着真卡住了，而不是阈值给小了
        timeout(time: 20, unit: 'MINUTES')
    }

    environment {
        // #11 的根因：Jenkins 只把"本次构建参数表里已有的"参数导成环境变量。新加的参数在**它第一次
        // 被注册之前的那一轮**拿不到环境变量，shell 里 ${COMPOSE_PROJECT} 就是空串，compose 退回按
        // 目录名推导 project（hr-api-coverage-gate），于是另建了一套网络 + 空 mysql-data/redis-data 卷，
        // 最后撞在容器名冲突上。而 Groovy 侧 params.X 会退回 parameters{} 的默认值（所以两个凭据 ID 一直正常），
        // 两种取值路径不一致，凡"只在 shell 里用"的新参数都必须在这里显式兜底，并由自检段验非空
        COMPOSE_PROJECT = "${params.COMPOSE_PROJECT ?: 'hr'}"
    }

    stages {
        stage('Checkout') {
            steps {
                // 百度内网 DNS 把 github.com 解析到 20.6.7.17，该地址只回 refs、传不了 pack，
                // 表现为 fetch 挂死后被 SIGTERM。已在服务器 /etc/hosts 固定为实测可用的 140.82.112.4。
                // 跨境链路全量 clone 实测 56~65s，这里显式给 5 分钟超时，不依赖 job 里的 Advanced Clone behaviours 取值。
                retry(3) {
                    checkout([
                        $class: 'GitSCM',
                        branches: scm.branches,
                        extensions: scm.extensions + [[$class: 'CloneOption', timeout: 5]],
                        userRemoteConfigs: scm.userRemoteConfigs
                    ])
                }
                sh '''
                    git log -1 --format="构建的提交：%h %ad %s" --date=iso
                    # 本轮产物的时间基准：post 只发布 mtime 晚于它的 junit.xml / summary.json。
                    # 没这个基准就会出现 #11 那种场面——构建 FAILURE，页面却显示历轮的 125 passed 和 70.09%
                    mkdir -p tests/logs && touch tests/logs/.build-start
                '''
            }
        }

        stage('执行平面自检') {
            steps {
                sh '''
                    if ! docker info >/dev/null 2>&1; then
                        echo "[自检] 拿不到 docker 权限。"
                        echo "       runner 账号已加入 docker 组，但组成员身份在登录时分配："
                        echo "       Manage Jenkins → Nodes → cloud-server → Disconnect 再 Relaunch（或重启 Jenkins）"
                        exit 1
                    fi
                    echo "[自检] docker server $(docker version --format '{{.Server.Version}}')"

                    # 参数在 shell 里取到空值 = 本轮参数表里还没有它（新加参数的第一轮构建必踩，#11 实证：
                    # -p 传空 → compose 按目录名推导 project → 另建一套空库卷）。在这里停，别让它往下走
                    params_line=""
                    for v in RUNNER_IMAGE DEPLOY_MODE MVN_LOCAL_REPO BACKEND_CONTAINER COMPOSE_PROJECT; do
                        eval "val=\${$v:-}"
                        if [ -z "${val}" ]; then
                            echo "[自检] 参数 ${v} 在 shell 里是空值。Jenkins 只把「本次构建参数表里已有的」参数导成"
                            echo "       环境变量，新增参数的第一轮构建拿不到它（Groovy 的 params.X 却有默认值，"
                            echo "       所以只在 shell 里用的那种才会中招）。处置二选一："
                            echo "       1) Build with Parameters 里显式填一次 ${v}，再重跑；"
                            echo "       2) 在顶部 environment{} 里给它兜底（COMPOSE_PROJECT 已经是这么修的）"
                            exit 1
                        fi
                        params_line="${params_line} ${v}=${val}"
                    done
                    echo "[自检] 参数齐备：${params_line}"

                    # 数据服务不归本流水线管（部署段只 --no-deps 重建 backend），所以缺了必须在这里就说清。
                    # 否则要等部署段的登录探活转满 120 秒才失败，报出来的还是"后端没就绪"这种误导性结论
                    for svc in hr-mysql hr-redis; do
                        st=$(docker inspect -f '{{.State.Status}}/{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${svc}" 2>/dev/null || echo 缺失)
                        echo "[自检] ${svc}: ${st}"
                        if [ "${st}" != "running/healthy" ]; then
                            echo "[自检] 数据服务没就绪。在服务器上先把它们起来（compose v2）："
                            echo "       docker compose -f docker-compose.yml up -d mysql redis"
                            exit 1
                        fi
                    done

                    if [ ! -f backend/settings.xml ]; then
                        echo "[自检] 仓库里没有 backend/settings.xml（镜像仓库配置随代码分发，checkout 应带回该文件）"
                        exit 1
                    fi

                    # backend 容器在不在、agent 挂没挂、8080/6300 通不通，都不再是前置条件：
                    # 这些正是「部署本次提交」段要产出的东西，由那一段自己验并给原因
                    if docker inspect "${BACKEND_CONTAINER}" >/dev/null 2>&1; then
                        echo "[自检] ${BACKEND_CONTAINER} 已存在（$(docker inspect -f '{{.Image}}' "${BACKEND_CONTAINER}" | cut -c8-19)），部署段按需重建它"
                    else
                        echo "[自检] ${BACKEND_CONTAINER} 不存在，由部署段首次创建"
                    fi
                '''
            }
        }

        stage('Runner 镜像') {
            steps {
                sh '''
                    if [ "${REBUILD_RUNNER}" = "true" ] || ! docker image inspect "${RUNNER_IMAGE}" >/dev/null 2>&1; then
                        echo "[runner] 构建 ${RUNNER_IMAGE}"
                        docker build -t "${RUNNER_IMAGE}" \
                          --build-arg PIP_INDEX_URL="${PIP_INDEX_URL}" \
                          --build-arg PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST}" \
                          -f tests/Dockerfile tests/
                    else
                        echo "[runner] 复用已存在的 ${RUNNER_IMAGE}（构建于 $(docker image inspect -f '{{.Created}}' "${RUNNER_IMAGE}")）"
                    fi
                    # 复用旧镜像也不能假设里面的工具链还在，验一遍再继续
                    docker run --rm "${RUNNER_IMAGE}" sh -c 'python3 -m pytest --version && mvn -v | head -1'
                '''
            }
        }

        stage('执行平面配置') {
            steps {
                withCredentials([
                    usernamePassword(credentialsId: params.HR_ADMIN_CREDENTIAL_ID,
                                     usernameVariable: 'HR_ADMIN_USER', passwordVariable: 'HR_ADMIN_PWD'),
                    string(credentialsId: params.HR_JWT_CREDENTIAL_ID, variable: 'HR_JWT_SECRET')
                ]) {
                    sh '''
                        umask 077
                        mkdir -p tests/config tests/reports tests/logs backend/target/deployed
                        # conftest 在会话启动时按 --env 读 .env.dev，且 switch_env 会先清掉同名 OS 环境变量，
                        # 所以凭据只能落成这份 workspace 内、gitignore 掉的文件，不能只靠 -e 传进容器
                        {
                            printf 'HR_BASE_URL=%s\\n' 'http://127.0.0.1:8080'
                            printf 'HR_LOG_LEVEL=%s\\n' 'INFO'
                            printf 'HR_ADMIN_USER=%s\\n' "${HR_ADMIN_USER}"
                            printf 'HR_ADMIN_PWD=%s\\n' "${HR_ADMIN_PWD}"
                            printf 'HR_JWT_SECRET=%s\\n' "${HR_JWT_SECRET}"
                        } > tests/config/.env.dev
                        if [ -z "${HR_JWT_SECRET}" ]; then
                            echo "[配置] 警告：JWT 凭据为空，TC-AUTH-014 会按条件跳过（基线少一条用例）"
                        fi
                        # 只打印键名与值长度，值不进构建日志；值含 = 时长度也算对
                        echo "[配置] tests/config/.env.dev"
                        awk -F= 'NF>1 {printf "  %-16s len=%d\\n", $1, length($0)-length($1)-1}' tests/config/.env.dev
                    '''
                }
            }
        }

        stage('部署本次提交') {
            steps {
                withCredentials([
                    string(credentialsId: params.HR_MYSQL_CREDENTIAL_ID, variable: 'MYSQL_ROOT_PASSWORD'),
                    string(credentialsId: params.HR_REDIS_CREDENTIAL_ID, variable: 'REDIS_PASSWORD'),
                    string(credentialsId: params.HR_JWT_CREDENTIAL_ID, variable: 'HR_AUTH_JWT_SECRET')
                ]) {
                    sh '''
                        umask 077
                        # project 名不能只信参数：运行中的容器身上写着它属于哪个 project，以它为准比对。
                        # 对不上就停在这里 —— 继续下去 compose 会另起一套容器和空库卷（#11 就是这样），
                        # 更糟的是空库上照样能跑完 125 条用例并出一个看似正常的覆盖率数字
                        if docker inspect "${BACKEND_CONTAINER}" >/dev/null 2>&1; then
                            own=$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' "${BACKEND_CONTAINER}")
                            echo "[部署] ${BACKEND_CONTAINER} 属于 compose project「${own:-无标签}」，本轮要用「${COMPOSE_PROJECT}」"
                            if [ "${own}" != "${COMPOSE_PROJECT}" ]; then
                                echo "[部署] 两者不一致，停。对不上意味着接下来这次 up 不会重建现有容器，"
                                echo "       而是另起一套（独立网络 + 独立的空 mysql-data 卷），数字就测到空库上了。"
                                echo "       参数 COMPOSE_PROJECT 留空/填错，或被测容器不是用 compose 起的（own 为空）"
                                exit 1
                            fi
                        else
                            echo "[部署] ${BACKEND_CONTAINER} 不存在，由本轮首次创建（project=${COMPOSE_PROJECT}）"
                        fi

                        # 口令只经 compose 的进程环境变量注入：不写 .env 文件、不出现在命令行上
                        # （sh 步骤带 -x，命令行原文会进构建日志），也不要求 runner 能读 /root/HR/.env。
                        # MYSQL_DATABASE 用 compose 里的 :-hr_db 默认值，已核对与服务器 .env 相同，不是凭据。
                        # --no-deps 只动 backend，不重启 mysql/redis；一律 Compose v2（本机 v1.29 的 recreate 必崩）
                        if ! docker compose -p "${COMPOSE_PROJECT}" \\
                               -f docker-compose.yml -f docker-compose.coverage.yml \\
                               up -d --build --no-deps backend > tests/logs/deploy.log 2>&1; then
                            echo "[部署] compose 构建/启动失败，tests/logs/deploy.log 末尾："
                            tail -30 tests/logs/deploy.log
                            exit 1
                        fi
                        echo "[部署] compose 输出末尾："
                        tail -5 tests/logs/deploy.log | sed 's/^/       /'
                        echo "[部署] ${BACKEND_CONTAINER} 现用镜像 sha(前12) $(docker inspect -f '{{.Image}}' "${BACKEND_CONTAINER}" | cut -c8-19)"

                        # 采集通道必须在用例之前通，否则门禁里的 jacoco dump 要重试十次才失败
                        if ! bash -c 'exec 3<>/dev/tcp/127.0.0.1/6300' 2>/dev/null; then
                            echo "[部署] 后端起了但 127.0.0.1:6300 连不上（JaCoCo tcpserver）——coverage overlay 没生效"
                            exit 1
                        fi
                        echo "[部署] 127.0.0.1:6300 可达，覆盖率采集通道正常"

                        # 就绪判据 = 用管理员账号真登录并拿到 token。/api/health 是硬编码 UP（已知缺陷 D4），
                        # 拿它当判据会把"进程起来了但连不上 mysql/redis"的后端放过去，用例就整片红在原因之外
                        if [ ! -f tests/config/.env.dev ]; then
                            echo "[部署] 没有 tests/config/.env.dev，探活无从取账号（上一段「执行平面配置」没跑成？）"
                            exit 1
                        fi
                        i=0
                        while :; do
                            i=$((i + 1))
                            # 登录体由 python 从 .env.dev 现读现拼、经管道进 curl：口令既不落盘也不进 argv
                            if python3 -c 'import json,pathlib; kv=dict(l.split("=",1) for l in pathlib.Path("tests/config/.env.dev").read_text(encoding="utf-8").splitlines() if "=" in l); print(json.dumps({"username":kv["HR_ADMIN_USER"],"password":kv["HR_ADMIN_PWD"]}))' \\
                               | curl -s -m 5 -X POST -H 'Content-Type: application/json' \\
                                     --data-binary @- http://127.0.0.1:8080/api/auth/login | grep -q '"token"'; then
                                echo "[部署] 就绪：管理端登录拿到 token（第 ${i} 次探测）"
                                break
                            fi
                            if [ "${i}" -ge 40 ]; then
                                echo "[部署] 120 秒内登录不通，后端没有真正就绪。容器日志里的报错行："
                                docker logs --tail 200 "${BACKEND_CONTAINER}" 2>&1 \\
                                  | grep -E 'ERROR|Exception|Caused by' | tail -20
                                exit 1
                            fi
                            sleep 3
                        done
                    '''
                }
            }
        }

        stage('接口用例') {
            steps {
                sh '''
                    # 这一步只负责 JUnit 结果与用例趋势。覆盖率不会因此算重：
                    # jacoco:dump 默认 reset=true，门禁段的第一步就是清零并丢弃那次取数
                    docker run --rm --network host -e TZ=Asia/Shanghai \
                      -v "${WORKSPACE}:/workspace" -w /workspace/tests \
                      "${RUNNER_IMAGE}" \
                      python3 -m pytest testcases --env=dev --junitxml=reports/junit.xml
                '''
            }
        }

        stage('部署字节码落盘') {
            steps {
                sh '''
                    # 门禁按 class id（类文件内容哈希）匹配执行数据，出报告用的必须是**正在运行**的那份字节码。
                    # 落盘而不是在容器里现取：执行平面因此不需要免密 ssh，也不需要 docker 之外的权限。
                    # 有了「部署本次提交」段，这份 jar 就是本轮构建的产物；下面「本次提交编译」段的逐文件
                    # sha256 断言于是从"抓出忘了重新部署"升级成"证明那次部署真的落到了容器里"
                    docker cp "${BACKEND_CONTAINER}:/app/app.jar" backend/target/deployed/app.jar
                    echo "[字节码] $(wc -c < backend/target/deployed/app.jar) 字节，sha256(前16) $(sha256sum backend/target/deployed/app.jar | cut -c1-16)"
                    echo "[字节码] 来源 $(docker inspect -f '容器 {{.Id}} / 镜像 {{.Image}}' "${BACKEND_CONTAINER}")"
                '''
            }
        }

        stage('本次提交编译') {
            steps {
                sh '''
                    # 为下一段的部署一致性断言准备"本次检出的字节码"。
                    # 刻意编译到隔离副本而不是 backend/：门禁会用部署字节码覆盖 backend/target/classes，
                    # 若在同一目录里编，下一轮构建的增量编译会因源码未变而跳过，
                    # 于是"本次编译产物"其实是上一轮留下的部署 class，断言就变成自证通过的假象
                    rm -rf .ci-verify
                    mkdir -p .ci-verify
                    cp -R backend/pom.xml backend/settings.xml backend/src .ci-verify/
                    docker run --rm -e TZ=Asia/Shanghai \\
                      -v "${WORKSPACE}/.ci-verify:/verify" \\
                      -v "${MVN_LOCAL_REPO}:/root/.m2" \\
                      -v "${WORKSPACE}/backend/settings.xml:/root/.m2/settings.xml:ro" \\
                      "${RUNNER_IMAGE}" \\
                      mvn -B -q -DskipTests compile -f /verify/pom.xml
                    n=$(find .ci-verify/target/classes -name '*.class' | wc -l)
                    echo "[编译] 本次检出编译出 ${n} 个 class"
                    [ "${n}" -gt 0 ] || { echo "[编译] 没有产出任何 class，断言无从比对，先修编译"; exit 1; }
                '''
            }
        }

        stage('覆盖率门禁') {
            steps {
                sh '''
                    docker run --rm --network host -e TZ=Asia/Shanghai \
                      -v "${WORKSPACE}:/workspace" \
                      -v "${MVN_LOCAL_REPO}:/root/.m2" \
                      -v "${WORKSPACE}/backend/settings.xml:/root/.m2/settings.xml:ro" \
                      "${RUNNER_IMAGE}" \
                      python3 tests/coverage_gate.py --deploy-mode "${DEPLOY_MODE}" \
                        --checkout-classes /workspace/.ci-verify/target/classes
                '''
            }
        }
    }

    post {
        always {
            sh '''
                # 只认本轮产物。#11 就是反面教材：构建在部署段就红了，post 仍把历轮留下的 summary.json 念了一遍，
                # 页面同时显示 FAILURE 与"70.09% 门禁通过"，那是假证据。时间基准是 Checkout 段落的 .build-start
                if [ ! -f tests/logs/.build-start ]; then
                    echo "[门禁] 没有本轮时间基准（Checkout 段没跑到），不发布任何覆盖率结论"
                elif [ ! tests/reports/coverage/summary.json -nt tests/logs/.build-start ]; then
                    echo "[门禁] 本轮没有产出 summary.json（工作区里那份早于本轮构建开始，是历轮残留，不作为本轮结论）"
                else
                    python3 -c '
import json
d = json.load(open("tests/reports/coverage/summary.json", encoding="utf-8"))
meta, totals = d["meta"], d["totals"]
print("[门禁] 字节码来源=%s 采集时间=%s pytest退出码=%s"
      % (meta["classes_source"], meta["captured_at"], meta["pytest_exit"]))
print("[门禁] 部署一致性断言=%s（本次编译与部署逐文件比对的 class 数=%s）"
      % (meta.get("checkout_verified"), meta.get("checkout_classes_checked")))
for name in ("line", "branch", "method"):
    t = totals[name]
    print("       %-6s %d/%d = %s%%" % (name, t["covered"], t["total"], t["percent"]))
'
                fi
            '''
            script {
                // junit 与归档一起按时间基准过滤。原先的 allowEmptyResults: true 恰恰掩盖了这一点：
                // "本轮没跑用例"和"跑完全绿"在页面上都表现为收了上一份残留 junit.xml
                def junitFresh = sh(returnStatus: true, script:
                    '[ -f tests/logs/.build-start ] && [ tests/reports/junit.xml -nt tests/logs/.build-start ]') == 0
                def reportFresh = sh(returnStatus: true, script:
                    '[ -f tests/logs/.build-start ] && [ tests/reports/coverage/summary.json -nt tests/logs/.build-start ]') == 0
                if (junitFresh) {
                    junit testResults: 'tests/reports/junit.xml'
                } else {
                    echo "[发布] 本轮没跑用例，跳过 junit（收历轮残留那份就会造出 FAILURE 却 125 passed 的假象）"
                }
                if (reportFresh) {
                    archiveArtifacts(
                        artifacts: 'tests/reports/coverage/summary.json, ' +
                                   'tests/reports/coverage/latest/index.html, ' +
                                   'tests/reports/coverage/latest/jacoco.xml, ' +
                                   'tests/reports/coverage/latest/jacoco.csv',
                        allowEmptyArchive: true,
                        fingerprint: false
                    )
                } else {
                    echo "[发布] 本轮没有覆盖率报告，跳过归档"
                }
            }
        }
        failure {
            script {
                if (params.MAIL_TO?.trim()) {
                    emailext(
                        to: params.MAIL_TO,
                        subject: "[失败] ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                        body: "见 ${env.BUILD_URL}（console 末尾就是失败阶段的自检提示）"
                    )
                }
            }
        }
    }
}
