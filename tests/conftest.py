# -*- coding: utf-8 -*-
"""
pytest 公共 fixture（根目录副本）
pytest 要求 conftest.py 位于测试目录或其父目录才能自动发现
此文件与 fixtures/conftest.py 内容一致，确保 pytest 能正确加载所有 fixture

环境切换（三选一，优先级从高到低）：
    1. pytest --env test          # 命令行参数
    2. HR_ENV=test pytest         # 环境变量
    3. 默认 dev                   # 兜底

Allure 报告集成：
    - 自动设置环境信息（测试环境、服务地址、执行时间）
    - 自动标记 feature / story / severity / title
    - 失败用例自动附加请求和响应详情
"""
import re
import pytest
import allure
import sys
import os

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from common.request_handler import BaseRequest
from common.data_factory import DataFactory, DataCleaner
from common.logger import logger
from api.auth_api import AuthAPI
from api.employee_api import EmployeeAPI
from api.department_api import DepartmentAPI
from config import Config, switch_env, VALID_ENVS


# ── pytest 钩子：在任何 fixture 初始化之前完成环境切换 ────────────────────────

def pytest_addoption(parser):
    """
    注册 --env 命令行参数

    用法：
        pytest --env dev          # 开发环境（默认）
        pytest --env test         # 测试环境
        pytest --env prod         # 生产环境
    """
    parser.addoption(
        "--env",
        action="store",
        default=None,
        choices=list(VALID_ENVS),
        help="运行环境：dev（开发）/ test（测试）/ prod（生产），默认读取 HR_ENV 或 dev",
    )


def pytest_configure(config):
    """
    pytest 启动钩子：根据 --env 参数或 HR_ENV 环境变量切换配置

    执行时机早于所有 fixture 初始化，确保 Config 已是目标环境值。
    """
    env_name = config.getoption("--env") or os.getenv("HR_ENV", "dev")
    switch_env(env_name)
    logger.info(f"[conftest] 当前环境: {Config.ENV_NAME} -> {Config.BASE_URL}")


def pytest_collection_modifyitems(items):
    """
    收集用例后自动设置 Allure 标签

    规则：
        feature    ← 模块文件名（test_auth → 认证模块）
        story      ← 类名（TestLogin → 登录接口）
        severity   ← docstring 首行的用例级别 [P0]/[P1]/[P2]，缺失时回退 TC 编号前缀
        title      ← docstring 首行（TC 编号 + 级别 + 标题）
        description ← 类 docstring

    级别由测试用例表（HR系统测试用例.xlsx）同步到 docstring，
    用例代码里不需要手写任何 allure 装饰器。
    """
    feature_map = {
        "test_auth": "认证模块",
        "test_employee": "员工管理模块",
        "test_department": "部门管理模块",
    }
    severity_map = {
        "AUTH": allure.severity_level.CRITICAL,
        "EMP":  allure.severity_level.CRITICAL,
        "DP":   allure.severity_level.CRITICAL,
        "LIST": allure.severity_level.NORMAL,
        "DET":  allure.severity_level.NORMAL,
        "EDT":  allure.severity_level.NORMAL,
        "DU":   allure.severity_level.NORMAL,
        "DEL":  allure.severity_level.NORMAL,
        "DX":   allure.severity_level.NORMAL,
        "DD":   allure.severity_level.NORMAL,
        "DN":   allure.severity_level.MINOR,
    }
    priority_map = {
        "P0": allure.severity_level.CRITICAL,
        "P1": allure.severity_level.NORMAL,
        "P2": allure.severity_level.MINOR,
    }

    for item in items:
        module_name = item.module.__name__.split(".")[-1]
        feature_name = feature_map.get(module_name, module_name)
        item.add_marker(allure.label("feature", feature_name))

        cls = item.cls
        if cls:
            story_name = re.sub(r"^Test", "", cls.__name__)
            story_name = re.sub(r"([A-Z])", r" \1", story_name).strip()
            item.add_marker(allure.label("story", story_name))

            if cls.__doc__:
                item.add_marker(allure.label("description", cls.__doc__))

        doc = item.function.__doc__ or ""
        first_line = doc.strip().split("\n")[0].strip() if doc.strip() else ""

        tc_match = re.match(r"(TC-\w+-\d+)", first_line)
        if tc_match:
            allure.title(first_line)(item.function)

        priority_match = re.search(r"\[(P\d)\]", first_line)
        if priority_match:
            severity = priority_map.get(priority_match.group(1), allure.severity_level.NORMAL)
        else:
            tc_prefix = tc_match.group(1).split("-")[1] if tc_match else ""
            severity = severity_map.get(tc_prefix, allure.severity_level.NORMAL)
        item.add_marker(allure.severity(severity))


