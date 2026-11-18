# -*- coding: utf-8 -*-
"""
接口用例的后端代码覆盖率归因与门禁

统计对象是被测系统（backend/src/main/java）的行与分支覆盖率，不是自动化脚本自身。
后端以 JaCoCo agent 的 tcpserver 模式运行（见 docker-compose.coverage.yml），
本脚本负责：清零计数 → 跑接口用例 → 取回执行数据 → 出报告 → 按包归因 → 阈值判定。

用法：
    ./.venv/Scripts/python.exe coverage_gate.py                 # 完整流程：清零+跑用例+归因+判定
    ./.venv/Scripts/python.exe coverage_gate.py -k employee      # 只跑部分用例，用于对比用例集的覆盖增量
    ./.venv/Scripts/python.exe coverage_gate.py --check-only     # 不跑用例，只读上一轮清零之后新跑到的代码
    ./.venv/Scripts/python.exe coverage_gate.py --update-thresholds   # 用本轮实测值刷新门禁阈值（棘轮）

字节码口径（决定数字是否可信）：
    默认在出报告前，从运行中的容器里取回 BOOT-INF/classes 覆盖 backend/target/classes，
    保证报告用的就是实际执行的那份字节码。JaCoCo 按 class id（类文件内容哈希）匹配执行数据，
    本地重新编译只要与构建镜像的 JDK 补丁版本有差异就会静默丢类（显示 0% 而非报错）。
    --build 改用本地 mvn compile，仅用于本机直连部署的调试，不能用于出覆盖率结论。

取数口径（决定门禁能不能发现回归）：
    jacoco:dump 对 destFile 是追加合并而不是覆盖，所以每轮 dump 前会删掉 exec_file，
    "只为清零计数器"的那次取数也被丢弃。留着旧 .exec 会让报告变成历轮并集：
    覆盖率只涨不跌，-k 也测不出单块用例集的贡献（2026-11-17 踩过，同一子集 89.18% vs 49.57%）。
    exec_file 与 pom 中 prepare-agent 的默认文件（target/jacoco.exec）刻意分开命名：
    单元测试通道与接口用例通道各写各的执行数据，report 阶段显式传 dataFile 只读本轮 dump 的那份。

前置条件：
    1. 后端已用 coverage overlay 启动，容器内有 /opt/jacoco/jacocoagent.jar；
    2. 配置里的 dump.host:dump.port 可达（远端部署时先建 SSH 隧道，见 config/coverage.yml）；
    3. 配置里的 deploy.ssh 能免密执行 docker exec（取部署字节码用）。
"""
import argparse
import csv
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
DEFAULT_CONFIG = os.path.join(TESTS_DIR, "config", "coverage.yml")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="接口用例覆盖率归因与门禁（统计被测系统代码，不统计测试脚本）")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="覆盖率配置文件，默认 config/coverage.yml")
    parser.add_argument("--env", default="dev", choices=["dev", "test", "prod"], help="pytest 运行环境")
    parser.add_argument("-k", dest="keyword", default=None, help="pytest 关键字过滤，用于测量单个用例集的覆盖增量")
    parser.add_argument("-m", dest="marker", default=None, help="pytest marker 过滤")
    parser.add_argument("--check-only", action="store_true",
                        help="不执行用例，只 dump 当前累计数据并出报告（不清零 agent 计数）")
    parser.add_argument("--build", action="store_true",
                        help="改用本地 mvn compile 产出字节码，跳过从部署环境取运行中的 class。"
                             "仅适用于本机直连部署的调试；JDK 补丁版本与构建镜像不一致时会静默丢类")
    parser.add_argument("--keep-classes", action="store_true",
                        help="不刷新 backend/target/classes，直接用现有内容出报告（同一轮复算用）")
    parser.add_argument("--dump-host", default=None, help="覆盖配置里的 tcpserver 地址")
    parser.add_argument("--dump-port", type=int, default=None, help="覆盖配置里的 tcpserver 端口")
    parser.add_argument("--update-thresholds", action="store_true",
                        help="把本轮实测的行/分支覆盖率写回配置作为下限（向下取整，需人工复核后提交）")
    return parser.parse_args()


