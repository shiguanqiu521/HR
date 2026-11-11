# -*- coding: utf-8 -*-
"""
数据工厂
统一管理测试数据的生成和清理
"""
import uuid
import random
import string
from datetime import datetime, timedelta
from common.logger import logger


class DataFactory:
    """测试数据工厂，提供各类测试数据的生成方法"""
    
    @staticmethod
    def unique_phone():
        """
        生成唯一手机号（138开头的11位数字）
        
        Returns:
            str: 如 "13812345678"，每次调用结果唯一
        """
        return f"138{str(uuid.uuid4().int)[:8]}"
    
    @staticmethod
    def unique_name(prefix="测试"):
        """
        生成唯一姓名
        
        Args:
            prefix: 姓名前缀，默认"测试"
        
        Returns:
            str: 如 "测试_a1b2c3"，每次调用结果唯一
        """
        return f"{prefix}_{uuid.uuid4().hex[:6]}"
    
    @staticmethod
    def unique_dept_name(prefix="部门"):
        """
        生成唯一部门名称
        
        Args:
            prefix: 部门名前缀，默认"部门"
        
        Returns:
            str: 如 "部门_a1b2c3"
        """
        return f"{prefix}_{uuid.uuid4().hex[:6]}"
    
    @staticmethod
    def random_string(length=10):
        """
        生成指定长度的随机字符串（字母+数字）
        
        Args:
            length: 字符串长度，默认 10
        
        Returns:
            str: 随机字符串
        """
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_date(start_year=2020, end_year=2027):
        """
        生成指定年份范围内的随机日期
        
        Args:
            start_year: 起始年份，默认 2020
            end_year: 结束年份，默认 2027
        
        Returns:
            str: 格式为 "yyyy-MM-dd" 的日期字符串
        """
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        delta = (end - start).days
        random_days = random.randint(0, delta)
        return (start + timedelta(days=random_days)).strftime("%Y-%m-%d")
    
    @staticmethod
    def employee_payload(**overrides):
        """
        生成员工请求体数据，支持覆盖任意字段
        
        Args:
            **overrides: 需要覆盖的字段键值对，如 name="张三", status="试用期"
        
        Returns:
            dict: 包含 name/phone/department/position/hireDate/status 的完整员工数据
        """
        data = {
            "name": DataFactory.unique_name(),
            "phone": DataFactory.unique_phone(),
            "department": "研发部",
            "position": "测试工程师",
            "hireDate": "2026-03-01",
            "status": "在职"
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def department_payload(**overrides):
        """
        生成部门请求体数据，支持覆盖任意字段
        
        Args:
            **overrides: 需要覆盖的字段键值对，如 name="新部门"
        
        Returns:
            dict: 包含 name/description/manager 的部门数据
        """
        data = {
            "name": DataFactory.unique_dept_name(),
            "description": "自动化测试部门",
            "manager": "测试负责人"
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def login_payload(username="admin", password="admin123"):
        """
        生成登录请求体数据
        
        Args:
            username: 用户名，默认 "admin"
            password: 密码，默认 "admin123"
        
        Returns:
            dict: {"username": ..., "password": ...}
        """
        return {"username": username, "password": password}
    
    @staticmethod
    def string_of_length(length):
        """
        生成指定长度的中文字符串（用于边界值测试）
        
        Args:
            length: 目标字符串长度
        
        Returns:
            str: 由"测"字重复 length 次组成的字符串
        """
        return "测" * length
    
    @staticmethod
    def invalid_phone_cases():
        """
        无效手机号测试数据集
        
        Returns:
            list[tuple]: 每个元素为 (无效手机号, 场景描述) 的元组
        """
        return [
            ("12345", "非11位"),
            ("138abcd0000", "含字母"),
            ("23800138000", "非1开头"),
            ("", "空值"),
            ("12345678901234567890", "超长"),
        ]
    
    @staticmethod
    def invalid_status_cases():
        """
        无效员工状态测试数据集
        
        Returns:
            list[str]: 不在枚举范围内的状态值列表
        """
        return ["未知", "active", "123", "", "离职中"]
    
    @staticmethod
    def invalid_date_cases():
        """
        无效日期格式测试数据集
        
        Returns:
            list[tuple]: 每个元素为 (无效日期字符串, 场景描述) 的元组
        """
        return [
            ("2026/11/01", "斜杠格式"),
            ("20261101", "无分隔符"),
            ("01-11-2026", "日月年"),
            ("not-a-date", "非日期"),
            ("", "空值"),
        ]


class DataCleaner:
    """数据清理器，追踪测试中创建的数据并在用例结束后自动清理"""
    
    def __init__(self, api_client):
        """
        初始化数据清理器
        
        Args:
            api_client: BaseRequest 实例，用于发送删除请求
        """
        self.api = api_client
        self._created_employee_ids = []
        self._created_dept_ids = []
    
    def track_employee(self, emp_id):
        """
        记录创建的员工 ID，以便测试结束后清理
        
        Args:
            emp_id: 员工 ID（long 类型）
        """
        self._created_employee_ids.append(emp_id)
        logger.debug(f"追踪员工: {emp_id}")
    
    def track_department(self, dept_id):
        """
        记录创建的部门 ID，以便测试结束后清理
        
        Args:
            dept_id: 部门 ID（long 类型）
        """
        self._created_dept_ids.append(dept_id)
        logger.debug(f"追踪部门: {dept_id}")
    
    def cleanup(self):
        """
        清理所有追踪的测试数据（员工和部门）
        清理失败不会抛出异常，仅记录警告日志
        """
        for emp_id in self._created_employee_ids:
            try:
                self.api.delete(f"/api/employees/{emp_id}")
                logger.info(f"清理员工: {emp_id}")
            except Exception as e:
                logger.warning(f"清理员工 {emp_id} 失败: {e}")
        
        for dept_id in self._created_dept_ids:
            try:
                self.api.delete(f"/api/departments/{dept_id}")
                logger.info(f"清理部门: {dept_id}")
            except Exception as e:
                logger.warning(f"清理部门 {dept_id} 失败: {e}")
        
        self._created_employee_ids.clear()
        self._created_dept_ids.clear()
