# -*- coding: utf-8 -*-
"""
统一测试执行入口
用法：
    python run.py                  # 默认 dev 环境，生成全部报告
    python run.py --env test       # 指定测试环境
    python run.py --env prod -k login   # 指定环境 + 关键字过滤
    python run.py --no-allure      # 跳过 Allure 报告（仅 HTML）
    python run.py --no-html        # 跳过 HTML 报告（仅 Allure）
"""
import sys
import os
import subprocess
import argparse
import shutil
from datetime import datetime

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")


def parse_args():
    parser = argparse.ArgumentParser(description="HR 系统自动化测试执行器")
    parser.add_argument("--env", default="dev", choices=["dev", "test", "prod"],
                        help="运行环境（默认 dev）")
    parser.add_argument("-k", dest="keyword", default=None,
                        help="用例关键字过滤，如 -k login")
    parser.add_argument("--no-allure", action="store_true",
                        help="不生成 Allure 报告")
    parser.add_argument("--no-html", action="store_true",
                        help="不生成 HTML 报告")
    parser.add_argument("--allure-serve", action="store_true",
                        help="执行完毕后自动打开 Allure 报告预览")
    parser.add_argument("testpath", nargs="*", default=["testcases/api/"],
                        help="测试路径（默认 testcases/api/）")
    return parser.parse_args()


def clean_old_results():
    """清理上一轮的原始结果，保留历史报告"""
    for d in ["allure-results"]:
        path = os.path.join(REPORTS_DIR, d)
        if os.path.exists(path):
            shutil.rmtree(path)


def build_pytest_cmd(args, timestamp):
    """构建 pytest 命令"""
    cmd = [
        sys.executable, "-m", "pytest",
        *args.testpath,
        f"--env={args.env}",
        f"--alluredir={os.path.join(REPORTS_DIR, 'allure-results')}",
    ]

    if not args.no_html:
        html_path = os.path.join(REPORTS_DIR, f"report_{timestamp}.html")
        cmd += [f"--html={html_path}", "--self-contained-html"]

    if args.keyword:
        cmd += ["-k", args.keyword]

    return cmd


def generate_allure_report():
    """调用 allure 命令行生成静态 HTML 报告"""
    results_dir = os.path.join(REPORTS_DIR, "allure-results")
    report_dir = os.path.join(REPORTS_DIR, "allure-report")

    if not os.path.exists(results_dir):
        print("[WARN] allure-results 目录不存在，跳过 Allure 报告生成")
        return None

    # 清理旧报告
    if os.path.exists(report_dir):
        shutil.rmtree(report_dir)

    try:
        subprocess.run(
            ["allure", "generate", results_dir, "-o", report_dir, "--clean"],
            check=True, capture_output=True, text=True,
        )
        return report_dir
    except FileNotFoundError:
        print("[WARN] allure 命令未找到，跳过 Allure 报告生成")
        print("       安装: https://github.com/allure-framework/allure2/releases")
        return None
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Allure 报告生成失败: {e.stderr}")
        return None


def print_summary(timestamp, html_path, allure_report_dir, returncode):
    """打印执行摘要"""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  测试执行摘要")
    print(f"  时间: {timestamp}")
    print(f"  结果: {'PASS' if returncode == 0 else 'FAIL'} (exit code: {returncode})")
    print(sep)

    if html_path and os.path.exists(html_path):
        print(f"  HTML 报告: {html_path}")

    if allure_report_dir and os.path.exists(allure_report_dir):
        print(f"  Allure 报告: {allure_report_dir}")
        print(f"  预览命令:  allure open {allure_report_dir}")

    print(sep)


def main():
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"[run] 环境: {args.env}")
    print(f"[run] 用例: {' '.join(args.testpath)}")
    if args.keyword:
        print(f"[run] 过滤: -k {args.keyword}")
    print()

    # 清理旧结果
    clean_old_results()

    # 执行 pytest
    cmd = build_pytest_cmd(args, timestamp)
    print(f"[run] {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=ROOT_DIR)

    # 生成 Allure 报告
    allure_report_dir = None
    if not args.no_allure:
        allure_report_dir = generate_allure_report()

    # 查找 HTML 报告路径
    html_path = None
    if not args.no_html:
        html_path = os.path.join(REPORTS_DIR, f"report_{timestamp}.html")

    # 打印摘要
    print_summary(timestamp, html_path, allure_report_dir, result.returncode)

    # 自动打开 Allure
    if args.allure_serve and allure_report_dir:
        subprocess.Popen(["allure", "open", allure_report_dir])

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
