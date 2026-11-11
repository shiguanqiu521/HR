# -*- coding: utf-8 -*-
"""
部门管理接口测试

覆盖 TC-DP-*（新增）、TC-DL-*（列表）、TC-DD-*（详情）、TC-DU-*（编辑）、TC-DX-*（删除）、TC-DN-*（名称字典）
已合并删除的编号（不回收）：TC-DP-007
设计方法：等价类划分、边界值分析（上下界成对）、判定表（查重短路分支）、场景法、错误推测法
预期基线：DepartmentRequest 注解 + DepartmentService 校验顺序 + DepartmentRepository JPQL + GlobalExceptionHandler
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.assertions import AssertUtil
from common.data_factory import DataFactory

NOT_FOUND = "部门不存在或已删除"
NAME_DUPLICATE = "部门名称已存在"

# department.created_at 为 DATETIME(0)，只保留到秒。编辑若发生在同一秒内，
# 库内 updated_at 与 created_at 取值相同，"已刷新"的判定点会假失败。
SECOND_BOUNDARY_WAIT = 1.2


def unique_name_of_length(length):
    """定长且唯一的部门名：尾部 6 位随机字符，避免历史残留数据触发 409 掩盖长度判定。"""
    suffix = DataFactory.random_string(6)
    return DataFactory.string_of_length(length - len(suffix)) + suffix


class TestDepartmentCreate:
    """POST /api/departments"""

    @pytest.mark.parametrize("mode", ["可选字段键不传", "可选字段显式null"])
    def test_create_required_only(self, department_api, data_factory, data_cleaner, mode):
        """TC-DP-001 [P0] 新增部门-仅必填字段（不传 / 显式 null）

        等价类：可选字段的两种合法写法。源码 request.getDescription()!=null?trim:null
        对"键缺失"与"值为 null"行为一致，应同时验证而非只测其一。
        """
        name = data_factory.unique_dept_name("仅必填")
        if mode == "可选字段键不传":
            payload = {"name": name}
        else:
            payload = {"name": name, "description": None, "manager": None}

        resp = department_api.create(payload)
        AssertUtil.assert_response_success(resp, f"{mode}: ")
        data = resp.json()["data"]
        data_cleaner.track_department(data["id"])

        assert data["id"] > 0
        assert data["name"] == name
        assert data["description"] is None
        assert data["manager"] is None

    def test_create_all_fields(self, department_api, data_factory, data_cleaner):
        """TC-DP-002 [P0] 新增部门-全部字段"""
        payload = data_factory.department_payload(name=data_factory.unique_dept_name("全字段"),
                                                  description="负责测试", manager="张三")
        resp = department_api.create(payload)
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        data_cleaner.track_department(data["id"])

        assert data["name"] == payload["name"]
        assert data["description"] == "负责测试"
        assert data["manager"] == "张三"

    @pytest.mark.parametrize("name", ["", "   "])
    def test_create_name_blank(self, department_api, data_factory, name):
        """TC-DP-003 [P0] 新增部门-name 为空或纯空白

        等价类：@NotBlank 的两类失败输入，message 相同故合并为一条用例的两个数据行。
        """
        payload = data_factory.department_payload(name=name)
        AssertUtil.assert_validation_error(department_api.create(payload), "部门名称不能为空",
                                           f"name={repr(name)}: ")

    def test_create_name_duplicate(self, department_api, created_department, data_factory):
        """TC-DP-004 [P0] 新增部门-name重复

        判定表：参数合法但唯一性冲突 → 409（不是 400），且 message 为固定串。
        """
        name = created_department["name"]
        resp = department_api.create(data_factory.department_payload(name=name))
        AssertUtil.assert_status_code(resp, 409)
        AssertUtil.assert_biz_code(resp, 409)
        AssertUtil.assert_message_equals(resp, NAME_DUPLICATE)
        assert resp.json()["data"] is None

        hits = department_api.list(name=name).json()["data"]
        assert [d["name"] for d in hits].count(name) == 1, "查重失败不应落库"

    def test_create_no_auth(self, no_auth_client, data_factory):
        """TC-DP-005 [P0] 新增部门-未认证"""
        resp = no_auth_client.post("/api/departments", json=data_factory.department_payload())
        AssertUtil.assert_status_code(resp, 401)
        AssertUtil.assert_biz_code(resp, 401)
        assert resp.json()["data"] is None

    @pytest.mark.parametrize("length,expected_status", [(100, 200), (101, 400)])
    def test_create_name_length_boundary(self, department_api, data_factory, data_cleaner,
                                         length, expected_status):
        """TC-DP-006 [P2] 新增部门-name 长度边界（100 / 101）

        边界值成对：有效上界与首个越界值共置（原 TC-DP-007 已并入）。
        """
        payload = data_factory.department_payload(name=unique_name_of_length(length))
        resp = department_api.create(payload)
        AssertUtil.assert_status_code(resp, expected_status, f"name 长度 {length}: ")
        if expected_status == 200:
            data = resp.json()["data"]
            data_cleaner.track_department(data["id"])
            assert len(data["name"]) == 100
        else:
            AssertUtil.assert_message_contains(resp, "部门名称长度不能超过100个字符")

    @pytest.mark.parametrize("field,length,expected_status", [
        ("description", 200, 200),
        ("description", 201, 400),
        ("manager", 50, 200),
        ("manager", 51, 400),
    ])
    def test_create_optional_field_length_boundary(self, department_api, data_factory, data_cleaner,
                                                  field, length, expected_status):
        """TC-DP-008 [P2] 新增部门-可选字段长度边界（description 200/201、manager 50/51）

        边界值成对：两个可选字段各取有效上界与越界值，补齐 manager 此前的零覆盖。
        """
        payload = data_factory.department_payload(name=data_factory.unique_dept_name("可选边界"),
                                                  **{field: DataFactory.string_of_length(length)})
        resp = department_api.create(payload)
        AssertUtil.assert_status_code(resp, expected_status, f"{field} 长度 {length}: ")
        if expected_status == 200:
            data = resp.json()["data"]
            data_cleaner.track_department(data["id"])
            assert len(data[field]) == length
        else:
            keyword = ("部门描述长度不能超过200个字符" if field == "description"
                       else "部门负责人长度不能超过50个字符")
            AssertUtil.assert_message_contains(resp, keyword)


class TestDepartmentList:
    """GET /api/departments"""

    def test_list_all(self, department_api, created_department):
        """TC-DL-001 [P0] 部门列表-查询全部

        预置 1 个部门，避免依赖环境历史数据（空库时判定点会假失败）。
        """
        resp = department_api.list()
        AssertUtil.assert_response_success(resp)
        AssertUtil.assert_data_is_list(resp)
        data = resp.json()["data"]
        assert len(data) >= 1, f"预置后应至少返回 1 个未删除部门，实际 {len(data)}"
        assert created_department["id"] in [d["id"] for d in data], "预置部门应出现在列表中"
        for item in data:
            for field in ("id", "name", "createdAt", "updatedAt"):
                assert field in item, f"列表项缺少字段 {field}：{item}"

    def test_list_filter_by_name(self, department_api, created_department):
        """TC-DL-002 [P1] 部门列表-按名称模糊筛选

        LIKE %:name% 的命中侧：结果集须整体满足条件，而非仅首项命中。
        """
        name = created_department["name"]
        keyword = name[:4]
        resp = department_api.list(name=keyword)
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        assert created_department["id"] in [d["id"] for d in data], "应命中预置部门"
        assert all(keyword in d["name"] for d in data), "结果应全部满足 LIKE 条件"

    def test_list_no_match(self, department_api):
        """TC-DL-003 [P1] 部门列表-无匹配数据"""
        resp = department_api.list(name="不存在的部门ZZZ")
        AssertUtil.assert_response_success(resp)
        assert resp.json()["data"] == []

    def test_list_excludes_deleted(self, department_api, data_factory, data_cleaner):
        """TC-DL-004 [P0] 部门列表-已删除部门不显示"""
        payload = data_factory.department_payload(name=data_factory.unique_dept_name("待删除"))
        resp = department_api.create(payload)
        AssertUtil.assert_response_success(resp, "预置部门: ")
        dept = resp.json()["data"]
        data_cleaner.track_department(dept["id"])
        AssertUtil.assert_status_code(department_api.delete(dept["id"]), 200, "删除预置部门: ")

        listing = department_api.list().json()["data"]
        assert dept["id"] not in [d["id"] for d in listing], "列表不应返回已删除部门"
        assert payload["name"] not in [d["name"] for d in listing], "列表不应返回已删除部门名称"

    def test_list_ordered_by_created_at_desc(self, department_api, two_departments):
        """TC-DL-005 [P1] 部门列表-按创建时间倒序

        非递增而非严格递减：created_at 为 DATETIME(0)，同秒创建的部门排序值相等，
        断言严格递减会假失败。
        """
        resp = department_api.list()
        AssertUtil.assert_response_success(resp)
        items = resp.json()["data"]
        seq = [d["createdAt"] for d in items]
        assert len(seq) >= 2, f"预置后应至少返回 2 个部门，实际 {len(seq)}"
        assert {d["id"] for d in two_departments} <= {d["id"] for d in items}, "预置部门应在列表中"
        assert seq == sorted(seq, reverse=True), f"createdAt 序列应非递增，实际：{seq}"

    def test_list_empty_name_matches_all(self, department_api, created_department):
        """TC-DL-006 [P2] 部门列表-name 传空串等价于不筛选

        判定表：JPQL 条件为 ":name IS NULL OR d.name LIKE %:name%"，
        空串不是 NULL，走 LIKE %% 匹配全部。
        预置 1 个部门，否则空库下两侧同为 0，比较式判定点等于没验。
        """
        no_param = department_api.list()
        # 封装层以 `if name:` 组参，空串会被丢弃，故这里直接经 req 发原生查询参数
        empty = department_api.req.get("/api/departments", params={"name": ""})
        AssertUtil.assert_response_success(no_param)
        AssertUtil.assert_response_success(empty)
        all_items = no_param.json()["data"]
        assert len(all_items) >= 1, f"预置后应至少返回 1 个部门，实际 {len(all_items)}"
        assert created_department["id"] in [d["id"] for d in all_items], "预置部门应出现在列表中"
        assert len(empty.json()["data"]) == len(all_items), \
            "name 传空串应返回全部部门"


class TestDepartmentDetail:
    """GET /api/departments/{id}"""

    def test_detail_success(self, department_api, created_department):
        """TC-DD-001 [P0] 部门详情-有效id"""
        resp = department_api.get_detail(created_department["id"])
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        assert data["id"] == created_department["id"]
        for field in ("name", "description", "manager", "createdAt", "updatedAt"):
            assert field in data, f"详情应包含字段 {field}"
        assert data["name"] == created_department["name"]

    def test_detail_not_found(self, department_api):
        """TC-DD-002 [P0] 部门详情-id不存在

        源码 DepartmentService.getDetail 抛的是不含 id 的固定串，与员工侧不一致（缺陷 D5）。
        """
        resp = department_api.get_detail(99999999)
        AssertUtil.assert_status_code(resp, 404)
        AssertUtil.assert_biz_code(resp, 404)
        AssertUtil.assert_message_equals(resp, NOT_FOUND)
        assert "99999999" not in resp.json()["message"], "部门侧 404 未拼接 id（缺陷 D5）"
        assert resp.json()["data"] is None


class TestDepartmentEdit:
    """PUT /api/departments/{id}"""

    def test_edit_success(self, department_api, created_department, data_factory):
        """TC-DU-001 [P0] 编辑部门-成功

        createdAt 同源比较（编辑前后各取一次详情）：新增响应返回 JPA 实体内存值（纳秒），
        详情响应返回 DB 秒级值，跨源字符串等值断言必然不稳定。
        """
        dept_id = created_department["id"]
        before = department_api.get_detail(dept_id).json()["data"]
        time.sleep(SECOND_BOUNDARY_WAIT)

        new_name = data_factory.unique_dept_name("改名")
        payload = data_factory.department_payload(name=new_name, description="改后的描述", manager="李四")
        resp = department_api.update(dept_id, payload)
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        for field in ("name", "description", "manager"):
            assert data[field] == payload[field], f"{field} 应与更新请求一致"

        after = department_api.get_detail(dept_id).json()["data"]
        assert after["createdAt"] == before["createdAt"], "createdAt 不应因编辑而改变（同源比较）"
        assert after["updatedAt"] != after["createdAt"], "跨秒编辑后 updatedAt 应已刷新"
        assert after["updatedAt"] > after["createdAt"], "updatedAt 应晚于 createdAt"
        assert "T" in after["createdAt"], \
            "部门时间字段为 ISO-8601，与 API.md 声明的 yyyy-MM-dd HH:mm:ss 不一致（缺陷 D2）"
        assert "T" in after["updatedAt"], "部门时间字段应为 ISO-8601（缺陷 D2）"

    def test_edit_name_conflict(self, department_api, two_departments, data_factory):
        """TC-DU-002 [P0] 编辑部门-name 与其他部门重复"""
        dept_a, dept_b = two_departments
        payload = data_factory.department_payload(name=dept_b["name"],
                                                  description=dept_a["description"],
                                                  manager=dept_a["manager"])
        resp = department_api.update(dept_a["id"], payload)
        AssertUtil.assert_status_code(resp, 409)
        AssertUtil.assert_biz_code(resp, 409)
        AssertUtil.assert_message_equals(resp, NAME_DUPLICATE)

        after = department_api.get_detail(dept_a["id"]).json()["data"]
        assert after["name"] == dept_a["name"], "409 后名称不应被改动"
        assert after["description"] == dept_a["description"], "409 后其余字段也不应被改动"

    def test_edit_not_found(self, department_api, data_factory):
        """TC-DU-003 [P0] 编辑部门-id不存在"""
        resp = department_api.update(99999999, data_factory.department_payload())
        AssertUtil.assert_status_code(resp, 404)
        AssertUtil.assert_biz_code(resp, 404)
        AssertUtil.assert_message_equals(resp, NOT_FOUND)

    def test_edit_name_unchanged(self, department_api, created_department, data_factory):
        """TC-DU-004 [P1] 编辑部门-名称保持不变

        判定表：update() 的 !dept.getName().equals(request.getName()) 短路分支 ——
        名称未变则完全不查查重表。缺该分支时"改成无条件查重"的回归无法发现。
        预期依据源码推导，待 dev 环境恢复后实测校准。
        """
        dept_id = created_department["id"]
        name = created_department["name"]
        payload = data_factory.department_payload(name=name, description="仅改描述",
                                                  manager=created_department["manager"])
        resp = department_api.update(dept_id, payload)
        AssertUtil.assert_status_code(resp, 200, "沿用自身名称不应触发 409: ")
        data = resp.json()["data"]
        assert data["name"] == name
        assert data["description"] == "仅改描述"

        hits = department_api.list(name=name).json()["data"]
        assert [d["id"] for d in hits] == [dept_id], "名称未变的编辑不应产生额外记录"

    def test_edit_reuse_deleted_name(self, department_api, data_factory, data_cleaner):
        """TC-DU-005 [P1] 编辑部门-复用已删除部门的名称

        判定表：查重条件 existsByNameAndDeleted(name, 0) 限定 deleted=0，软删除应释放名称；
        步骤 2 反向证明名称被未删除记录占用后仍生效，两条只可成功其一。
        """
        freed_name = data_factory.unique_dept_name("释放名称")
        doomed = department_api.create(data_factory.department_payload(name=freed_name))
        AssertUtil.assert_response_success(doomed, "预置待删除部门: ")
        doomed_id = doomed.json()["data"]["id"]
        data_cleaner.track_department(doomed_id)
        AssertUtil.assert_status_code(department_api.delete(doomed_id), 200, "删除预置部门: ")

        target = department_api.create(data_factory.department_payload(
            name=data_factory.unique_dept_name("编辑目标")))
        AssertUtil.assert_response_success(target, "预置编辑目标: ")
        target_data = target.json()["data"]
        data_cleaner.track_department(target_data["id"])

        edit_payload = data_factory.department_payload(
            name=freed_name, description=target_data["description"], manager=target_data["manager"])
        resp = department_api.update(target_data["id"], edit_payload)
        AssertUtil.assert_status_code(resp, 200, "已释放的部门名称应可被占用: ")

        dup = department_api.create(data_factory.department_payload(name=freed_name))
        AssertUtil.assert_status_code(dup, 409, "名称被未删除记录占用后应 409: ")
        AssertUtil.assert_message_equals(dup, NAME_DUPLICATE)


class TestDepartmentDelete:
    """DELETE /api/departments/{id}"""

    def test_delete_success(self, department_api, created_department):
        """TC-DX-001 [P0] 删除部门-成功

        删除契约：200 + data=null。
        """
        resp = department_api.delete(created_department["id"])
        AssertUtil.assert_status_code(resp, 200)
        AssertUtil.assert_biz_code(resp, 200)
        assert resp.json()["data"] is None

    def test_delete_duplicate(self, department_api, created_department):
        """TC-DX-002 [P0] 删除部门-重复删除"""
        dept_id = created_department["id"]
        AssertUtil.assert_status_code(department_api.delete(dept_id), 200, "首次删除: ")
        second = department_api.delete(dept_id)
        AssertUtil.assert_status_code(second, 404, "重复删除应返回 404: ")
        AssertUtil.assert_message_equals(second, NOT_FOUND)


class TestDepartmentNames:
    """GET /api/departments/meta/names"""

    def test_names_sorted_and_deduplicated(self, department_api, data_factory, data_cleaner):
        """TC-DN-001 [P1] 部门字典-返回名称列表

        排序+去重是 allNames() 的纯计算逻辑（distinct + sorted），需与 DB 顺序解耦验证。
        """
        for _ in range(2):
            resp = department_api.create(data_factory.department_payload(
                name=data_factory.unique_dept_name("字典")))
            AssertUtil.assert_response_success(resp, "预置部门: ")
            data_cleaner.track_department(resp.json()["data"]["id"])

        resp = department_api.get_names()
        AssertUtil.assert_response_success(resp)
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert all(isinstance(item, str) for item in data), "字典元素应为字符串"
        assert data == sorted(data), "字典应升序排列"
        assert len(data) == len(set(data)), "字典应去重"

    def test_names_exclude_deleted(self, department_api, data_factory, data_cleaner):
        """TC-DN-002 [P1] 部门字典-已删除部门不返回"""
        name = data_factory.unique_dept_name("字典删除")
        resp = department_api.create(data_factory.department_payload(name=name))
        AssertUtil.assert_response_success(resp, "预置部门: ")
        dept_id = resp.json()["data"]["id"]
        data_cleaner.track_department(dept_id)

        assert name in department_api.get_names().json()["data"], "预置名称应先出现在字典中"

        AssertUtil.assert_status_code(department_api.delete(dept_id), 200, "删除预置部门: ")
        assert name not in department_api.get_names().json()["data"], "已删除部门不应出现在字典中"
