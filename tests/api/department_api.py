# -*- coding: utf-8 -*-
"""
部门管理接口封装
"""
from common.request_handler import BaseRequest
from common.logger import logger


class DepartmentAPI:
    """部门管理相关接口封装"""
    
    def __init__(self, request_client: BaseRequest = None):
        """
        初始化部门 API
        
        Args:
            request_client: 可选的请求客户端实例，不传则自动创建新实例
        """
        self.req = request_client or BaseRequest()
    
    def create(self, payload):
        """
        新增部门
        
        Args:
            payload: 部门数据字典，name 必填，description 和 manager 选填
        
        Returns:
            requests.Response: 响应对象，成功时 data 中包含完整部门信息（含 id）
        """
        logger.info(f"[DepartmentAPI] 新增部门: name={payload.get('name')}")
        return self.req.post("/api/departments", json=payload)
    
    def list(self, name=None):
        """
        部门列表查询
        
        Args:
            name: 可选，按部门名称模糊筛选
        
        Returns:
            requests.Response: 响应对象，data 为部门列表（数组）
        """
        params = {}
        if name:
            params["name"] = name
        logger.info(f"[DepartmentAPI] 查询部门列表: {params}")
        return self.req.get("/api/departments", params=params)
    
    def get_detail(self, dept_id):
        """
        查询部门详情
        
        Args:
            dept_id: 部门 ID
        
        Returns:
            requests.Response: 响应对象，成功时 data 为完整部门信息
        """
        logger.info(f"[DepartmentAPI] 查询部门详情: id={dept_id}")
        return self.req.get(f"/api/departments/{dept_id}")
    
    def update(self, dept_id, payload):
        """
        编辑部门信息
        
        Args:
            dept_id: 部门 ID
            payload: 更新后的部门数据字典，name 必填
        
        Returns:
            requests.Response: 响应对象，成功时 data 为更新后的完整部门信息
        """
        logger.info(f"[DepartmentAPI] 编辑部门: id={dept_id}")
        return self.req.put(f"/api/departments/{dept_id}", json=payload)
    
    def delete(self, dept_id):
        """
        删除部门（软删除）
        
        Args:
            dept_id: 部门 ID
        
        Returns:
            requests.Response: 响应对象，成功时 data 为 null
        """
        logger.info(f"[DepartmentAPI] 删除部门: id={dept_id}")
        return self.req.delete(f"/api/departments/{dept_id}")
    
    def get_names(self):
        """
        获取部门名称字典（供前端下拉框使用）
        
        Returns:
            requests.Response: 响应对象，data 为去重升序的部门名称数组
        """
        logger.info("[DepartmentAPI] 获取部门名称字典")
        return self.req.get("/api/departments/meta/names")
    
    def create_and_track(self, payload, cleaner):
        """
        创建部门并追踪到清理器
        
        Args:
            payload: 部门数据字典
            cleaner: DataCleaner 实例
        
        Returns:
            requests.Response: 响应对象
        """
        resp = self.create(payload)
        if resp.status_code == 200:
            dept_id = resp.json()["data"]["id"]
            cleaner.track_department(dept_id)
        return resp
    
    def quick_create(self, cleaner=None, **overrides):
        """
        快速创建一个部门（使用 DataFactory 生成的默认数据）
        
        Args:
            cleaner: 可选的 DataCleaner 实例，传入时自动追踪创建的部门
            **overrides: 覆盖默认数据的字段，如 name="新部门"
        
        Returns:
            requests.Response: 响应对象
        """
        from common.data_factory import DataFactory
        payload = DataFactory.department_payload(**overrides)
        resp = self.create(payload)
        if resp.status_code == 200 and cleaner:
            cleaner.track_department(resp.json()["data"]["id"])
        return resp
