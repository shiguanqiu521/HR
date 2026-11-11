# -*- coding: utf-8 -*-
"""
认证接口封装
"""
from common.request_handler import BaseRequest
from common.logger import logger


class AuthAPI:
    """认证相关接口封装"""
    
    def __init__(self, request_client: BaseRequest = None):
        """
        初始化认证 API
        
        Args:
            request_client: 可选的请求客户端实例，不传则自动创建新实例
        """
        self.req = request_client or BaseRequest()
    
    def login(self, username, password):
        """
        登录接口
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            requests.Response: 响应对象，成功时 data 中包含 token
        """
        logger.info(f"[AuthAPI] 登录: username={username}")
        payload = {"username": username, "password": password}
        return self.req.post_no_auth("/api/auth/login", json=payload)
    
    def get_current_user(self):
        """
        获取当前登录用户信息（需携带 Token）
        
        Returns:
            requests.Response: 响应对象，data 中包含 userId/username/displayName
        """
        logger.info("[AuthAPI] 获取当前用户信息")
        return self.req.get("/api/auth/me")
    
    def health_check(self):
        """
        健康检查接口（无需认证）
        
        Returns:
            requests.Response: 响应对象，data 中包含 status 和 application
        """
        logger.info("[AuthAPI] 健康检查")
        return self.req.get_no_auth("/api/health")
    
    def login_and_get_token(self, username="admin", password="admin123"):
        """
        登录并返回 Token（便捷方法，用于 fixture 中快速获取认证凭证）
        
        Args:
            username: 用户名，默认 "admin"
            password: 密码，默认 "admin123"
        
        Returns:
            str: JWT Token 字符串
        
        Raises:
            AssertionError: 当登录失败时抛出
        """
        resp = self.login(username, password)
        assert resp.status_code == 200, f"登录失败: {resp.text}"
        token = resp.json()["data"]["token"]
        logger.info(f"[AuthAPI] 登录成功，获取 Token")
        return token