# ── Allure 环境信息 ─────────────────────────────────────────────────────────

def _write_allure_environment(allure_results_dir):
    """
    向 Allure 结果目录写入 environment.properties
    Allure 报告会自动读取该文件并在 Environment 面板展示
    """
    env_file = os.path.join(allure_results_dir, "environment.properties")
    os.makedirs(allure_results_dir, exist_ok=True)
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"测试环境={Config.ENV_NAME}\n")
        f.write(f"服务地址={Config.BASE_URL}\n")
        f.write(f"Python={sys.version.split()[0]}\n")
        f.write(f"pytest={pytest.__version__}\n")
        f.write(f"执行时间={__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")


@pytest.fixture(scope="session", autouse=True)
def allure_environment_session(request):
    """
    会话级别：在首次测试前写入 Allure environment.properties
    """
    allure_results_dir = request.config.getoption("--alluredir", default="reports/allure-results")
    _write_allure_environment(allure_results_dir)


# ── 失败用例请求/响应附件 ────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def allure_request_capture(request, request_client):
    """
    失败用例自动在 Allure 报告中附加请求和响应详情

    仅对使用 request_client 的接口测试用例生效；
    直接用 requests 库调用的用例（如未认证场景）无附件。
    """
    client = request_client
    yield
    if not (hasattr(request.node, "rep_call") and request.node.rep_call.failed):
        return
    if getattr(client, "last_request", None):
        req = client.last_request
        with allure.step(f"[附件] {req['method']} {req['url']}"):
            allure.attach(
                str(req.get("body", "")),
                name="Request Body",
                attachment_type=allure.attachment_type.JSON,
            )
    if getattr(client, "last_response", None):
        resp = client.last_response
        allure.attach(
            f"HTTP {resp['status_code']}\n{resp.get('body', '')}",
            name="Response",
            attachment_type=allure.attachment_type.JSON,
        )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    将每条用例的执行结果挂到 item.rep_call / rep_setup / rep_teardown
    供 allure_request_capture fixture 判断是否失败
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ── 基础 fixture ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url():
    """
    获取服务基础地址

    Returns:
        str: 当前环境的 BASE_URL
    """
    return Config.BASE_URL


@pytest.fixture(scope="session")
def request_client():
    """
    带认证的请求客户端（session 级别）
    自动登录并设置 Token，整个测试会话期间复用

    Returns:
        BaseRequest: 已设置认证 Token 的请求客户端实例
    """
    client = BaseRequest()
    auth_api = AuthAPI(client)
    token = auth_api.login_and_get_token(Config.ADMIN_USERNAME, Config.ADMIN_PASSWORD)
    client.set_token(token)
    logger.info("[Fixture] 全局认证客户端已初始化")
    return client


@pytest.fixture(scope="session")
def no_auth_client():
    """
    不带认证的请求客户端（用于测试未登录场景）

    Returns:
        BaseRequest: 未设置 Token 的请求客户端实例
    """
    return BaseRequest()


# ── API 封装 fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def auth_api(request_client):
    """
    认证 API 封装实例

    Args:
        request_client: 带认证的请求客户端

    Returns:
        AuthAPI: 认证接口操作封装
    """
    return AuthAPI(request_client)


@pytest.fixture(scope="session")
def employee_api(request_client):
    """
    员工 API 封装实例

    Args:
        request_client: 带认证的请求客户端

    Returns:
        EmployeeAPI: 员工管理接口操作封装
    """
    return EmployeeAPI(request_client)


