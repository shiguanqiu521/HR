# -*- coding: utf-8 -*-
"""
页面对象 - 登录页
封装登录页面的所有交互操作，遵循 Page Object 模式
"""
from common.ui_base import BasePage
from common.logger import logger


class LoginPage(BasePage):
    """
    登录页面 Page Object
    
    Attributes:
        USERNAME_INPUT: 用户名输入框定位器
        PASSWORD_INPUT: 密码输入框定位器
        LOGIN_BUTTON: 登录按钮定位器
        ERROR_MESSAGE: 错误提示消息定位器
        HEADER_TITLE: 页面头部标题定位器（登录成功后可见）
    """
    
    # 定位器
    USERNAME_INPUT = ("id", "username")
    PASSWORD_INPUT = ("id", "password")
    LOGIN_BUTTON = ("css", "button[type='submit']")
    ERROR_MESSAGE = ("css", ".el-message--error")
    HEADER_TITLE = ("css", ".header-title")
    
    def __init__(self, driver):
        """
        初始化登录页对象
        
        Args:
            driver: Selenium WebDriver 实例
        """
        super().__init__(driver)
    
    def open_login_page(self, base_url):
        """
        打开登录页面
        
        Args:
            base_url: 服务基础地址（如 http://localhost:8080）
            
        Returns:
            LoginPage: 返回自身实例，支持链式调用
        """
        url = f"{base_url}"
        self.open(url)
        return self
    
    def login(self, username, password):
        """
        执行登录操作：依次输入用户名、密码并点击登录按钮
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            LoginPage: 返回自身实例，支持链式调用
        """
        logger.info(f"[LoginPage] 登录: {username}")
        self.input_text(self.USERNAME_INPUT, username)
        self.input_text(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)
        return self
    
    def get_error_message(self):
        """
        获取登录失败时的错误提示文本
        
        Returns:
            str: 错误提示信息内容
        """
        return self.get_text(self.ERROR_MESSAGE)
    
    def is_login_success(self):
        """
        判断登录是否成功（通过检测页面头部标题是否出现）
        
        Returns:
            bool: 登录成功返回 True，否则返回 False
        """
        try:
            return self.is_element_present(self.HEADER_TITLE, timeout=5)
        except Exception:
            return False
