# -*- coding: utf-8 -*-
"""
接口请求封装
统一处理请求日志、异常、重试
"""
import requests
from common.logger import logger
from config import Config


class BaseRequest:
    """基础请求封装类，统一处理请求日志、异常、重试"""
    
    def __init__(self, base_url=None, timeout=None):
        """
        初始化请求客户端
        
        Args:
            base_url: 服务基础地址，默认从 Config 读取
            timeout: 请求超时时间（秒），默认从 Config 读取
        """
        self.base_url = base_url or Config.BASE_URL
        self.timeout = timeout or Config.REQUEST_TIMEOUT
        self.session = requests.Session()
        self.last_request = None
        self.last_response = None
    
    def _build_url(self, path):
        """
        构建完整请求 URL
        
        Args:
            path: 接口路径，如 /api/employees；若已是完整 URL 则直接返回
        
        Returns:
            str: 拼接后的完整 URL
        """
        if path.startswith("http"):
            return path
        return f"{self.base_url}{path}"
    
    def _log_request(self, method, url, **kwargs):
        """
        打印请求日志（自动脱敏 Authorization 头）并记录到 last_request
        
        Args:
            method: HTTP 方法（GET/POST/PUT/DELETE）
            url: 请求 URL
            **kwargs: 请求参数（headers、json、params 等）
        """
        logger.info(f">>> {method} {url}")
        body = kwargs.get("json") or kwargs.get("data") or ""
        self.last_request = {"method": method, "url": url, "body": body}
        if "headers" in kwargs:
            safe_headers = {k: v for k, v in kwargs["headers"].items() if k.lower() != "authorization"}
            if "authorization" in {k.lower() for k in kwargs["headers"].keys()}:
                safe_headers["Authorization"] = "Bearer ***"
            logger.info(f">>> Headers: {safe_headers}")
        if "json" in kwargs:
            logger.info(f">>> Body: {kwargs['json']}")
        if "params" in kwargs:
            logger.info(f">>> Params: {kwargs['params']}")
    
    def _log_response(self, response):
        """
        打印响应日志
        
        Args:
            response: requests 响应对象
        """
        logger.info(f"<<< {response.status_code}")
        try:
            body = response.json()
            logger.info(f"<<< Body: {body}")
        except Exception:
            logger.info(f"<<< Body: {response.text[:500]}")
    
    def _handle_response(self, response):
        """
        统一处理响应：记录日志、保存到 last_response 并返回
        
        Args:
            response: requests 响应对象
        
        Returns:
            requests.Response: 原始响应对象
        """
        self._log_response(response)
        try:
            resp_body = response.json()
        except Exception:
            resp_body = response.text[:500]
        self.last_response = {"status_code": response.status_code, "body": resp_body}
        return response
    
    def set_token(self, token):
        """
        设置认证 Token（后续所有请求自动携带）
        
        Args:
            token: JWT Token 字符串
        """
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def clear_token(self):
        """清除已设置的认证 Token"""
        self.session.headers.pop("Authorization", None)
    
    def get(self, path, **kwargs):
        """
        发送 GET 请求（带认证）
        
        Args:
            path: 接口路径
            **kwargs: 传给 requests.get 的参数（params、headers 等）
        
        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(path)
        self._log_request("GET", url, **kwargs)
        resp = self.session.get(url, timeout=self.timeout, **kwargs)
        return self._handle_response(resp)
    
    def post(self, path, **kwargs):
        """
        发送 POST 请求（带认证）
        
        Args:
            path: 接口路径
            **kwargs: 传给 requests.post 的参数（json、headers 等）
        
        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(path)
        self._log_request("POST", url, **kwargs)
        resp = self.session.post(url, timeout=self.timeout, **kwargs)
        return self._handle_response(resp)
    
    def put(self, path, **kwargs):
        """
        发送 PUT 请求（带认证）
        
        Args:
            path: 接口路径
            **kwargs: 传给 requests.put 的参数（json、headers 等）
        
        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(path)
        self._log_request("PUT", url, **kwargs)
        resp = self.session.put(url, timeout=self.timeout, **kwargs)
        return self._handle_response(resp)
    
    def delete(self, path, **kwargs):
        """
        发送 DELETE 请求（带认证）
        
        Args:
            path: 接口路径
            **kwargs: 传给 requests.delete 的参数
        
        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(path)
        self._log_request("DELETE", url, **kwargs)
        resp = self.session.delete(url, timeout=self.timeout, **kwargs)
        return self._handle_response(resp)
    
    def get_no_auth(self, path, **kwargs):
        """
        发送 GET 请求（不带认证，用于测试 401 场景）
        
        Args:
            path: 接口路径
            **kwargs: 传给 requests.get 的参数
        
        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(path)
        self._log_request("GET (no auth)", url, **kwargs)
        resp = requests.get(url, timeout=self.timeout, **kwargs)
        return self._handle_response(resp)
    
    def post_no_auth(self, path, **kwargs):
        """
        发送 POST 请求（不带认证，用于登录等白名单接口）
        
        Args:
            path: 接口路径
            **kwargs: 传给 requests.post 的参数
        
        Returns:
            requests.Response: 响应对象
        """
        url = self._build_url(path)
        self._log_request("POST (no auth)", url, **kwargs)
        resp = requests.post(url, timeout=self.timeout, **kwargs)
        return self._handle_response(resp)