@pytest.fixture(scope="session")
def department_api(request_client):
    """
    部门 API 封装实例

    Args:
        request_client: 带认证的请求客户端

    Returns:
        DepartmentAPI: 部门管理接口操作封装
    """
    return DepartmentAPI(request_client)


# ── 数据工具 fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def data_cleaner(request_client):
    """
    数据清理器（每个用例独立实例）
    用例执行完毕后自动清理测试过程中创建的数据

    Args:
        request_client: 带认证的请求客户端，用于发送删除请求

    Yields:
        DataCleaner: 数据清理器实例，用例结束自动调用 cleanup()
    """
    cleaner = DataCleaner(request_client)
    yield cleaner
    cleaner.cleanup()
    logger.info("[Fixture] 测试数据已清理")


@pytest.fixture
def data_factory():
    """
    数据工厂（返回 DataFactory 类本身）
    用于在测试用例中生成随机测试数据

    Returns:
        type: DataFactory 类（非实例，直接调用静态方法）
    """
    return DataFactory


# ── 预置数据 fixture ─────────────────────────────────────────────────────────

@pytest.fixture
def created_employee(employee_api, data_factory, data_cleaner):
    """
    预创建一个员工，用例结束自动删除
    返回包含 id 的完整员工数据字典

    Args:
        employee_api: 员工 API 封装
        data_factory: 数据工厂
        data_cleaner: 数据清理器

    Returns:
        dict: 员工数据，包含 id、name、phone、department 等字段
    """
    payload = data_factory.employee_payload()
    resp = employee_api.create(payload)
    assert resp.status_code == 200, f"预创建员工失败: {resp.text}"
    employee = resp.json()["data"]
    data_cleaner.track_employee(employee["id"])
    logger.info(f"[Fixture] 预创建员工: id={employee['id']}, name={employee['name']}")
    return employee


@pytest.fixture
def created_department(department_api, data_factory, data_cleaner):
    """
    预创建一个部门，用例结束自动删除
    返回包含 id 的完整部门数据字典

    Args:
        department_api: 部门 API 封装
        data_factory: 数据工厂
        data_cleaner: 数据清理器

    Returns:
        dict: 部门数据，包含 id、name、description、manager 等字段
    """
    payload = data_factory.department_payload()
    resp = department_api.create(payload)
    assert resp.status_code == 200, f"预创建部门失败: {resp.text}"
    department = resp.json()["data"]
    data_cleaner.track_department(department["id"])
    logger.info(f"[Fixture] 预创建部门: id={department['id']}, name={department['name']}")
    return department


@pytest.fixture
def two_employees(employee_api, data_factory, data_cleaner):
    """
    预创建两个员工（用于冲突测试、编辑覆盖等场景）

    Args:
        employee_api: 员工 API 封装
        data_factory: 数据工厂
        data_cleaner: 数据清理器

    Returns:
        list[dict]: 包含两个员工数据字典的列表
    """
    employees = []
    for i in range(2):
        payload = data_factory.employee_payload()
        resp = employee_api.create(payload)
        assert resp.status_code == 200
        emp = resp.json()["data"]
        data_cleaner.track_employee(emp["id"])
        employees.append(emp)
    logger.info(f"[Fixture] 预创建 2 个员工: {[e['id'] for e in employees]}")
    return employees


@pytest.fixture
def two_departments(department_api, data_factory, data_cleaner):
    """
    预创建两个部门（用于名称冲突测试、编辑覆盖等场景）

    Args:
        department_api: 部门 API 封装
        data_factory: 数据工厂
        data_cleaner: 数据清理器

    Returns:
        list[dict]: 包含两个部门数据字典的列表
    """
    departments = []
    for i in range(2):
        payload = data_factory.department_payload()
        resp = department_api.create(payload)
        assert resp.status_code == 200
        dept = resp.json()["data"]
        data_cleaner.track_department(dept["id"])
        departments.append(dept)
    logger.info(f"[Fixture] 预创建 2 个部门: {[d['id'] for d in departments]}")
    return departments
