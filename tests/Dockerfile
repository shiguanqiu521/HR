# 接口用例 + 覆盖率门禁的执行平面（runner）镜像
#
# 为什么需要这个镜像：门禁流程同时要用 mvn（jacoco:dump / jacoco:report）和
# python（pytest 执行用例、解析 jacoco.csv）。被测后端所在的机器一般只有 JRE ——
# 本项目的云服务器实测就是 `mvn MISSING`、pypi 公网源全断。把工具链固化成镜像，
# "在哪跑用例"就不再依赖某个人的电脑，也不依赖被测机器装了什么。
#
# 构建上下文只是 tests/，且只 COPY requirements.txt（见 tests/.dockerignore）：
# 镜像里装的是依赖，不是用例代码；代码、配置、产物都由运行时 bind mount 进去。
#   docker build -t hr-testrunner -f tests/Dockerfile tests/ \
#     --build-arg PIP_INDEX_URL=http://mirrors.baidubce.com/pypi/simple \
#     --build-arg PIP_TRUSTED_HOST=mirrors.baidubce.com
#
# 跑一轮（与被测后端同机，--network host 才能直连 127.0.0.1:8080 和 6300）：
#   docker run --rm --network host \
#     -v /root/HR:/workspace \
#     -v /root/.m2:/root/.m2 \
#     -v /root/HR/backend/settings.xml:/root/.m2/settings.xml:ro \
#     hr-testrunner python3 tests/coverage_gate.py
#
# 权限口径：不挂 /var/run/docker.sock（那等于把宿主机 root 交给测试通道）。
# 因此 config/coverage.yml 用 deploy.mode=file，字节码由部署步骤 docker cp 落盘后当普通文件读。
FROM maven:3.9-eclipse-temurin-17

# 默认走公网源；云上构建按环境覆盖，例：
#   --build-arg PIP_INDEX_URL=http://mirrors.baidubce.com/pypi/simple \
#   --build-arg PIP_TRUSTED_HOST=mirrors.baidubce.com
ARG PIP_INDEX_URL=https://pypi.org/simple
# 内网镜像源只提供 HTTP 时必须同时声明 trusted-host：pip 会直接忽略未信任的索引，
# 报的是 "Could not find a version ... (from versions: none)"，看不出真实原因是索引被跳过
# （2026-11-18 在云服务器上实测踩过）。公网 pypi 留空即可。
ARG PIP_TRUSTED_HOST=

# openssh-client 只为 deploy.mode=ssh 留条后路；CI 用 file 模式时不会碰它
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv python3-pip openssh-client \
    && rm -rf /var/lib/apt/lists/*

# 用 venv 而不是系统 site-packages：Debian/Ubuntu 的 python3-pip 受 PEP 668 限制不允许全局装；
# coverage_gate.run_pytest 用 sys.executable 拉 pytest，PATH 指向 venv 就保证跑的是这套依赖
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
      --index-url "${PIP_INDEX_URL}" \
      ${PIP_TRUSTED_HOST:+--trusted-host ${PIP_TRUSTED_HOST}} \
      -r /tmp/requirements.txt

WORKDIR /workspace

# maven 基础镜像的 ENTRYPOINT 是 mvn，会吃掉命令行；runner 要的是普通 shell/python
ENTRYPOINT []
CMD ["python3", "-m", "pytest", "--version"]
