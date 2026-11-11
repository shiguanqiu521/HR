# -*- coding: utf-8 -*-
"""
员工管理接口测试

覆盖 TC-EMP-*（新增/场景）、TC-LIST-*（列表）、TC-DET-*（详情）、TC-EDT-*（编辑）、TC-DEL-*（删除）
已合并删除的编号（不回收）：TC-EMP-003/007/016/017/019/022、TC-LIST-003/004/009、TC-DEL-005/006
设计方法：等价类划分、边界值分析（上下界成对）、判定表（校验优先级与短路）、场景法、错误推测法
预期基线：EmployeeRequest 注解 + EmployeeService 校验顺序 + GlobalExceptionHandler + AuthInterceptor
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.assertions import AssertUtil

UNREADABLE_BODY = "请求体格式错误，无法解析"
NOT_FOUND_PREFIX = "员工不存在或已被删除"


class TestEmployeeCreate:
    """POST /api/employees"""

    def test_create_success(self, employee_api, data_factory, data_cleaner):
        """TC-EMP-001 [P0] 新增员工-全部字段正确（含服务端时间字段生成）

        等价类：全字段合法。同时锚定 TC-EMP-022 合并进来的判定点——
        createdAt/updatedAt 由服务端生成（请求体本就不含），且新增响应与详情回读一致。
        """
        payload = data_factory.employee_payload(phone=data_factory.unique_phone())
        resp = employee_api.create(payload)
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        data_cleaner.track_employee(data["id"])

        assert data["id"] > 0
        for field in ("name", "phone", "department", "position", "status", "hireDate"):
            assert data[field] == payload[field], f"{field} 应与请求一致"
        assert data["createdAt"], "createdAt 应由服务端生成"
        assert data["updatedAt"] == data["createdAt"], "新建记录的创建/更新时间应相等"

        detail = employee_api.get_detail(data["id"]).json()["data"]
        assert detail == data, "create() 内部回读 DB，新增响应应与详情完全一致"

    @pytest.mark.parametrize("status", ["在职", "试用期", "离职"])
    def test_create_valid_status(self, employee_api, data_factory, data_cleaner, status):
        """TC-EMP-002 [P0] 新增员工-status 枚举有效值（在职/试用期/离职）

        等价类：ALLOWED_STATUS 的三个有效值，以数据行覆盖（原 TC-EMP-003 已并入）。
        """
        payload = data_factory.employee_payload(status=status, phone=data_factory.unique_phone())
        resp = employee_api.create(payload)
        AssertUtil.assert_response_success(resp, f"status={status}: ")
        data_cleaner.track_employee(resp.json()["data"]["id"])
        assert resp.json()["data"]["status"] == status

    def test_create_name_empty(self, employee_api, data_factory):
        """TC-EMP-004 [P0] 新增员工-name为空

        等价类：必填字段 name 为空。message 逐字段定位是必填校验的判定点。
        """
        payload = data_factory.employee_payload(name="")
        AssertUtil.assert_validation_error(employee_api.create(payload), "姓名不能为空", "name 为空: ")

    def test_create_phone_empty(self, employee_api, data_factory):
        """TC-EMP-005 [P0] 新增员工-phone为空

        等价类：phone 同时挂 @NotBlank 与 @Pattern，"" 非 null 因此两个注解都失败，
        message 是两条提示的拼接（源码 EmployeeRequest.phone + 全局异常处理器 "; " 拼接）。
        """
        payload = data_factory.employee_payload(phone="")
        resp = employee_api.create(payload)
        AssertUtil.assert_validation_error(resp, "手机号不能为空", "phone 为空: ")
        AssertUtil.assert_message_contains(resp, "手机号格式不正确", "phone 为空: ")

    @pytest.mark.parametrize("phone,label", [
        ("12345", "位数不足"),
        ("138abcd0000", "含字母"),
        ("23800138000", "号段非法"),
        ("1380013800012345678", "超长"),
    ])
    def test_create_phone_invalid_format(self, employee_api, data_factory, phone, label):
        """TC-EMP-006 [P0] 新增员工-phone 格式非法

        等价类：@Pattern(^1[3-9]\\d{9}$) 的各失败维度，以数据行覆盖
        （原 TC-EMP-007 含字母、TC-EMP-017 号段非法已并入）。
        """
        payload = data_factory.employee_payload(phone=phone)
        AssertUtil.assert_validation_error(employee_api.create(payload), "手机号格式不正确", f"{label} {phone}: ")

    def test_create_phone_duplicate(self, employee_api, data_factory, created_employee):
        """TC-EMP-008 [P0] 新增员工-phone重复

        判定表：参数合法但业务唯一性冲突 → 409（不是 400）。
        """
        payload = data_factory.employee_payload(phone=created_employee["phone"])
        resp = employee_api.create(payload)
        AssertUtil.assert_status_code(resp, 409)
        AssertUtil.assert_biz_code(resp, 409)
        AssertUtil.assert_message_contains(resp, "手机号已存在")
        assert created_employee["phone"] in resp.json()["message"], "message 应回显被占用的号码"
        listing = employee_api.list(name=payload["name"]).json()["data"]
        assert listing["total"] == 0, "查重失败不应落库"

    def test_create_department_empty(self, employee_api, data_factory):
        """TC-EMP-009 [P0] 新增员工-department为空"""
        payload = data_factory.employee_payload(department="")
        AssertUtil.assert_validation_error(employee_api.create(payload), "部门不能为空", "department 为空: ")

    def test_create_position_empty(self, employee_api, data_factory):
        """TC-EMP-010 [P0] 新增员工-position为空"""
        payload = data_factory.employee_payload(position="")
        AssertUtil.assert_validation_error(employee_api.create(payload), "岗位不能为空", "position 为空: ")

    @pytest.mark.parametrize("mode", ["显式null", "字段缺失"])
    def test_create_hire_date_missing(self, employee_api, data_factory, mode):
        """TC-EMP-011 [P0] 新增员工-hireDate 为 null 或字段缺失

        等价类：@NotNull 分支。原用例的 hireDate="" 实际走 Jackson 反序列化分支，
        已由 TC-EMP-012 单独锚定，两者不可混用。
        """
        payload = data_factory.employee_payload()
        if mode == "显式null":
            payload["hireDate"] = None
        else:
            del payload["hireDate"]
        AssertUtil.assert_validation_error(employee_api.create(payload), "入职时间不能为空", f"{mode}: ")

    @pytest.mark.parametrize("hire_date,label", [
        ("2026/11/01", "斜杠分隔"),
        ("20261101", "无分隔符"),
        ("01/11/2026", "日月年"),
        ("not-a-date", "非日期字符串"),
        ("2026-13-01", "月份越界"),
    ])
    def test_create_hire_date_unparsable(self, employee_api, data_factory, hire_date, label):
        """TC-EMP-012 [P1] 新增员工-hireDate 格式非法

        等价类：Jackson 无法解析为 LocalDate。原用例数据（2026-03-01）其实是合法日期，
        用例名存实亡，本次纠正为真正非法的 5 种写法。
        """
        payload = data_factory.employee_payload(hireDate=hire_date)
        resp = employee_api.create(payload)
        AssertUtil.assert_status_code(resp, 400, f"{label} {hire_date}: ")
        AssertUtil.assert_message_equals(resp, UNREADABLE_BODY, f"{label} {hire_date}: ")
        assert "入职时间" not in resp.json()["message"], "反序列化早于 Bean Validation"

    @pytest.mark.parametrize("status,keyword", [
        ("", "状态不能为空"),
        ("未知", "状态不合法"),
        ("在职 ", "状态不合法"),
    ])
    def test_create_status_invalid(self, employee_api, data_factory, status, keyword):
        """TC-EMP-013 [P0] 新增员工-status 非法

        等价类：三个不同的源码失败分支（@NotBlank / 枚举 / 枚举用未 trim 的原值）。
        message 中的可选值集合来自 Set.of，顺序不保证，禁止断言全等。
        """
        payload = data_factory.employee_payload(status=status)
        AssertUtil.assert_validation_error(employee_api.create(payload), keyword, f"status={repr(status)}: ")

    def test_create_no_token(self, no_auth_client, data_factory):
        """TC-EMP-014 [P0] 新增员工-未携带Token"""
        resp = no_auth_client.post("/api/employees", json=data_factory.employee_payload())
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)

    @pytest.mark.parametrize("length,expected_status", [(50, 200), (51, 400)])
    def test_create_name_length_boundary(self, employee_api, data_factory, data_cleaner, length, expected_status):
        """TC-EMP-015 [P1] 新增员工-name 长度边界（50 / 51）

        边界值成对：有效上界与首个无效值共置（原 TC-EMP-016 已并入）。
        """
        payload = data_factory.employee_payload(name=data_factory.string_of_length(length),
                                               phone=data_factory.unique_phone())
        resp = employee_api.create(payload)
        AssertUtil.assert_status_code(resp, expected_status, f"name 长度 {length}: ")
        if expected_status == 200:
            data_cleaner.track_employee(resp.json()["data"]["id"])
            assert len(resp.json()["data"]["name"]) == 50
        else:
            AssertUtil.assert_message_contains(resp, "姓名长度不能超过50个字符")

    @pytest.mark.parametrize("length,expected_status", [(50, 200), (51, 400)])
    def test_create_department_length_boundary(self, employee_api, data_factory, data_cleaner,
                                               length, expected_status):
        """TC-EMP-018 [P2] 新增员工-department 长度边界（50 / 51）

        边界值成对（原 TC-EMP-019 已并入）。此前脚本完全缺失该边界。
        """
        payload = data_factory.employee_payload(department=data_factory.string_of_length(length),
                                                phone=data_factory.unique_phone())
        resp = employee_api.create(payload)
        AssertUtil.assert_status_code(resp, expected_status, f"department 长度 {length}: ")
        if expected_status == 200:
            data_cleaner.track_employee(resp.json()["data"]["id"])
            assert len(resp.json()["data"]["department"]) == 50
        else:
            AssertUtil.assert_message_contains(resp, "部门长度不能超过50个字符")

    def test_create_reuse_deleted_phone(self, employee_api, data_factory, data_cleaner):
        """TC-EMP-020 [P1] 新增员工-已删除手机号可复用

        错误推测：existsByPhone 带 deleted=0 过滤，软删除应释放唯一键。
        """
        first = data_factory.employee_payload(phone=data_factory.unique_phone())
        resp = employee_api.create(first)
        AssertUtil.assert_response_success(resp, "预置员工: ")
        emp_id = resp.json()["data"]["id"]
        data_cleaner.track_employee(emp_id)
        AssertUtil.assert_status_code(employee_api.delete(emp_id), 200, "删除预置员工: ")

        second = data_factory.employee_payload(phone=first["phone"])
        resp2 = employee_api.create(second)
        AssertUtil.assert_status_code(resp2, 200, "复用已删除手机号: ")
        data_cleaner.track_employee(resp2.json()["data"]["id"])
        assert resp2.json()["data"]["phone"] == first["phone"]

    def test_create_all_required_empty(self, employee_api):
        """TC-EMP-021 [P1] 新增员工-全部必填字段同时为空

        判定表：多字段同时非法时的错误聚合行为（以 "; " 拼接），
        与 TC-EMP-026 的短路行为相反，两者必须分别锚定。
        """
        resp = employee_api.create({})
        AssertUtil.assert_status_code(resp, 400)
        message = resp.json()["message"]
        for keyword in ("姓名不能为空", "部门不能为空", "岗位不能为空", "状态不能为空"):
            assert keyword in message, f"message 应包含 {keyword}，实际：{message}"
        assert "; " in message, f"message 应以 '; ' 聚合多条提示，实际：{message}"

    def test_create_string_fields_trimmed(self, employee_api, data_factory, data_cleaner):
        """TC-EMP-023 [P2] 新增员工-字符串字段前后带空格被 trim 后存储

        错误推测：applyRequest 统一 trim 入库，接口返回 DB 回读值。
        """
        payload = data_factory.employee_payload(name="  测试空格  ", department=" 研发部 ",
                                                phone=data_factory.unique_phone())
        resp = employee_api.create(payload)
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        data_cleaner.track_employee(data["id"])
        assert data["name"] == "测试空格"
        assert data["department"] == "研发部"
        assert employee_api.get_detail(data["id"]).json()["data"]["name"] == "测试空格"

    @pytest.mark.parametrize("phone,label", [
        ("13800138000 ", "尾部空格"),
        (" 13800138000", "首部空格"),
    ])
    def test_create_phone_with_spaces(self, employee_api, data_factory, phone, label):
        """TC-EMP-024 [P2] 新增员工-phone 前后带空格

        错误推测：@Pattern 校验未 trim 的原值，而 Service 存储时才 trim，
        与 name 等字段的行为不一致 —— 本用例锚定现状并作为风险项提出。
        """
        payload = data_factory.employee_payload(phone=phone)
        resp = employee_api.create(payload)
        AssertUtil.assert_status_code(resp, 400, f"phone={repr(phone)}（{label}）: ")
        AssertUtil.assert_message_contains(resp, "手机号格式不正确", f"{label}: ")

    def test_create_status_invalid_takes_priority_over_duplicate_phone(
            self, employee_api, data_factory, created_employee):
        """TC-EMP-025 [P1] 新增员工-status 非法与 phone 重复同时存在（校验优先级）

        判定表：Service 顺序为 validateStatus → existsByPhone，故 400 优先于 409。
        预期依据源码推导，待 dev 环境恢复后实测校准。
        """
        payload = data_factory.employee_payload(phone=created_employee["phone"], status="未知")
        resp = employee_api.create(payload)
        AssertUtil.assert_status_code(resp, 400, "应为 400 而非 409: ")
        assert resp.status_code != 409, "参数非法应优先于业务冲突报出"
        AssertUtil.assert_message_contains(resp, "状态不合法")
        assert employee_api.list(name=payload["name"]).json()["data"]["total"] == 0

    def test_create_unparsable_hire_date_short_circuits_other_validation(self, employee_api, data_factory):
        """TC-EMP-026 [P1] 新增员工-hireDate 不可解析时其余字段校验不执行（短路行为）

        判定表：Jackson 反序列化早于 @Valid，整条请求体丢失并返回统一提示。
        预期依据源码推导，待 dev 环境恢复后实测校准。
        """
        payload = data_factory.employee_payload(name="", phone="12345", hireDate="2026/11/01")
        resp = employee_api.create(payload)
        AssertUtil.assert_status_code(resp, 400)
        message = resp.json()["message"]
        AssertUtil.assert_message_equals(resp, UNREADABLE_BODY)
        assert "姓名不能为空" not in message, f"反序列化失败应短路掉 Bean Validation：{message}"
        assert "手机号格式不正确" not in message, f"反序列化失败应短路掉 Bean Validation：{message}"


class TestEmployeeFlow:
    """场景法：员工业务主流程"""

    def test_employee_lifecycle(self, employee_api, department_api, data_factory, data_cleaner):
        """TC-EMP-027 [P0] 员工全生命周期场景

        场景法：同一数据跨接口流转的一致性 —— 列表返回的 id 能查详情、
        编辑反映到详情、删除后手机号可复用，且全程无脏数据残留。
        """
        dept_resp = department_api.create(data_factory.department_payload())
        AssertUtil.assert_response_success(dept_resp, "预置部门: ")
        dept = dept_resp.json()["data"]
        data_cleaner.track_department(dept["id"])

        payload = data_factory.employee_payload(department=dept["name"], phone=data_factory.unique_phone())
        created = employee_api.create(payload)
        AssertUtil.assert_response_success(created, "步骤 1 新增员工: ")
        employee = created.json()["data"]
        emp_id = employee["id"]
        data_cleaner.track_employee(emp_id)

        hit = employee_api.list(name=employee["name"]).json()["data"]
        assert hit["total"] >= 1 and emp_id in [e["id"] for e in hit["list"]], "步骤 2 列表应命中该 id"

        detail = employee_api.get_detail(emp_id).json()["data"]
        assert detail == employee, "步骤 3 详情应与新增响应一致"
        created_at = detail["createdAt"]

        update_payload = dict(payload, position="升迁岗位", status="试用期")
        updated = employee_api.update(emp_id, update_payload)
        AssertUtil.assert_response_success(updated, "步骤 4 编辑员工: ")

        detail_after = employee_api.get_detail(emp_id).json()["data"]
        assert detail_after["position"] == "升迁岗位"
        assert detail_after["status"] == "试用期"
        assert detail_after["createdAt"] == created_at, "步骤 5 createdAt 不应变化"

        AssertUtil.assert_status_code(employee_api.delete(emp_id), 200, "步骤 6 删除员工: ")
        AssertUtil.assert_status_code(employee_api.get_detail(emp_id), 404, "步骤 7 已删除不可查详情: ")
        assert emp_id not in [e["id"] for e in employee_api.list(name=employee["name"]).json()["data"]["list"]], \
            "步骤 7 已删除不应出现在列表"

        reuse = data_factory.employee_payload(phone=payload["phone"])
        resp_reuse = employee_api.create(reuse)
        AssertUtil.assert_status_code(resp_reuse, 200, "步骤 8 手机号应可复用: ")
        data_cleaner.track_employee(resp_reuse.json()["data"]["id"])


class TestEmployeeList:
    """GET /api/employees"""

    def test_list_default_pagination(self, employee_api, created_employee):
        """TC-LIST-001 [P0] 列表查询-默认分页

        等价类：合法分页参数。锚定分页元数据结构与取值。
        预置 1 条员工，否则空库下 total>=0 之类的判定点会空转。
        """
        resp = employee_api.list(page=1, size=10)
        AssertUtil.assert_response_success(resp)
        AssertUtil.assert_pagination(resp)
        data = resp.json()["data"]
        assert data["page"] == 1 and data["size"] == 10
        assert data["total"] >= 1, f"预置后 total 应 ≥1，实际 {data['total']}"
        assert data["pages"] == -(-data["total"] // data["size"])
        assert len(data["list"]) == min(data["size"], data["total"])
        assert created_employee["id"] in [e["id"] for e in data["list"]], "预置员工应在首页结果中"

    def test_list_filter_combination(self, employee_api, data_factory, data_cleaner):
        """TC-LIST-002 [P1] 列表查询-筛选条件组合（name / department 判定表）

        判定表 2×2：只 name / 只 department / 两者（AND）/ 组合无匹配。
        原 TC-LIST-003（只按部门）、TC-LIST-004（组合）已并入。
        """
        name = data_factory.unique_name("组合筛选")
        department = data_factory.unique_dept_name("组合部门")
        payload = data_factory.employee_payload(name=name, department=department,
                                               phone=data_factory.unique_phone())
        resp = employee_api.create(payload)
        AssertUtil.assert_response_success(resp, "预置筛选数据: ")
        emp_id = resp.json()["data"]["id"]
        data_cleaner.track_employee(emp_id)

        name_kw, dept_kw = name[:4], department[:4]

        only_name = employee_api.list(name=name_kw).json()["data"]
        assert emp_id in [e["id"] for e in only_name["list"]], "只按 name 筛选应命中"
        assert all(name_kw in e["name"] for e in only_name["list"]), "结果应全部满足 name 条件"

        only_dept = employee_api.list(department=dept_kw).json()["data"]
        assert emp_id in [e["id"] for e in only_dept["list"]], "只按 department 筛选应命中"
        assert all(dept_kw in e["department"] for e in only_dept["list"]), "结果应全部满足 department 条件"

        both = employee_api.list(name=name_kw, department=dept_kw).json()["data"]
        assert emp_id in [e["id"] for e in both["list"]], "两条件同时满足应命中"

        conflict = employee_api.list(name=name_kw, department="不存在的部门ZZZ").json()["data"]
        assert conflict["list"] == [] and conflict["total"] == 0, "组合条件应为 AND 语义，不可只按其一过滤"

    def test_list_no_match(self, employee_api):
        """TC-LIST-005 [P1] 列表查询-无匹配数据"""
        resp = employee_api.list(name="不存在的名字XXXXX")
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        assert data["list"] == []
        assert data["total"] == 0
        assert data["pages"] == 0

    def test_list_ordered_by_id_desc(self, employee_api, two_employees):
        """TC-LIST-006 [P1] 列表查询-按 id 倒序

        默认排序是接口契约的一部分（前端"最新在前"），此前无回归防护。
        预置 2 条数据，空库环境下判定点同样成立。
        """
        resp = employee_api.list(page=1, size=100)
        AssertUtil.assert_response_success(resp)
        ids = [e["id"] for e in resp.json()["data"]["list"]]
        assert len(ids) >= 2, f"预置后首页至少应有 2 条，实际 {len(ids)}"
        assert ids == sorted(ids, reverse=True), f"id 序列应严格倒序，实际：{ids}"
        new_ids = [e["id"] for e in two_employees]
        assert set(new_ids) <= set(ids), f"预置员工应出现在首页：{new_ids} vs {ids}"
        assert ids.index(max(new_ids)) < ids.index(min(new_ids)), "后创建的员工应排在前面"

    @pytest.mark.parametrize("page", [0, -1])
    def test_list_page_below_lower_bound(self, employee_api, page):
        """TC-LIST-007 [P0] 列表查询-page 下界越界（0 / -1）

        边界值：越界侧。补 -1 负数分支（源码为 page < 1，而非 page == 0）。
        """
        resp = employee_api.list(page=page, size=10)
        AssertUtil.assert_status_code(resp, 400, f"page={page}: ")
        AssertUtil.assert_message_equals(resp, "页码 page 必须大于等于 1", f"page={page}: ")

    @pytest.mark.parametrize("size", [0, 101])
    def test_list_size_out_of_range(self, employee_api, size):
        """TC-LIST-008 [P0] 列表查询-size 越界（0 / 101）

        边界值：越界侧成对（原 TC-LIST-009 的 size=0 已并入）。有效侧见 TC-LIST-015。
        """
        resp = employee_api.list(page=1, size=size)
        AssertUtil.assert_status_code(resp, 400, f"size={size}: ")
        AssertUtil.assert_message_equals(resp, "每页条数 size 必须在 1 ~ 100 之间", f"size={size}: ")

    def test_list_no_auth(self, no_auth_client):
        """TC-LIST-010 [P0] 列表查询-未认证"""
        resp = no_auth_client.get("/api/employees", params={"page": 1, "size": 10})
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)

    def test_list_page_beyond_last_page(self, employee_api, two_employees):
        """TC-LIST-011 [P1] 列表查询-page 超出总页数

        分页语义：越界页不等于无数据，total/pages 仍应为真实值。
        预置 2 条数据，否则空库下 total/pages 的比较式判定点两侧同为 0，等于没验。
        """
        baseline = employee_api.list(page=1, size=10).json()["data"]
        assert baseline["total"] >= 2, f"预置后 total 应 ≥2，实际 {baseline['total']}"
        assert baseline["pages"] >= 1
        data = employee_api.list(page=99999, size=10).json()["data"]
        assert data["list"] == []
        assert data["total"] == baseline["total"]
        assert data["page"] == 99999
        assert data["pages"] == baseline["pages"]

    def test_list_excludes_deleted(self, employee_api, data_factory, data_cleaner):
        """TC-LIST-012 [P0] 列表查询-已删除员工不显示

        同时锚定"按姓名筛选"与"全量列表"两种查法（原 TC-DEL-006 已并入）。
        """
        payload = data_factory.employee_payload(phone=data_factory.unique_phone())
        resp = employee_api.create(payload)
        AssertUtil.assert_response_success(resp, "预置员工: ")
        emp_id = resp.json()["data"]["id"]
        data_cleaner.track_employee(emp_id)
        AssertUtil.assert_status_code(employee_api.delete(emp_id), 200, "删除预置员工: ")

        filtered = employee_api.list(name=payload["name"]).json()["data"]
        assert emp_id not in [e["id"] for e in filtered["list"]], "按姓名筛选不应返回已删除员工"

        full = employee_api.list(page=1, size=100).json()["data"]
        assert emp_id not in [e["id"] for e in full["list"]], "全量列表不应返回已删除员工"

    def test_list_pagination_metadata(self, employee_api, data_factory, data_cleaner):
        """TC-LIST-013 [P1] 列表查询-分页元数据计算正确性

        pages=ceil(total/size) 是纯计算逻辑，最易出"整除时多算一页"的差一错误，
        故自建可控的 total=3，不依赖库里不可控的历史数据量。
        """
        department = data_factory.unique_dept_name("分页校验")
        for _ in range(3):
            resp = employee_api.create(data_factory.employee_payload(
                department=department, phone=data_factory.unique_phone()))
            AssertUtil.assert_response_success(resp, "预置分页数据: ")
            data_cleaner.track_employee(resp.json()["data"]["id"])

        p1 = employee_api.list(page=1, size=2, department=department).json()["data"]
        p2 = employee_api.list(page=2, size=2, department=department).json()["data"]
        assert p1["total"] == 3, f"total 应为 3，实际 {p1['total']}"
        assert p1["pages"] == 2, f"pages 应为 ceil(3/2)=2，实际 {p1['pages']}"
        assert len(p1["list"]) == 2 and len(p2["list"]) == 1
        id1 = [e["id"] for e in p1["list"]]
        id2 = [e["id"] for e in p2["list"]]
        assert not set(id1) & set(id2), "两页数据不应有交集"
        assert min(id1) > max(id2), "第 2 页的 id 应均小于第 1 页（ORDER BY id DESC）"

    @pytest.mark.parametrize("keyword", ["%", "_"])
    def test_list_filter_with_like_wildcard(self, employee_api, two_employees, keyword):
        """TC-LIST-014 [P2] 列表查询-筛选值含 SQL LIKE 通配符

        错误推测：API.md 声明 name 为 `LIKE %name%` 且未承诺 ESCAPE，
        源码 appendFilters 用 "%" + name.trim() + "%" 拼接，因此 % / _ 按 SQL 语义生效，
        返回全量是本契约下的必然结果（不构成注入，JDBC 已参数化）。
        本用例锁定当前契约行为，同时为改进建议 R1 提供证据：
        用户无法检索姓名中的字面量 % / _，若业务需要则后端应做转义。
        """
        baseline = employee_api.list(page=1, size=10).json()["data"]["total"]
        resp = employee_api.list(name=keyword)
        AssertUtil.assert_status_code(resp, 200, f"name={keyword} 不应报 500: ")
        assert "SQL" not in resp.text and "SELECT" not in resp.text, "响应不应泄露 SQL 片段"
        total = resp.json()["data"]["total"]
        assert total == baseline, (
            f"按 API.md `LIKE %name%` 语义，name={keyword} 应命中全部 {baseline} 条，实际 {total} 条")

    @pytest.mark.parametrize("size", [1, 100])
    def test_list_size_valid_boundary(self, employee_api, two_employees, size):
        """TC-LIST-015 [P1] 列表查询-分页参数有效边界（size=1 / size=100）

        边界值成对的有效侧：与 TC-LIST-008 的越界侧共同界定 size 区间。
        预置 2 条数据，size=1 才能断言"首页取满 1 条"而不是 len<=size 的空转判定。
        """
        resp = employee_api.list(page=1, size=size)
        AssertUtil.assert_response_success(resp, f"size={size}: ")
        data = resp.json()["data"]
        assert data["page"] == 1 and data["size"] == size
        assert data["total"] >= 2, f"预置后 total 应 ≥2，实际 {data['total']}"
        assert data["pages"] == -(-data["total"] // size)
        assert len(data["list"]) == min(size, data["total"]), \
            f"size={size} 时首页应取满（total={data['total']}），实际 {len(data['list'])} 条"


class TestEmployeeDetail:
    """GET /api/employees/{id}"""

    def test_detail_success(self, employee_api, created_employee):
        """TC-DET-001 [P0] 查看详情-有效id"""
        resp = employee_api.get_detail(created_employee["id"])
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        assert data["id"] == created_employee["id"]
        for field in ("name", "phone", "department", "position", "hireDate", "status",
                      "createdAt", "updatedAt"):
            assert field in data, f"详情应包含字段 {field}"

    def test_detail_not_found(self, employee_api):
        """TC-DET-002 [P0] 查看详情-id不存在

        源码 message 拼接了入参 id，"包含 id"是排障上下文契约（与部门侧不一致，缺陷 D5）。
        """
        resp = employee_api.get_detail(99999999)
        AssertUtil.assert_status_code(resp, 404)
        AssertUtil.assert_biz_code(resp, 404)
        AssertUtil.assert_message_equals(resp, f"{NOT_FOUND_PREFIX}，id=99999999")
        assert resp.json()["data"] is None

    def test_detail_deleted(self, employee_api, data_factory, data_cleaner):
        """TC-DET-003 [P0] 查看详情-id 为已删除员工

        软删除与不存在走同一 404 分支（原 TC-DEL-005 已并入本用例）。
        """
        resp = employee_api.create(data_factory.employee_payload(phone=data_factory.unique_phone()))
        AssertUtil.assert_response_success(resp, "预置员工: ")
        emp = resp.json()["data"]
        data_cleaner.track_employee(emp["id"])
        AssertUtil.assert_status_code(employee_api.delete(emp["id"]), 200, "删除预置员工: ")

        detail = employee_api.get_detail(emp["id"])
        AssertUtil.assert_status_code(detail, 404)
        AssertUtil.assert_message_contains(detail, f"{NOT_FOUND_PREFIX}，id={emp['id']}")

    def test_detail_no_auth(self, no_auth_client, created_employee):
        """TC-DET-004 [P0] 查看详情-未认证"""
        resp = no_auth_client.get(f"/api/employees/{created_employee['id']}")
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)

    def test_detail_id_not_number(self, employee_api):
        """TC-DET-005 [P2] 查看详情-id 为非数字

        @PathVariable long id 的类型不匹配由 MethodArgumentTypeMismatchException 处理为 400；
        原预期"400 或 404"两分支都能通过，等于未断言。
        """
        resp = employee_api.get_detail("abc")
        AssertUtil.assert_status_code(resp, 400, "非数字 id 应确定为 400，不应是 404/500: ")
        AssertUtil.assert_biz_code(resp, 400)
        assert NOT_FOUND_PREFIX not in resp.json()["message"]
        assert resp.json()["data"] is None

    @pytest.mark.parametrize("emp_id", [0, -1])
    def test_detail_id_zero_or_negative(self, employee_api, emp_id):
        """TC-DET-006 [P2] 查看详情-id 为 0 或负数

        错误推测：0 是自增主键下界的相邻值，-1 常被前端用作"未选择"哨兵值。
        """
        resp = employee_api.get_detail(emp_id)
        AssertUtil.assert_status_code(resp, 404, f"id={emp_id}: ")
        AssertUtil.assert_message_contains(resp, f"{NOT_FOUND_PREFIX}，id={emp_id}")


class TestEmployeeEdit:
    """PUT /api/employees/{id}"""

    def test_edit_success(self, employee_api, created_employee, data_factory):
        """TC-EDT-001 [P0] 编辑员工-全字段更新（含手机号变更）

        createdAt 采用同源比较：新增响应回内存值（纳秒）且 MySQL DATETIME(0) 落库会四舍五入，
        编辑响应回 DB 值（秒级），跨源字符串等值断言不稳定。
        """
        emp_id = created_employee["id"]
        before = employee_api.get_detail(emp_id).json()["data"]

        payload = data_factory.employee_payload(
            phone=data_factory.unique_phone(), department="研发中心", position="高级测试工程师")
        resp = employee_api.update(emp_id, payload)
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]

        for field in ("name", "phone", "department", "position", "status", "hireDate"):
            assert data[field] == payload[field], f"{field} 应与更新请求一致"
        assert data["phone"] != before["phone"], "本用例应真正变更手机号（与 TC-EDT-002 形成对照）"

        after = employee_api.get_detail(emp_id).json()["data"]
        assert after["createdAt"] == before["createdAt"], "createdAt 不应因编辑而改变（同源比较）"
        assert after["updatedAt"] >= after["createdAt"]
        assert data == after, "编辑接口返回值应与库内值一致"

    def test_edit_phone_unchanged(self, employee_api, created_employee, data_factory):
        """TC-EDT-002 [P0] 编辑员工-手机号保持不变不触发 409

        判定表：existsByPhone(phone, excludeId) 的 `id <> ?` 分支。
        """
        emp_id = created_employee["id"]
        total_before = employee_api.list(page=1, size=1).json()["data"]["total"]

        payload = data_factory.employee_payload(
            name=created_employee["name"], phone=created_employee["phone"],
            department=created_employee["department"], position=created_employee["position"],
            hireDate=created_employee["hireDate"], status=created_employee["status"])

        resp = employee_api.update(emp_id, payload)
        AssertUtil.assert_status_code(resp, 200, "沿用自身手机号不应 409: ")

        after = employee_api.get_detail(emp_id).json()["data"]
        assert after["phone"] == created_employee["phone"], "手机号不应被改动"
        assert employee_api.list(page=1, size=1).json()["data"]["total"] == total_before, \
            "沿用自身手机号不应产生额外记录"

    def test_edit_not_found(self, employee_api, data_factory):
        """TC-EDT-003 [P0] 编辑员工-id不存在"""
        resp = employee_api.update(99999999, data_factory.employee_payload())
        AssertUtil.assert_status_code(resp, 404)
        AssertUtil.assert_message_contains(resp, NOT_FOUND_PREFIX)

    def test_edit_deleted_employee(self, employee_api, data_factory, data_cleaner):
        """TC-EDT-004 [P1] 编辑员工-id 为已删除员工

        update() 先 findById(id AND deleted=0) 返回 404；
        还需确认不会把 deleted 改回 0，否则编辑接口成了"恢复删除"的后门。
        """
        resp = employee_api.create(data_factory.employee_payload(phone=data_factory.unique_phone()))
        AssertUtil.assert_response_success(resp, "预置员工: ")
        emp_id = resp.json()["data"]["id"]
        data_cleaner.track_employee(emp_id)
        AssertUtil.assert_status_code(employee_api.delete(emp_id), 200, "删除预置员工: ")

        update_resp = employee_api.update(emp_id, data_factory.employee_payload())
        AssertUtil.assert_status_code(update_resp, 404, "已删除员工不应可编辑: ")
        AssertUtil.assert_status_code(employee_api.get_detail(emp_id), 404, "编辑失败不应使记录复活: ")

    def test_edit_phone_conflict(self, employee_api, two_employees):
        """TC-EDT-005 [P0] 编辑员工-手机号被他人占用"""
        emp_a, emp_b = two_employees
        payload = {k: emp_a[k] for k in ("name", "department", "position", "hireDate", "status")}
        payload["phone"] = emp_b["phone"]

        resp = employee_api.update(emp_a["id"], payload)
        AssertUtil.assert_status_code(resp, 409)
        AssertUtil.assert_biz_code(resp, 409)
        AssertUtil.assert_message_contains(resp, "手机号已被其他员工占用")
        assert emp_b["phone"] in resp.json()["message"], "message 应回显被占用的号码"
        assert employee_api.get_detail(emp_a["id"]).json()["data"]["phone"] == emp_a["phone"], \
            "409 后原手机号不应被改动"

    def test_edit_validation_error(self, employee_api, created_employee, data_factory):
        """TC-EDT-006 [P0] 编辑员工-参数校验失败

        编辑复用与新增完全相同的 @Valid 规则（同一 DTO），逐字段重复验证属冗余；
        取 3 个代表字段证明"同一套校验在 PUT 路径上同样生效"，并补新增侧没有的无脏写判定点。
        """
        emp_id = created_employee["id"]
        before = employee_api.get_detail(emp_id).json()["data"]
        base = dict(name=before["name"], phone=before["phone"], department=before["department"],
                    position=before["position"], hireDate=before["hireDate"], status=before["status"])

        for override, keyword in [({"name": ""}, "姓名不能为空"),
                                  ({"phone": "12345"}, "手机号格式不正确"),
                                  ({"status": "未知"}, "状态不合法")]:
            payload = dict(base, **override)
            resp = employee_api.update(emp_id, payload)
            AssertUtil.assert_status_code(resp, 400, f"{override}: ")
            AssertUtil.assert_message_contains(resp, keyword, f"{override}: ")
            assert employee_api.get_detail(emp_id).json()["data"] == before, \
                f"校验失败后不应发生部分写入（{override}）"

    def test_edit_no_auth(self, employee_api, no_auth_client, created_employee, data_factory):
        """TC-EDT-007 [P0] 编辑员工-未认证"""
        resp = no_auth_client.put(f"/api/employees/{created_employee['id']}",
                                  json=data_factory.employee_payload())
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)
        assert employee_api.get_detail(created_employee["id"]).json()["data"]["name"] \
            == created_employee["name"], "未认证请求不应产生写入副作用"

    def test_edit_reuse_deleted_phone(self, employee_api, data_factory, data_cleaner):
        """TC-EDT-008 [P1] 编辑员工-可使用已删除员工的手机号

        与 TC-EMP-020（新增复用）构成同一业务规则的读写两侧。
        """
        doomed = employee_api.create(data_factory.employee_payload(phone=data_factory.unique_phone()))
        AssertUtil.assert_response_success(doomed, "预置待删除员工: ")
        doomed_id = doomed.json()["data"]["id"]
        data_cleaner.track_employee(doomed_id)
        freed_phone = doomed.json()["data"]["phone"]
        AssertUtil.assert_status_code(employee_api.delete(doomed_id), 200, "删除预置员工: ")

        target = employee_api.create(data_factory.employee_payload(phone=data_factory.unique_phone()))
        AssertUtil.assert_response_success(target, "预置编辑目标: ")
        target_data = target.json()["data"]
        data_cleaner.track_employee(target_data["id"])

        payload = {k: target_data[k] for k in ("name", "department", "position", "hireDate", "status")}
        payload["phone"] = freed_phone
        resp = employee_api.update(target_data["id"], payload)
        AssertUtil.assert_status_code(resp, 200, "已释放的手机号应可被占用: ")
        assert employee_api.get_detail(target_data["id"]).json()["data"]["phone"] == freed_phone

    def test_edit_missing_required_field(self, employee_api, created_employee):
        """TC-EDT-009 [P1] 编辑员工-请求体缺失必填字段（全量更新契约）

        判定表：API.md §3.4 声明 PUT 是全量更新而非 PATCH。
        预期依据文档契约推导，待 dev 环境恢复后实测校准。
        """
        emp_id = created_employee["id"]
        resp = employee_api.update(emp_id, {"name": "仅改名"})
        AssertUtil.assert_status_code(resp, 400, "PUT 应为全量更新，缺必填字段不能被接受: ")
        AssertUtil.assert_message_contains(resp, "手机号不能为空")
        assert employee_api.get_detail(emp_id).json()["data"]["name"] == created_employee["name"], \
            "校验失败不应发生部分写入"


class TestEmployeeDelete:
    """DELETE /api/employees/{id}"""

    def test_delete_success(self, employee_api, data_factory, data_cleaner):
        """TC-DEL-001 [P0] 删除员工-成功

        删除契约：200 + data=null。
        """
        resp = employee_api.create(data_factory.employee_payload(phone=data_factory.unique_phone()))
        AssertUtil.assert_response_success(resp, "预置员工: ")
        emp_id = resp.json()["data"]["id"]
        data_cleaner.track_employee(emp_id)

        del_resp = employee_api.delete(emp_id)
        AssertUtil.assert_status_code(del_resp, 200)
        AssertUtil.assert_biz_code(del_resp, 200)
        assert del_resp.json()["data"] is None

    def test_delete_not_found(self, employee_api):
        """TC-DEL-002 [P0] 删除员工-id不存在

        删除侧 404 的 message 同样拼接了 id，需锚定；与部门侧（不含 id）形成对照，支撑缺陷 D5。
        """
        resp = employee_api.delete(99999999)
        AssertUtil.assert_status_code(resp, 404)
        AssertUtil.assert_biz_code(resp, 404)
        AssertUtil.assert_message_equals(resp, f"{NOT_FOUND_PREFIX}，id=99999999")

    def test_delete_duplicate(self, employee_api, data_factory, data_cleaner):
        """TC-DEL-003 [P0] 删除员工-重复删除"""
        resp = employee_api.create(data_factory.employee_payload(phone=data_factory.unique_phone()))
        AssertUtil.assert_response_success(resp, "预置员工: ")
        emp_id = resp.json()["data"]["id"]
        data_cleaner.track_employee(emp_id)

        AssertUtil.assert_status_code(employee_api.delete(emp_id), 200, "首次删除: ")
        second = employee_api.delete(emp_id)
        AssertUtil.assert_status_code(second, 404, "重复删除应返回 404: ")
        AssertUtil.assert_message_contains(second, NOT_FOUND_PREFIX)

    def test_delete_no_auth(self, employee_api, no_auth_client, created_employee):
        """TC-DEL-004 [P0] 删除员工-未认证"""
        resp = no_auth_client.delete(f"/api/employees/{created_employee['id']}")
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)
        AssertUtil.assert_status_code(employee_api.get_detail(created_employee["id"]), 200,
                                      "未认证请求不应产生删除副作用: ")
