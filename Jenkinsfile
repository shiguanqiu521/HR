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
 *   1. agent 账号在 docker 组里。组成员身份在登录时分配，加组后必须重连 agent（或重启 Jenkins）才生效。
 *   2. 两条 Jenkins 凭据：hr-api-admin（Username with password，接口用例的管理员账号）、
 *      hr-jwt-secret（Secret text，后端 hr.auth.jwt-secret，只 TC-AUTH-014 本地自签过期 token 用）。
 *   3. 被测后端用 coverage overlay 启动（走 Compose v2，v1.29 的 recreate 必崩）：
 *      docker compose -f docker-compose.yml -f docker-compose.coverage.yml up -d backend
 *
 * 关于工作区属主：容器内的 root 会在 gitignore 目录（backend/target、tests/reports、tests/logs）里留下
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
        string(name: 'HR_ADMIN_CREDENTIAL_ID', defaultValue: 'hr-api-admin',
               description: '接口用例管理员账号凭据（Username with password）')
        string(name: 'HR_JWT_CREDENTIAL_ID', defaultValue: 'hr-jwt-secret',
               description: '后端 JWT 密钥凭据（Secret text）')
        string(name: 'MAIL_TO', defaultValue: '',
               description: '失败收件人，留空则不发邮件（SMTP 取全局 E-mail Notification 配置）')
    }

    options {
        timestamps()
        skipDefaultCheckout(true)
        // JaCoCo 的计数器是被测 JVM 里的一份全局状态，并发构建会互相清零，必须串行
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '20'))
        timeout(time: 20, unit: 'MINUTES')
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
                sh 'git log -1 --format="构建的提交：%h %ad %s" --date=iso'
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

                    if ! docker inspect "${BACKEND_CONTAINER}" >/dev/null 2>&1; then
                        echo "[自检] 没有 ${BACKEND_CONTAINER} 容器，被测环境未就绪"
                        exit 1
                    fi
                    # 只判断 agent 挂没挂上：grep -q 不打印任何 environment 值（那里面有真实口令）
                    if ! docker inspect -f "{{range .Config.Env}}{{println .}}{{end}}" "${BACKEND_CONTAINER}" | grep -q jacocoagent.jar; then
                        echo "[自检] ${BACKEND_CONTAINER} 没挂 JaCoCo agent，覆盖率无从采集。用 coverage overlay 重建："
                        echo "       docker compose -f docker-compose.yml -f docker-compose.coverage.yml up -d backend"
                        exit 1
                    fi
                    echo "[自检] ${BACKEND_CONTAINER} 已挂 JaCoCo agent"

                    if [ ! -f backend/settings.xml ]; then
                        echo "[自检] 仓库里没有 backend/settings.xml（镜像仓库配置随代码分发，checkout 应带回该文件）"
                        exit 1
                    fi

                    # /api/health 是硬编码 UP（已知缺陷 D4），所以探活只看 8080 有没有 HTTP 应答，不看它
                    code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' http://127.0.0.1:8080/ || echo 000)
                    echo "[自检] 被测服务 8080 应答 HTTP ${code}"
                    if [ "${code}" = "000" ]; then
                        echo "[自检] 8080 无应答，检查 ${BACKEND_CONTAINER} 的端口发布与容器状态"
                        exit 1
                    fi

                    # 采集端口必须先通，否则门禁里的 mvn dump 要重试十次才失败
                    if ! bash -c 'exec 3<>/dev/tcp/127.0.0.1/6300' 2>/dev/null; then
                        echo "[自检] 127.0.0.1:6300 连不上（JaCoCo tcpserver）。同机执行不需要隧道，"
                        echo "       确认 coverage overlay 的端口发布绑在了 127.0.0.1"
                        exit 1
                    fi
                    echo "[自检] 127.0.0.1:6300 可达"
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
                    # 落盘而不是在容器里现取：执行平面因此不需要免密 ssh，也不需要 docker 之外的权限
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
                # 数字自证来源：classes_source 记的就是这一轮用哪条通道取回部署字节码
                if [ -f tests/reports/coverage/summary.json ]; then
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
                else
                    echo "[门禁] 没有 summary.json，本轮没出覆盖率结论（见上面失败阶段的自检提示）"
                fi
            '''
            junit testResults: 'tests/reports/junit.xml', allowEmptyResults: true
            archiveArtifacts(
                artifacts: 'tests/reports/coverage/summary.json, ' +
                           'tests/reports/coverage/latest/index.html, ' +
                           'tests/reports/coverage/latest/jacoco.xml, ' +
                           'tests/reports/coverage/latest/jacoco.csv',
                allowEmptyArchive: true,
                fingerprint: false
            )
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