def load_config(path):
    """读取覆盖率配置，并把相对路径解析为绝对路径

    Args:
        path: config/coverage.yml 的路径

    Returns:
        dict: 原始配置 + 派生的绝对路径字段（_backend_pom/_classes_dir/_exec_file/_report_dir/_output_dir/_config_file）
    """
    import yaml
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    jacoco = cfg["jacoco"]
    gate = cfg["gate"]
    cfg["_config_file"] = path
    cfg["_backend_pom"] = os.path.join(REPO_ROOT, cfg["backend_pom"])
    # jacoco:report 没有 classDirectories 参数，只读 ${project.build.outputDirectory}，
    # 所以"用哪份字节码出报告"完全等价于"backend/target/classes 里放的是什么"。
    cfg["_classes_dir"] = os.path.join(os.path.dirname(cfg["_backend_pom"]), "target", "classes")
    jacoco["_exec_file"] = os.path.join(REPO_ROOT, jacoco["exec_file"])
    jacoco["_report_dir"] = os.path.join(REPO_ROOT, jacoco["report_dir"])
    gate["_output_dir"] = os.path.join(REPO_ROOT, gate["output_dir"])
    return cfg


def find_maven():
    """定位可执行 mvn，Windows 下必须是 .cmd 版本

    Returns:
        str: mvn 可执行文件路径

    Raises:
        EnvironmentError: 本机未安装 Maven
    """
    names = ["mvn.cmd", "mvn.bat", "mvn"] if os.name == "nt" else ["mvn"]
    for name in names:
        found = shutil.which(name)
        if found and os.path.isfile(found):
            return found
    raise EnvironmentError("未找到 mvn，请先安装 Maven 并加入 PATH（配置里 jacoco 目标依赖 mvn 执行）")


