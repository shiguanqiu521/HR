# -*- coding: utf-8 -*-
"""
员工管理接口封装
"""
from common.request_handler import BaseRequest
from common.logger import logger


class EmployeeAPI:
    """员工管理相关接口封装"""
    
    def __init__(self, request_client: BaseRequest = None):
        """
        初始化员工 API
        
        Args:
            request_client: 可选的请求客户端实例，不传则自动创建新实例
        """
        self.req = request_client or BaseRequest()
    
    def create(self, payload):
        """
        新增员工
        
        Args:
            payload: 员工数据字典，包含 name/phone/department/position/hireDate/status
        
        Returns:
            requests.Response: 响应对象，成功时 data 中包含完整员工信息（含 id）
        """
        logger.info(f"[EmployeeAPI] 新增员工: name={payload.get('name')}")
        return self.req.post("/api/employees", json=payload)
    
    def list(self, page=1, size=10, name=None, department=None):
        """
        员工列表查询（分页 + 筛选）
        
        Args:
            page: 页码，从 1 开始，默认 1
            size: 每页条数，1~100，默认 10
            name: 可选，按姓名模糊筛选
            department: 可选，按部门模糊筛选
        
        Returns:
            requests.Response: 响应对象，data 中包含 list/total/page/size/pages
        """
        params = {"page": page, "size": size}
        if name:
            params["name"] = name
        if department:
            params["department"] = department
        logger.info(f"[EmployeeAPI] 查询列表: {params}")
        return self.req.get("/api/employees", params=params)
    
    def get_detail(self, emp_id):
        """
        查询员工详情
        
        Args:
            emp_id: 员工 ID
        
        Returns:
            requests.Response: 响应对象，成功时 data 为完整员工信息
        """
        logger.info(f"[EmployeeAPI] 查询详情: id={emp_id}")
        return self.req.get(f"/api/employees/{emp_id}")
    
    def update(self, emp_id, payload):
        """
        编辑员工信息（全量更新）
        
        Args:
            emp_id: 员工 ID
            payload: 更新后的员工数据字典，所有必填字段都需要传入
        
        Returns:
            requests.Response: 响应对象，成功时 data 为更新后的完整员工信息
        """
        logger.info(f"[EmployeeAPI] 编辑员工: id={emp_id}")
        return self.req.put(f"/api/employees/{emp_id}", json=payload)
    
    def delete(self, emp_id):
        """
        删除员工（软删除）
        
        Args:
            emp_id: 员工 ID
        
        Returns:
            requests.Response: 响应对象，成功时 data 为 null
        """
        logger.info(f"[EmployeeAPI] 删除员工: id={emp_id}")
        return self.req.delete(f"/api/employees/{emp_id}")
    
    def create_and_track(self, payload, cleaner):
        """
        创建员工并追踪到清理器（用于自动清理测试数据）
        
        Args:
            payload: 员工数据字典
            cleaner: DataCleaner 实例
        
        Returns:
            requests.Response: 响应对象
        """
        resp = self.create(payload)
        if resp.status_code == 200:
            emp_id = resp.json()["data"]["id"]
            cleaner.track_employee(emp_id)
        return resp
    
    def quick_create(self, cleaner=None, **overrides):
        """
        快速创建一个员工（使用 DataFactory 生成的默认数据）
        
        Args:
            cleaner: 可选的 DataCleaner 实例，传入时自动追踪创建的员工
            **overrides: 覆盖默认数据的字段，如 name="张三", status="试用期"
        
        Returns:
            requests.Response: 响应对象
        """
        from common.data_factory import DataFactory
        payload = DataFactory.employee_payload(**overrides)
        resp = self.create(payload)
        if resp.status_code == 200 and cleaner:
            cleaner.track_employee(resp.json()["data"]["id"])
        return resp
