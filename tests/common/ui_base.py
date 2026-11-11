# -*- coding: utf-8 -*-
"""
UI 自动化基础封装（Selenium/Playwright）
预留接口，后续扩展 UI 测试时使用
"""
from common.logger import logger


class BasePage:
    """
    Page Object 基类
    所有页面对象继承此类，封装常用的浏览器操作方法
    """
    
    def __init__(self, driver=None):
        """
        初始化页面对象
        
        Args:
            driver: Selenium WebDriver 实例，为 None 时仅记录日志不执行操作
        """
        self.driver = driver
        self.page_name = self.__class__.__name__
    
    def open(self, url):
        """
        打开指定 URL 页面
        
        Args:
            url: 要访问的完整 URL 地址
        """
        logger.info(f"[{self.page_name}] 打开页面: {url}")
        if self.driver:
            self.driver.get(url)
    
    def find_element(self, locator):
        """
        查找页面元素
        
        Args:
            locator: 定位器元组，如 ("id", "username") 或 ("css", ".btn")
        
        Returns:
            WebElement: 找到的元素对象，driver 为 None 时返回 None
        """
        logger.info(f"[{self.page_name}] 查找元素: {locator}")
        if self.driver:
            return self.driver.find_element(*locator)
        return None
    
    def click(self, locator):
        """
        点击元素
        
        Args:
            locator: 定位器元组
        """
        logger.info(f"[{self.page_name}] 点击: {locator}")
        element = self.find_element(locator)
        if element:
            element.click()
    
    def input_text(self, locator, text):
        """
        向输入框填写文本（先清空再输入）
        
        Args:
            locator: 定位器元组
            text: 要输入的文本内容
        """
        logger.info(f"[{self.page_name}] 输入 '{text}' 到: {locator}")
        element = self.find_element(locator)
        if element:
            element.clear()
            element.send_keys(text)
    
    def get_text(self, locator):
        """
        获取元素的文本内容
        
        Args:
            locator: 定位器元组
        
        Returns:
            str: 元素文本，元素不存在时返回空字符串
        """
        element = self.find_element(locator)
        if element:
            text = element.text
            logger.info(f"[{self.page_name}] 获取文本: {locator} = '{text}'")
            return text
        return ""
    
    def is_element_present(self, locator, timeout=10):
        """
        判断元素是否在页面上存在（不要求可见）
        
        Args:
            locator: 定位器元组
            timeout: 等待超时时间（秒），默认 10
        
        Returns:
            bool: 元素存在返回 True，超时或不存在返回 False
        """
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except Exception:
            return False
    
    def wait_for_element(self, locator, timeout=10):
        """
        等待元素可见后返回
        
        Args:
            locator: 定位器元组
            timeout: 等待超时时间（秒），默认 10
        
        Returns:
            WebElement: 可见的元素对象
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )
    
    def screenshot(self, filename):
        """
        对当前页面截图并保存
        
        Args:
            filename: 截图文件保存路径
        """
        logger.info(f"[{self.page_name}] 截图: {filename}")
        if self.driver:
            self.driver.save_screenshot(filename)


class LoginPage(BasePage):
    """
    登录页面对象（示例）
    后续根据实际前端页面补充定位器
    """
    
    # 定位器（待补充实际值）
    USERNAME_INPUT = ("id", "username")
    PASSWORD_INPUT = ("id", "password")
    LOGIN_BUTTON = ("id", "login-btn")
    ERROR_MESSAGE = ("class", "error-msg")
    
    def login(self, username, password):
        """
        执行登录操作
        
        Args:
            username: 用户名
            password: 密码
        """
        logger.info(f"[LoginPage] 用户 '{username}' 登录")
        self.input_text(self.USERNAME_INPUT, username)
        self.input_text(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)
    
    def get_error_message(self):
        """
        获取登录失败时的错误提示信息
        
        Returns:
            str: 错误提示文本
        """
        return self.get_text(self.ERROR_MESSAGE)
    
    def is_login_success(self):
        """
        判断是否登录成功（根据页面是否跳转到首页判断）
        
        Returns:
            bool: 登录成功返回 True，否则返回 False
        """
        # 根据实际页面判断，比如跳转到首页
        return True


class EmployeeListPage(BasePage):
    """
    员工列表页面对象（示例）
    """
    
    # 定位器（待补充）
    TABLE_ROWS = ("css", "table tbody tr")
    SEARCH_INPUT = ("id", "search-name")
    SEARCH_BUTTON = ("id", "btn-search")
    
    def search_by_name(self, name):
        """
        按姓名搜索员工
        
        Args:
            name: 搜索关键字（员工姓名）
        """
        logger.info(f"[EmployeeListPage] 搜索: {name}")
        self.input_text(self.SEARCH_INPUT, name)
        self.click(self.SEARCH_BUTTON)
    
    def get_row_count(self):
        """
        获取当前表格中显示的员工行数
        
        Returns:
            int: 表格行数
        """
        elements = self.driver.find_elements(*self.TABLE_ROWS)
        return len(elements)