def run(cmd, cwd=None, allow_fail=False, tail=0):
    """执行外部命令，失败时打印输出并中断

    Args:
        cmd: 命令参数列表
        cwd: 工作目录
        allow_fail: 为 True 时返回退出码而不抛错
        tail: 成功时也打印输出的最后若干行。pytest 的统计行在末尾，
              只回显退出码会把最有信息量的一行丢掉

    Returns:
        int: 命令退出码
    """
    print("  $ " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(proc.stdout[-4000:] if proc.stdout else "")
        print(proc.stderr[-2000:] if proc.stderr else "")
        if not allow_fail:
            raise RuntimeError(f"命令执行失败（exit={proc.returncode}）: {cmd[0]}")
    elif tail and proc.stdout:
        print("\n".join(proc.stdout.splitlines()[-tail:]))
    return proc.returncode


def mvn_goal(cfg, goal, extra_props=None):
    """以后端 pom 为工作对象调用 jacoco 插件目标

    Args:
        cfg: 配置字典
        goal: 目标名，如 dump / report
        extra_props: 追加的 -D 参数列表

    Returns:
        int: mvn 退出码
    """
    version = str(cfg["jacoco"]["version"])
    coord = f"org.jacoco:jacoco-maven-plugin:{version}:{goal}"
    cmd = [find_maven(), "-B", "-q", "-f", cfg["_backend_pom"], coord]
    if extra_props:
        cmd += extra_props
    return run(cmd, cwd=REPO_ROOT)


def dump_execution_data(cfg, host, port, dest_file, reset=True, discard=False):
    """从运行中的后端取回 JaCoCo 执行数据

    jacoco-maven-plugin 的 dump 对 destFile 是**追加合并**写入而不是覆盖（2026-11-17 实测：
    同一子集用例，保留旧 .exec 时报告 89.18%，删掉后同一命令 49.57%）。
    所以每次 dump 前必须先删掉旧文件，否则报告算的是历轮并集——门禁失去发现回归的能力，
    `-k` 也测不出单块用例集的覆盖贡献。

    Args:
        cfg: 配置字典
        host: tcpserver 地址
        port: tcpserver 端口
        dest_file: .exec 落地路径
        reset: 取数后是否清零 agent 计数器
        discard: 为 True 时这次取数只为清零计数器，落地的数据随即删除
    """
    if os.path.exists(dest_file):
        os.remove(dest_file)
    props = [
        f"-Djacoco.address={host}",
        f"-Djacoco.port={port}",
        f"-Djacoco.destFile={dest_file}",
        f"-Djacoco.reset={'true' if reset else 'false'}",
        f"-Djacoco.retryCount={cfg['jacoco']['dump'].get('retry_count', 10)}",
    ]
    mvn_goal(cfg, "dump", props)
    if discard:
        # 清零用的这次取数拿到的是"上一轮之后累计跑到的代码"（可能含手工请求、别的用例集），
        # 不属于本轮接口用例的贡献，删掉
        if os.path.exists(dest_file):
            os.remove(dest_file)
    elif not os.path.exists(dest_file):
        raise RuntimeError(f"未生成执行数据文件 {dest_file}，说明 dump 没拿到 agent 数据")


def run_pytest(cfg, args):
    """执行接口用例，这是覆盖率的唯一驱动来源

    Args:
        cfg: 配置字典
        args: 命令行参数

    Returns:
        int: pytest 退出码
    """
    cmd = [sys.executable, "-m", "pytest"]
    if args.keyword:
        cmd += ["-k", args.keyword]
    if args.marker:
        cmd += ["-m", args.marker]
    cmd += [f"--env={args.env}"]
    return run(cmd, cwd=TESTS_DIR, allow_fail=True, tail=15)


def compile_backend(cfg):
    """用本地 mvn compile 产出 backend/target/classes

    只在被测服务就跑在本机、字节码天然一致时可用。作为覆盖率结论的来源时不可靠：
    本地 javac 与构建镜像的 JDK 补丁版本不同就会产出不同的类文件，class id 对不上的类
    被 JaCoCo 静默丢弃，报告显示 0 覆盖而不是报错。
    """
    run([find_maven(), "-B", "-q", "-f", cfg["_backend_pom"], "compile"], cwd=REPO_ROOT)


def sync_deployed_classes(cfg):
    """从运行中的容器里取回实际执行的字节码，覆盖 backend/target/classes

    这是让报告可信的关键一步：jacoco:report 只能读 backend/target/classes，
    而执行数据是按 class id（类文件内容哈希）匹配的，两边必须是同一份字节码。

    Args:
        cfg: 配置字典

    Returns:
        int: 同步到本地的 class 文件数

    Raises:
        EnvironmentError: 配置缺少 deploy.ssh，或容器内取不到 class
    """
    deploy = cfg.get("deploy") or {}
    target = deploy.get("ssh")
    if not target:
        raise EnvironmentError(
            "config/coverage.yml 的 deploy.ssh 为空，无法取回部署字节码。"
            "服务部署在远端时填 ssh 目标（需免密）；服务跑在本机时才用 --build")

    container = deploy["container"]
    jar = deploy["jar"]
    prefix = deploy.get("classes_prefix", "BOOT-INF/classes/")
    root = prefix.rstrip("/")
    # 镜像是运行时精简镜像，有 busybox 的 unzip/tar，没有 jar；
    # tar 成功后再清理临时目录，失败时退出码仍是 tar 的，不会被 rm 掩盖
    inner = (f"cd /tmp && rm -rf jacoco_classes && mkdir jacoco_classes && cd jacoco_classes "
             f"&& unzip -q -o {shlex.quote(jar)} {shlex.quote(prefix + '*')} "
             f"&& tar -cf - {shlex.quote(root)} "
             f"&& cd / && rm -rf /tmp/jacoco_classes")
    remote = f"docker exec {shlex.quote(container)} sh -c {shlex.quote(inner)}"
    cmd = ["ssh", "-o", "BatchMode=yes", target, remote]
    print(f"  $ ssh {target} docker exec {container} <unzip {jar}:{prefix} 并打包>")
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise EnvironmentError(
            f"取回部署字节码失败（exit={proc.returncode}）："
            f"{(proc.stderr or b'').decode('utf-8', 'replace').strip()[-1500:]}\n"
            f"请确认 {target} 能免密登录、容器 {container} 在运行、jar 路径 {jar} 正确")

    classes_dir = cfg["_classes_dir"]
    members = []
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith(".class"):
                continue
            rel = member.name[len(root) + 1:]
            if rel.startswith(("/", "\\")) or ".." in rel.replace("\\", "/").split("/"):
                raise EnvironmentError(f"部署产物里有异常路径：{member.name}")
            members.append((rel, member))
        if not members:
            raise EnvironmentError(
                f"容器 {container} 的 {jar} 里没找到 {prefix} 下的 class，"
                "请核对 config/coverage.yml 的 deploy.jar 与 deploy.classes_prefix")

        shutil.rmtree(classes_dir, ignore_errors=True)
        for rel, member in members:
            dest = os.path.join(classes_dir, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with archive.extractfile(member) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    return len(members)


def generate_report(cfg):
    """用本轮 dump 的 .exec 生成 HTML/XML/CSV 报告（落在 maven 默认目录）

    dataFile 必须显式指定：jacoco:report 的默认值是 ${project.build.directory}/jacoco.exec，
    与 pom 里 prepare-agent 给单元测试用的文件名相同。接口用例通道与单元测试通道各写各的
    执行数据文件，显式传参才能保证报告读的是本轮 dump 的那份，不被本机跑过的 mvn test 覆盖。
    """
    mvn_goal(cfg, "report", [f"-Djacoco.dataFile={cfg['jacoco']['_exec_file']}"])
    csv_path = os.path.join(cfg["jacoco"]["_report_dir"], "jacoco.csv")
    if not os.path.exists(csv_path):
        raise RuntimeError(
            f"未生成 {csv_path}，请确认 {cfg['jacoco']['_exec_file']} 存在，"
            f"且 {cfg['_classes_dir']} 里有字节码（默认由 deploy.ssh 从容器取回）")
    return csv_path


def read_coverage(csv_path, prefix, excludes):
    """解析 jacoco.csv，按包汇总行/分支/方法覆盖

    Args:
        csv_path: jacoco.csv 路径
        prefix: 只保留以此包前缀开头的类，如 com.hr.
        excludes: 不计入合计的包前缀列表

    Returns:
        (list, dict): 按行覆盖率排序的包级明细，以及计入门禁的合计计数
    """
    counters = ("line", "branch", "method")
    per_pkg = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            pkg = (row.get("PACKAGE") or "").replace("/", ".").strip()
            if prefix and not pkg.startswith(prefix):
                continue
            agg = per_pkg.setdefault(pkg, {name: [0, 0] for name in counters})
            for name, missed_col in (("line", "LINE"), ("branch", "BRANCH"), ("method", "METHOD")):
                agg[name][0] += int(row[f"{missed_col}_MISSED"])
                agg[name][1] += int(row[f"{missed_col}_COVERED"])

    packages = []
    for pkg, agg in sorted(per_pkg.items()):
        entry = {"package": pkg, "excluded": any(pkg.startswith(e) for e in excludes)}
        for name in counters:
            missed, covered = agg[name]
            entry[name] = {"missed": missed, "covered": covered, "total": missed + covered,
                           "percent": percent(covered, missed + covered)}
        packages.append(entry)

    total = {name: [0, 0] for name in counters}
    for entry in packages:
        if entry["excluded"]:
            continue
        for name in counters:
            total[name][0] += entry[name]["missed"]
            total[name][1] += entry[name]["covered"]
    totals = {name: {"missed": v[0], "covered": v[1], "total": v[0] + v[1],
                     "percent": percent(v[1], v[0] + v[1])} for name, v in total.items()}
    return packages, totals


def percent(covered, total):
    """覆盖率百分比，总数为 0 时返回 None 而不是除零"""
    if not total:
        return None
    return round(covered * 100.0 / total, 2)


def fmt(pct):
    """把百分比渲染成定宽字符串，None 显示为 n/a"""
    return "n/a " if pct is None else f"{pct:.2f}"


def print_table(packages, totals, prefix):
    """打印包级覆盖率明细表"""
    scope = prefix or "全部"
    print(f"\n覆盖率归因（统计范围 {scope}，仅被测系统代码）")
    print(f"{'包':<28}{'行覆盖':>12}{'行%':>9}{'分支%':>9}{'方法%':>9}  计入门禁")
    print("-" * 84)
    for entry in packages:
        cells = [entry["package"],
                 f"{entry['line']['covered']}/{entry['line']['total']}",
                 fmt(entry["line"]["percent"]),
                 fmt(entry["branch"]["percent"]),
                 fmt(entry["method"]["percent"]),
                 "否" if entry["excluded"] else "是"]
        print(f"{cells[0]:<28}{cells[1]:>12}{cells[2]:>9}{cells[3]:>9}{cells[4]:>9}  {cells[5]}")
    print("-" * 84)
    total_lines = f"{totals['line']['covered']}/{totals['line']['total']}"
    print(f"{'合计':<28}{total_lines:>12}{fmt(totals['line']['percent']):>9}"
          f"{fmt(totals['branch']['percent']):>9}{fmt(totals['method']['percent']):>9}")


def write_outputs(cfg, packages, totals, meta):
    """归档报告目录并写出 JSON 摘要，供后续 CI 阶段消费

    Args:
        cfg: 配置字典
        packages: 包级明细
        totals: 合计计数
        meta: 本轮元信息（环境、时间、阈值判定结果等）

    Returns:
        (str, str): 归档 HTML 路径、summary.json 路径
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = cfg["gate"]["_output_dir"]
    os.makedirs(out, exist_ok=True)
    archived = os.path.join(out, stamp)
    shutil.copytree(cfg["jacoco"]["_report_dir"], archived, dirs_exist_ok=True)
    latest = os.path.join(out, "latest")
    shutil.rmtree(latest, ignore_errors=True)
    shutil.copytree(cfg["jacoco"]["_report_dir"], latest)

    summary = {"meta": meta, "totals": totals, "packages": packages}
    summary_path = os.path.join(out, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    return os.path.join(archived, "index.html"), summary_path


def evaluate_gate(cfg, totals):
    """按配置阈值判定门禁

    Args:
        cfg: 配置字典
        totals: 合计计数

    Returns:
        (bool, str): 是否通过、说明文字。阈值未设置时判为通过并提示
    """
    thresholds = cfg["gate"].get("thresholds") or {}
    lines = []
    passed = True
    for metric in ("line", "branch"):
        limit = thresholds.get(metric)
        actual = totals[metric]["percent"]
        if limit is None:
            lines.append(f"{metric}: 未设阈值（实测 {fmt(actual)}%）")
            continue
        ok = actual is not None and actual >= float(limit)
        passed = passed and ok
        lines.append(f"{metric}: 实测 {fmt(actual)}% / 阈值 {limit}% → {'达标' if ok else '未达标'}")
    if all(thresholds.get(m) is None for m in ("line", "branch")):
        return True, "阈值未配置，本轮只测量不归因判定。核对口径后用 --update-thresholds 固化下限。\n" + "\n".join(lines)
    return passed, "\n".join(lines)


def update_thresholds(cfg, totals):
    """把本轮实测覆盖率写回配置作为门禁下限（向下取整，形成只升不降的棘轮）

    Args:
        cfg: 配置字典
        totals: 合计计数
    """
    path = cfg["_config_file"]
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    for metric in ("line", "branch"):
        value = totals[metric]["percent"]
        if value is None:
            continue
        new_value = int(value)
        text = re.sub(rf"^(\s+{metric}: )(.*)$", rf"\g<1>{new_value}", text, count=1, flags=re.M)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"已把门禁阈值写回 {path}（向下取整，请复核后再提交）")


def setup_stdout():
    """统一输出编码：管道/重定向时用 UTF-8，交互终端保持控制台原生编码

    GBK 控制台只有在沿用系统编码时才能正常显示中文，
    因此不能无条件切 UTF-8，否则重定向到文件才会乱码。
    """
    try:
        if not sys.stdout.isatty():
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass


def main():
    """主流程：清零 → 跑用例 → 取数 → 出报告 → 归因 → 门禁判定"""
    setup_stdout()
    args = parse_args()
    cfg = load_config(args.config)
    host = args.dump_host or cfg["jacoco"]["dump"]["host"]
    port = args.dump_port or cfg["jacoco"]["dump"]["port"]
    exec_file = cfg["jacoco"]["_exec_file"]

    print(f"覆盖率采集通道：{host}:{port}（JaCoCo tcpserver）")

    classes_source = "keep"
    if args.keep_classes:
        print("\n[准备] 沿用现有 backend/target/classes（--keep-classes）")
    elif args.build:
        print("\n[准备] 本地编译产出字节码（--build）")
        print("        警告：本机 JDK 与构建镜像的补丁版本不同会静默丢类，此模式的数字不能作为覆盖率结论")
        compile_backend(cfg)
        classes_source = "local-build"
    else:
        print("\n[准备] 取回运行中的字节码")
        try:
            classes = sync_deployed_classes(cfg)
        except Exception as exc:
            print(f"取回失败：{exc}")
            print("没有一致的字节码就无法出报告：修好 ssh/容器后再复跑，"
                  "或本机直连部署时临时用 --build（数字不可信）")
            return 2
        print(f"        已用容器内的 class 覆盖 backend/target/classes（{classes} 个）")
        classes_source = "deployed"

    if args.check_only:
        print("\n[1/5] 跳过清零（--check-only：读上一轮取数之后新跑到的代码）")
        print("        上一轮完整采集结束时计数器已清零，期间没有流量的话本轮就是 0%")
    else:
        print("\n[1/5] 清零历史计数")
        try:
            dump_execution_data(cfg, host, port, exec_file, discard=True)
        except Exception as exc:
            print(f"清零失败：{exc}")
            print("请确认后端已用 coverage overlay 启动，且端口可达（重建走 Compose v2）：\n"
                  "  docker compose -f docker-compose.yml -f docker-compose.coverage.yml up -d backend\n"
                  "  远端部署时先建隧道：ssh -N -L 6300:127.0.0.1:6300 root@106.12.144.134")
            return 2

    pytest_exit = 0
    if not args.check_only:
        print(f"\n[2/5] 执行接口用例（env={args.env}）")
        pytest_exit = run_pytest(cfg, args)
        if pytest_exit not in (0, 1):
            print(f"pytest 以 {pytest_exit} 退出（非正常收集/执行），覆盖率数据不可信，终止")
            return 2
    else:
        print("\n[2/5] 跳过用例执行（--check-only）")

    print("\n[3/5] 取回执行数据" + ("（保留累计计数，供下次复算）" if args.check_only else ""))
    dump_execution_data(cfg, host, port, exec_file, reset=not args.check_only)

    print("\n[4/5] 生成 JaCoCo 报告")
    csv_path = generate_report(cfg)

    print("\n[5/5] 按包归因")
    packages, totals = read_coverage(csv_path,
                                     cfg["jacoco"]["package_prefix"],
                                     cfg["gate"].get("exclude_packages") or [])
    print_table(packages, totals, cfg["jacoco"]["package_prefix"])

    if totals["line"]["total"] == 0:
        print("\n警告：报告里没有匹配到任何被测类。逐项检查 config/coverage.yml 的 package_prefix、"
              f"backend/target/classes 是否非空（本轮字节码来源：{classes_source}）、"
              "agent 启动参数里的 includes=com.hr.*")
    elif totals["line"]["covered"] == 0 and not args.check_only:
        print("\n警告：用例已执行但覆盖为 0。先确认报告的字节码口径：")
        print("  --build / --keep-classes 下，backend/target/classes 与容器里运行的类不是同一份时，"
              "JaCoCo 会按 class id 静默丢弃执行数据——去掉这两个开关复跑，让它取部署字节码")
        print("  取部署字节码后仍为 0，才按用例侧排查：请求是否真的打到了这个后端（base_url、隧道、防火墙）")

    passed, verdict = evaluate_gate(cfg, totals)
    archived_html, summary_path = write_outputs(
        cfg, packages, totals,
        {"env": args.env, "host": host, "port": port, "driver": "check-only" if args.check_only else "pytest",
         "keyword": args.keyword, "marker": args.marker, "pytest_exit": pytest_exit,
         "classes_source": classes_source,
         "captured_at": datetime.now().isoformat(timespec="seconds")})
    print(f"\nHTML 报告：{archived_html}")
    print(f"最新报告：{os.path.join(cfg['gate']['_output_dir'], 'latest', 'index.html')}")
    print(f"机器可读摘要：{summary_path}")

    if args.update_thresholds:
        update_thresholds(cfg, totals)

    print("\n门禁判定：" + ("通过" if passed else "不通过"))
    print(verdict)
    if pytest_exit != 0:
        print("提示：本轮存在未通过用例，覆盖率不能作为质量结论，先按失败归因处理用例再复测")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
