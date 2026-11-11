# -*- coding: utf-8 -*-
"""
通用断言工具
封装常用的接口断言逻辑
"""
from common.logger import logger


class AssertUtil:
    """断言工具类"""
    
    @staticmethod
    def assert_status_code(response, expected_code, msg=""):
        """
        断言 HTTP 状态码
        
        Args:
            response: requests 响应对象
            expected_code: 期望的 HTTP 状态码（如 200, 400, 401, 404, 409）
            msg: 可选的前置提示信息，会拼接在断言失败消息前面
        
        Raises:
            AssertionError: 当实际状态码与期望不符时抛出
        """
        actual = response.status_code
        assert actual == expected_code, (
            f"{msg}HTTP 状态码不符: 期望 {expected_code}, 实际 {actual}\n"
            f"响应内容: {response.text}"
        )
        logger.info(f"[断言通过] HTTP 状态码 = {expected_code}")
    
    @staticmethod
    def assert_biz_code(response, expected_code, msg=""):
        """
        断言业务 code 字段
        
        Args:
            response: requests 响应对象
            expected_code: 期望的业务状态码（与 HTTP 状态码一致）
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当响应体中 code 字段与期望不符时抛出
        """
        data = response.json()
        actual = data.get("code")
        assert actual == expected_code, (
            f"{msg}业务 code 不符: 期望 {expected_code}, 实际 {actual}\n"
            f"响应内容: {data}"
        )
        logger.info(f"[断言通过] 业务 code = {expected_code}")
    
    @staticmethod
    def assert_message_contains(response, keyword, msg=""):
        """
        断言响应 message 包含指定关键字
        
        Args:
            response: requests 响应对象
            keyword: 期望 message 中包含的关键字
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当 message 不包含关键字时抛出
        """
        data = response.json()
        actual_msg = data.get("message", "")
        assert keyword in actual_msg, (
            f"{msg}message 不包含 '{keyword}': 实际 message = '{actual_msg}'\n"
            f"响应内容: {data}"
        )
        logger.info(f"[断言通过] message 包含 '{keyword}'")
    
    @staticmethod
    def assert_message_equals(response, expected_msg, msg=""):
        """
        断言响应 message 完全匹配指定值
        
        Args:
            response: requests 响应对象
            expected_msg: 期望的完整 message 内容
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当 message 与期望值不完全一致时抛出
        """
        data = response.json()
        actual_msg = data.get("message", "")
        assert actual_msg == expected_msg, (
            f"{msg}message 不匹配: 期望 '{expected_msg}', 实际 '{actual_msg}'"
        )
        logger.info(f"[断言通过] message = '{expected_msg}'")
    
    @staticmethod
    def assert_validation_error(response, keyword, msg=""):
        """
        断言参数校验失败的整体契约
        
        HTTP 400 + 业务 code 400 + message 包含指定关键字 + data 为 null。
        四个判定点缺一会让"返回 200 但 message 恰好含关键字"这类假阳性通过。
        
        Args:
            response: requests 响应对象
            keyword: 期望 message 中包含的关键字
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当任一判定点不满足时抛出
        """
        AssertUtil.assert_status_code(response, 400, msg)
        AssertUtil.assert_biz_code(response, 400, msg)
        AssertUtil.assert_message_contains(response, keyword, msg)
        assert response.json().get("data") is None, f"{msg}失败请求不应返回数据"
    
    @staticmethod
    def assert_data_not_null(response, msg=""):
        """
        断言响应 data 字段不为 null
        
        Args:
            response: requests 响应对象
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当 data 为 null 时抛出
        """
        data = response.json()
        assert data.get("data") is not None, (
            f"{msg}data 为 null\n响应内容: {data}"
        )
        logger.info(f"[断言通过] data 不为 null")
    
    @staticmethod
    def assert_data_is_list(response, msg=""):
        """
        断言响应 data 字段为列表类型
        
        Args:
            response: requests 响应对象
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当 data 不是 list 类型时抛出
        """
        data = response.json().get("data")
        assert isinstance(data, list), (
            f"{msg}data 不是列表类型: 实际类型 = {type(data)}"
        )
        logger.info(f"[断言通过] data 为列表")
    
    @staticmethod
    def assert_field_equals(response, field, expected_value, msg=""):
        """
        断言响应 data 中指定字段等于期望值
        
        Args:
            response: requests 响应对象
            field: 要检查的字段名（如 "name", "status"）
            expected_value: 期望的字段值
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当字段值与期望不符时抛出
        """
        data = response.json().get("data", {})
        actual_value = data.get(field)
        assert actual_value == expected_value, (
            f"{msg}字段 {field} 不匹配: 期望 {expected_value}, 实际 {actual_value}"
        )
        logger.info(f"[断言通过] {field} = {expected_value}")
    
    @staticmethod
    def assert_field_in(response, field, msg=""):
        """
        断言响应 data 中包含指定字段
        
        Args:
            response: requests 响应对象
            field: 期望存在的字段名
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当 data 中不存在该字段时抛出
        """
        data = response.json().get("data", {})
        assert field in data, (
            f"{msg}data 中缺少字段 {field}\n"
            f"实际字段: {list(data.keys())}"
        )
        logger.info(f"[断言通过] data 包含字段 {field}")
    
    @staticmethod
    def assert_response_success(response, msg=""):
        """
        断言接口整体成功（HTTP 200 + 业务 code 200）
        
        Args:
            response: requests 响应对象
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当 HTTP 状态码或业务 code 不为 200 时抛出
        """
        AssertUtil.assert_status_code(response, 200, msg)
        AssertUtil.assert_biz_code(response, 200, msg)
    
    @staticmethod
    def assert_pagination(response, msg=""):
        """
        断言分页响应结构完整且字段类型正确
        
        Args:
            response: requests 响应对象
            msg: 可选的前置提示信息
        
        Raises:
            AssertionError: 当缺少 list/total/page/size/pages 字段或类型不正确时抛出
        """
        data = response.json().get("data", {})
        for field in ["list", "total", "page", "size", "pages"]:
            assert field in data, f"{msg}分页响应缺少字段: {field}"
        assert isinstance(data["list"], list), f"{msg}list 不是数组"
        assert isinstance(data["total"], int), f"{msg}total 不是整数"
        logger.info(f"[断言通过] 分页结构正确: total={data['total']}, page={data['page']}, pages={data['pages']}")
